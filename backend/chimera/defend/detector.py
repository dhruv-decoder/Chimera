"""Ensemble fraud detector.

Two complementary channels:

  * Supervised (LightGBM gradient boosting) - high-precision detection of known
    attack shapes, trained on labelled events with class-imbalance weighting.
  * Novelty (IsolationForest + PCA reconstruction error, fit on legitimate
    traffic only) - flags events that don't look like normal behaviour even when
    the supervised model has never seen that attack type. This is the zero-day
    channel and the reason the loop can catch emerging vectors.

Per-transaction explanations use LightGBM's exact TreeSHAP contributions
(``pred_contrib=True``) - no extra serving dependency.
"""
from __future__ import annotations

import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from .features import build_features


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))


@dataclass
class FraudDetector:
    n_estimators: int = 450
    learning_rate: float = 0.05
    num_leaves: int = 64
    seed: int = 42

    lgbm: Optional[lgb.LGBMClassifier] = None
    scaler: Optional[StandardScaler] = None
    iforest: Optional[IsolationForest] = None
    pca: Optional[PCA] = None
    feature_names: List[str] = field(default_factory=list)
    _recon_mu: float = 0.0
    _recon_sd: float = 1.0
    _if_mu: float = 0.0
    _if_sd: float = 1.0

    # --- training --------------------------------------------------------
    def fit(self, df: pd.DataFrame) -> "FraudDetector":
        X, names = build_features(df)
        return self.fit_matrix(X, df["is_fraud"].to_numpy().astype(int), names)

    def fit_matrix(self, X: pd.DataFrame, y: np.ndarray, names: List[str]) -> "FraudDetector":
        """Fit from a precomputed feature matrix (lets callers share one feature
        computation across a train/test split for consistent aggregation context)."""
        self.feature_names = names
        y = np.asarray(y).astype(int)

        n_pos = max(int(y.sum()), 1)
        n_neg = int((y == 0).sum())
        self.lgbm = lgb.LGBMClassifier(
            n_estimators=self.n_estimators, learning_rate=self.learning_rate,
            num_leaves=self.num_leaves, subsample=0.85, subsample_freq=1,
            colsample_bytree=0.8, reg_lambda=1.0, min_child_samples=40,
            scale_pos_weight=n_neg / n_pos, random_state=self.seed, n_jobs=-1,
            verbose=-1,
        )
        self.lgbm.fit(X.to_numpy(), y)

        # Novelty channel fits on legitimate traffic only.
        legit = X[y == 0]
        self.scaler = StandardScaler().fit(legit.to_numpy())
        Z = self.scaler.transform(legit.to_numpy())
        n_comp = min(12, Z.shape[1])
        self.pca = PCA(n_components=n_comp, random_state=self.seed).fit(Z)
        recon = self._recon_error(Z)
        self._recon_mu, self._recon_sd = float(recon.mean()), float(recon.std() + 1e-9)

        self.iforest = IsolationForest(
            n_estimators=200, contamination=0.02, random_state=self.seed, n_jobs=-1
        ).fit(Z)
        if_scores = -self.iforest.score_samples(Z)  # higher = more anomalous
        self._if_mu, self._if_sd = float(if_scores.mean()), float(if_scores.std() + 1e-9)
        return self

    def _recon_error(self, Z: np.ndarray) -> np.ndarray:
        recon = self.pca.inverse_transform(self.pca.transform(Z))
        return np.mean((Z - recon) ** 2, axis=1)

    # --- scoring ---------------------------------------------------------
    def _features(self, df: pd.DataFrame) -> pd.DataFrame:
        X, _ = build_features(df)
        # Align to training columns (robust to a vector adding/removing a dummy).
        return X.reindex(columns=self.feature_names, fill_value=0.0)

    def _align(self, X: pd.DataFrame) -> pd.DataFrame:
        return X.reindex(columns=self.feature_names, fill_value=0.0)

    def predict_proba_matrix(self, X: pd.DataFrame) -> np.ndarray:
        return self.lgbm.predict_proba(self._align(X).to_numpy())[:, 1]

    def novelty_matrix(self, X: pd.DataFrame) -> np.ndarray:
        Z = self.scaler.transform(self._align(X).to_numpy())
        recon_z = (self._recon_error(Z) - self._recon_mu) / self._recon_sd
        if_z = (-self.iforest.score_samples(Z) - self._if_mu) / self._if_sd
        return 0.5 * _sigmoid(recon_z) + 0.5 * _sigmoid(if_z)

    def predict_proba(self, df: pd.DataFrame) -> np.ndarray:
        return self.predict_proba_matrix(self._features(df))

    def novelty_score(self, df: pd.DataFrame) -> np.ndarray:
        return self.novelty_matrix(self._features(df))

    def score(self, df: pd.DataFrame, novelty_weight: float = 0.45) -> pd.DataFrame:
        """Return supervised, novelty and blended risk for each event."""
        p = self.predict_proba(df)
        nov = self.novelty_score(df)
        # Novelty can only escalate risk (catch unknowns), never mask a known hit.
        risk = np.maximum(p, novelty_weight * nov)
        return pd.DataFrame({
            "txn_id": df["txn_id"].to_numpy(),
            "supervised_prob": p,
            "novelty_score": nov,
            "risk": risk,
        })

    # --- explainability --------------------------------------------------
    def explain(self, df: pd.DataFrame, top_k: int = 6) -> List[dict]:
        """Per-event top feature contributions via exact TreeSHAP."""
        X = self._features(df)
        contrib = self.lgbm.predict(X.to_numpy(), pred_contrib=True)  # (n, n_feat+1)
        names = np.array(self.feature_names)
        out = []
        for i in range(len(df)):
            vals = contrib[i, :-1]
            order = np.argsort(-np.abs(vals))[:top_k]
            out.append([
                {"feature": str(names[j]), "contribution": round(float(vals[j]), 4),
                 "value": round(float(X.iloc[i, j]), 4)}
                for j in order
            ])
        return out

    def global_importance(self) -> List[dict]:
        imp = self.lgbm.feature_importances_
        order = np.argsort(-imp)
        return [{"feature": self.feature_names[j], "importance": int(imp[j])} for j in order]

    # --- persistence -----------------------------------------------------
    def save(self, path: str | Path) -> None:
        with open(path, "wb") as fh:
            pickle.dump(self, fh)

    @staticmethod
    def load(path: str | Path) -> "FraudDetector":
        with open(path, "rb") as fh:
            return pickle.load(fh)
