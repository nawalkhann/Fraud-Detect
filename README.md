# Fraud Detect

Cost-sensitive fraud detection on the **IEEE-CIS Fraud Detection** dataset (real e-commerce
transactions from Vesta), with a decision threshold picked by business cost and an alert
queue an analyst can work through.

## Why this is hard
- **Imbalance:** about 3.5% of transactions are fraud, so a model that predicts "legit" for everything is 96.5% accurate and useless. We evaluate with PR-AUC and dollars.
- **Asymmetric cost:** a missed fraud loses the transaction amount plus a chargeback fee; a false alarm costs an analyst review. The threshold is chosen to minimise total cost (see `configs/default.yaml`).
- **Time:** fraud patterns drift, so every split is out-of-time: train on earlier days, tune on the next month, report on the last month.

## Plan
1. Data and validation setup: download, join, out-of-time split, data report. *(this step)*
2. Model and cost-based threshold: features, LightGBM vs logistic baseline, cost curve.
3. Scoring API (FastAPI) and analyst alert-queue dashboard (Streamlit).
4. Production shape: Docker, CI, model registry, drift check.

## Quick start
```bash
make install
export KAGGLE_USERNAME=... KAGGLE_KEY=...   # and click "Join Competition" on Kaggle once
make data                                   # or: make data ZIP=path/to/ieee-fraud-detection.zip
make report                                 # writes reports/data_report.md
make test
```
Set `FRAUD_DATA_DIR` to keep the ~1.5 GB of data somewhere other than `./data`.

## Layout
```
configs/default.yaml   split days and cost assumptions
src/fraud/data.py      download, identity join, dtype downcast, out-of-time split
src/fraud/profile.py   data report: fraud rates, amounts, missingness, drift (PSI)
tests/                 unit tests on tiny files with the IEEE-CIS column layout
```
