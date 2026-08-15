"""A graph neural network for coordinated fraud (mule rings, structuring).

Per-transaction models see one event at a time. Fraud rings are relational: an
account can look ordinary on its own features yet be one hop from a mule
collector. A GNN propagates signal along the account-to-account transfer graph,
so an account is judged partly by the company it keeps.

This is a compact GraphSAGE (mean-aggregation) implemented directly on a
row-normalised adjacency (no torch-geometric dependency): two message-passing
layers that each combine an account's own features with the mean of its
neighbours', trained for node classification (is this account part of a fraud
ring). It is benchmarked against gradient boosting on the *same node features*
without message passing, to isolate the value the graph structure adds.
"""
from __future__ import annotations

from typing import Tuple

import numpy as np
import pandas as pd

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    _HAS_TORCH = True
except Exception:  # pragma: no cover
    _HAS_TORCH = False


def build_node_dataset(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray, list]:
    """From the labelled event stream, build an account-graph node-classification
    task: node features X, row-normalised adjacency A, labels y (account touches
    fraud), and the node id list. Only account-to-account transfers form edges."""
    a2a = df[df["counterparty_type"] == "account"].copy()
    nodes = pd.Index(pd.unique(pd.concat([a2a["payer_account_id"], a2a["counterparty_id"]])))
    idx = {n: i for i, n in enumerate(nodes)}
    n = len(nodes)

    # directed adjacency (payer -> counterparty), weighted by count
    A = np.zeros((n, n), dtype=np.float32)
    for p, c in zip(a2a["payer_account_id"], a2a["counterparty_id"]):
        A[idx[p], idx[c]] += 1.0
    # symmetrise for undirected message passing + self loops
    A = A + A.T
    A[np.diag_indices(n)] += 1.0
    A /= A.sum(axis=1, keepdims=True) + 1e-9

    # node features (per account)
    feats = np.zeros((n, 8), dtype=np.float32)
    grp_out = a2a.groupby("payer_account_id")
    grp_in = a2a.groupby("counterparty_id")
    out_cnt = grp_out.size(); out_deg = grp_out["counterparty_id"].nunique()
    out_sum = grp_out["amount"].sum(); out_mean = grp_out["amount"].mean()
    in_cnt = grp_in.size(); in_deg = grp_in["payer_account_id"].nunique()
    in_sum = grp_in["amount"].sum(); in_mean = grp_in["amount"].mean()
    for series, col in [(out_cnt, 0), (out_deg, 1), (out_sum, 2), (out_mean, 3),
                        (in_cnt, 4), (in_deg, 5), (in_sum, 6), (in_mean, 7)]:
        for k, v in series.items():
            feats[idx[k], col] = float(v)
    feats[:, [2, 6]] = np.log1p(feats[:, [2, 6]])   # log the amount sums
    feats = (feats - feats.mean(0)) / (feats.std(0) + 1e-9)

    # label: account participates in any fraudulent A2A transfer
    fraud = a2a[a2a["is_fraud"] == 1]
    ring = set(fraud["payer_account_id"]) | set(fraud["counterparty_id"])
    y = np.array([1 if node in ring else 0 for node in nodes], dtype=np.int64)
    return feats, A, y, list(nodes)


if _HAS_TORCH:
    class GraphSAGE(nn.Module):
        def __init__(self, in_dim: int, hidden: int = 32):
            super().__init__()
            self.self1 = nn.Linear(in_dim, hidden); self.neigh1 = nn.Linear(in_dim, hidden)
            self.self2 = nn.Linear(hidden, hidden); self.neigh2 = nn.Linear(hidden, hidden)
            self.out = nn.Linear(hidden, 1)
            self.drop = nn.Dropout(0.3)

        def forward(self, x, a):
            h = F.relu(self.self1(x) + self.neigh1(a @ x))
            h = self.drop(h)
            h = F.relu(self.self2(h) + self.neigh2(a @ h))
            return self.out(h).squeeze(-1)

    def train_gnn(feats: np.ndarray, A: np.ndarray, y: np.ndarray, train_mask: np.ndarray,
                  epochs: int = 200, seed: int = 42, infer_A: np.ndarray | None = None) -> np.ndarray:
        """Train GraphSAGE on the train nodes; return sigmoid scores for all nodes.

        `A` is the adjacency used during training. Pass a separate `infer_A` for the
        final scoring pass to run an *inductive* evaluation: train on a graph that
        excludes the test nodes' edges (so their connectivity never influences the
        learned weights), then let the held-out accounts attach to their neighbours
        only at inference. When `infer_A` is None the evaluation is transductive."""
        torch.set_num_threads(1)  # avoid an OpenMP deadlock with LightGBM's thread pool
        torch.manual_seed(seed)
        x = torch.tensor(feats); a = torch.tensor(A); yt = torch.tensor(y, dtype=torch.float32)
        m = torch.tensor(train_mask)
        model = GraphSAGE(feats.shape[1])
        pos = float(y[train_mask].sum()); neg = float((y[train_mask] == 0).sum())
        pos_weight = torch.tensor([max(neg / max(pos, 1), 1.0)])
        opt = torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=5e-4)
        for _ in range(epochs):
            model.train(); opt.zero_grad()
            logits = model(x, a)
            loss = F.binary_cross_entropy_with_logits(logits[m], yt[m], pos_weight=pos_weight)
            loss.backward(); opt.step()
        model.eval()
        a_eval = torch.tensor(infer_A) if infer_A is not None else a
        with torch.no_grad():
            return torch.sigmoid(model(x, a_eval)).numpy()
