# Fraud Detect

Cost-sensitive fraud detection on two real, labelled transaction datasets, with a decision threshold picked by business cost and an alert
queue an analyst can work through.

## Data
| Dataset | What it is | Role |
|---|---|---|
| **IEEE-CIS** | 590k real e-commerce transactions from Vesta, ~6 months, 3.5% fraud, readable features | Main model, drives the alert queue and per-alert reasons |
| **ULB** | 285k real European card transactions (Sept 2013), 2 days, 0.17% fraud, PCA features | Second benchmark: does the cost-based threshold hold on a different fraud profile? |

The columns differ, so each gets its own model; both are mapped to the same core names
(`TransactionID`, `TransactionDT`, `TransactionAmt`, `isFraud`) so the cost, threshold and
dashboard code is shared. Kaggle's IEEE-CIS test file has no labels, so the test set for each
dataset is its final, held-out time slice.

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
make data-ulb                               # or: make data-ulb CSV=path/to/creditcard.csv
make report                                 # writes reports/data_report_{ieee,ulb}.md
make train                                  # writes reports/model_report_{ieee,ulb}.md
make serve                                  # scoring API: POST /score, GET /health
make dashboard                              # analyst alert queue
make drift BATCH=recent.parquet              # drift check, non-zero exit on alert
make docker                                 # API on :8000 and dashboard on :8501
make test
```
Each training run writes `models/<dataset>/metadata.json` (git sha, time, costs, test metrics)
and a reference sample for drift checks. CI runs the tests and builds the image on every push.
Set `FRAUD_DATA_DIR` to keep the ~1.5 GB of data somewhere other than `./data`.

## Layout
```
configs/default.yaml   split days and cost assumptions
src/fraud/data.py      download, identity join, dtype downcast, out-of-time split
src/fraud/ulb.py       ULB loader mapped to the shared schema, hourly out-of-time split
src/fraud/features.py  features fitted on train only (frequency, customer-id proxy, amount vs history)
src/fraud/cost.py      cost model, vectorised cost curve, cost-optimal threshold
src/fraud/train.py     LightGBM + logistic baseline, threshold policies, train/valid/test error report
src/fraud/alerts.py    scorer, per-alert reasons (LightGBM SHAP), queue ranked by expected loss
src/fraud/api.py       FastAPI scoring service
src/fraud/drift.py     PSI + score-shift drift check against the training reference (exit 1 on alert)
app/dashboard.py       Streamlit alert queue: live cost sliders, cost curve, review + decisions (SQLite)
src/fraud/profile.py   data report: fraud rates, amounts, missingness, drift (PSI)
tests/                 unit tests on tiny files with the IEEE-CIS column layout
```
