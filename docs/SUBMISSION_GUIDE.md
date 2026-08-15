# Kaggle submission - do this top to bottom

Follow the Writeup form field by field, in order. Everything you paste or upload
is in this repo. Nothing here has placeholders - it is all final.

## Step 0 - before you open the form (5 min)
1. Confirm the live site works: open https://chimera-8vx7.onrender.com and
   https://chimera-8vx7.onrender.com/api/health (should say `"detector_loaded":true`).
   If it is asleep, the first load takes ~30-60s; open it once to warm it.
2. Repo is already public: https://github.com/dhruv-decoder/chimera
3. (Optional) Upload the demo video to YouTube as **Unlisted**:
   youtube.com -> Create -> Upload -> `docs/Chimera_Demo.webm` -> copy the link.

---

## Now fill the form, top to bottom

### 1. Title
Paste: **Chimera: a closed-loop adversarial AI lab for GenAI-era payment fraud**

### 2. Subtitle
Paste: **An AI red team evolves fraud against a live detector; the detector retrains on what gets through. Identify, generate, defend as one loop.**

### 3. Card and Thumbnail Image
Click **Edit image** -> upload `docs/kaggle_card_560x280.png`.
(Use the same image if it asks for cover and thumbnail separately.)

### 4. Submission Track
Already set to **AI Defense Lab for Payment Security**. Leave it.

### 5. Media gallery (Add videos or photos)
Add in this exact order (the files are pre-numbered in `docs/gallery/`):
1. The **YouTube video link** (if you uploaded it) - put it first so it plays on top.
2. `docs/gallery/01-overview-thesis.png`
3. `docs/gallery/02-closed-loop.png`
4. `docs/gallery/03-attack-lab.png`
5. `docs/gallery/04-detection.png`
6. `docs/gallery/05-threat-matrix.png`
7. `docs/gallery/06-network-graph.png`
8. `docs/gallery/07-validation.png` (real-data + GNN + rigor evidence)

(Skipping the video is fine - the seven photos tell the whole story.)

### 6. Project Description
Open `docs/KAGGLE_WRITEUP.md`, copy everything from **`### Overview`** down to the
end of **`### What I Learned`**, and paste it into the description editor. It is
already in Kaggle's section structure and already links your live URL and repo -
nothing to edit.

### 7. Attachments
- **Project Links -> + Add a link** (add all three):
  1. `https://github.com/dhruv-decoder/chimera` (code)
  2. `https://chimera-8vx7.onrender.com` (live prototype)
  3. (optional) your Kaggle reproducibility notebook link
- **Files -> Upload Files:** upload `docs/Chimera_Deck.pdf`.

### 7b. External data, models and benchmarks (the "External" tabs)
The Writeup form has tabs for **Datasets / Models / Benchmarks / External links**.
Everything below is real, used in the project, and reproducible - fill them so the
judges see the grounding at a glance.

- **Datasets:** add the Kaggle dataset **ULB Credit Card Fraud** (`mlg-ulb/creditcardfraud`,
  284,807 real transactions, 492 fraud; also OpenML id 1597). This is what
  `scripts/validate_real.py` and `scripts/benchmark_baselines.py` run on. Say in one
  line: "detector + closed loop validated on this real benchmark, unchanged from the
  synthetic setup."
- **Models:** the open-weight **gpt-oss-120b / gpt-oss-20b** (OpenAI open models,
  served via Groq) drive the RAG ideation agent. The detector stack is **LightGBM**,
  a 2-layer **GraphSAGE** GNN (PyTorch), and an **IsolationForest + PCA** novelty
  channel; baselines are Logistic Regression, Random Forest and XGBoost.
- **Benchmarks:** the ULB real-fraud benchmark above (held-out PR-AUC: RandomForest
  0.82, LightGBM 0.81, Chimera 0.78, LogReg 0.70) and the GraphSAGE ring-detection
  benchmark (PR-AUC 0.84 -> 0.998). The runnable notebook is
  `notebooks/external_benchmark.ipynb`.
- **External links:** the repo and the live app (already added above), plus the two
  notebooks if you publish them on Kaggle.

Not sure a field applies? It is always safe to skip a tab - but the ULB dataset and
the gpt-oss / LightGBM / GraphSAGE models are worth adding, because they show real
external grounding rather than only synthetic data.

### 8. Submit
The checklist (top-right) turns 5/5 once Title, Subtitle, Track, Project
Description and Project Files are done. Click **Submit**. You can edit and
resubmit until **31 Aug 23:59 IST** - submit an early draft now as insurance.

---

## Optional: reproducibility notebooks (add credibility)
New Notebook -> File -> Upload -> then Save/Run:
- `notebooks/reproduce_chimera.ipynb` - clones the repo, runs the tests, prints the
  metrics + hardening curve.
- `notebooks/external_benchmark.ipynb` - runs the baselines + loop on the **real**
  ULB dataset (XGBoost is available on Kaggle), prints the PR-AUC table and chart.

Enable Internet in settings for both. Add their links under Project Links, and
attach the ULB dataset to `external_benchmark.ipynb` so it is one click to run.

## File reference
| Field | File |
|---|---|
| Title / Subtitle / Description | `docs/KAGGLE_WRITEUP.md` |
| Card image | `docs/kaggle_card_560x280.png` |
| Gallery photos (in order) | `docs/gallery/01..07-*.png` |
| Video | `docs/Chimera_Demo.webm` |
| Deck (Files attachment) | `docs/Chimera_Deck.pdf` |
| Reproducibility notebooks | `notebooks/reproduce_chimera.ipynb`, `notebooks/external_benchmark.ipynb` |
| Datasets / Models / Benchmarks tabs | see Step 7b above |
