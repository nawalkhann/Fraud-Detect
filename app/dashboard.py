"""Analyst alert queue.

    streamlit run app/dashboard.py

Scores the held-out test month, applies the cost-based alert rule (live, from the cost sliders), and lists alerts ranked by expected loss. Analyst
decisions are stored in SQLite next to the data so they survive restarts.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from fraud.alerts import Scorer, build_queue, model_dir
from fraud.config import data_paths, load_config
from fraud.cost import Costs, best_threshold, cost_curve, flag_by_expected_loss, outcome
from fraud.data import load_split

st.set_page_config(page_title="Fraud alert queue", layout="wide")
CFG = load_config()
DATASETS = {"ieee": "IEEE-CIS (Vesta e-commerce)", "ulb": "ULB (European cards)"}
STATUSES = ["open", "confirmed fraud", "dismissed", "escalated"]


# --------------------------------------------------------------------------- data

@st.cache_resource
def load_scored(dataset: str):
    scorer = Scorer.load(dataset)
    raw = {s: load_split(CFG, s, dataset=dataset) for s in ("valid", "test")}
    proba = {s: scorer.score(df) for s, df in raw.items()}
    return scorer, raw, proba


def db() -> sqlite3.Connection:
    path = data_paths(CFG).ensure().root / "analyst_decisions.sqlite"
    con = sqlite3.connect(path)
    con.execute("""CREATE TABLE IF NOT EXISTS decisions (
        dataset TEXT, transaction_id INTEGER, status TEXT, note TEXT, decided_at TEXT,
        PRIMARY KEY (dataset, transaction_id))""")
    return con


def decisions(dataset: str) -> pd.DataFrame:
    with db() as con:
        return pd.read_sql("SELECT transaction_id, status, note FROM decisions WHERE dataset = ?",
                           con, params=(dataset,))


def save_decision(dataset: str, tx_id: int, status: str, note: str) -> None:
    with db() as con:
        con.execute("INSERT OR REPLACE INTO decisions VALUES (?, ?, ?, ?, ?)",
                    (dataset, int(tx_id), status, note, datetime.now(timezone.utc).isoformat()))


# --------------------------------------------------------------------------- sidebar

available = [d for d in DATASETS if (model_dir(d) / "lightgbm.joblib").exists()]
if not available:
    st.error("No trained model found. Run `make data data-ulb train` first.")
    st.stop()

with st.sidebar:
    dataset = st.selectbox("Dataset", available, format_func=DATASETS.get)
    st.subheader("Business costs")
    c = CFG["costs"]
    review = st.slider("Analyst review per alert ($)", 0.0, 50.0, float(c["review_cost"]), 0.5)
    fee = st.slider("Chargeback fee per missed fraud ($)", 0.0, 100.0, float(c["chargeback_fee"]), 1.0)
    friction = st.slider("Customer friction per false alarm ($)", 0.0, 50.0, float(c["friction_cost"]), 0.5)
    mult = st.slider("Share of fraud amount lost", 0.0, 1.0, float(c["fn_amount_multiplier"]), 0.05)
    show_truth = st.toggle("Show actual label (evaluation only)", value=False)

costs = Costs(fn_amount_multiplier=mult, chargeback_fee=fee, review_cost=review, friction_cost=friction)
scorer, raw, proba = load_scored(dataset)
amt = {s: raw[s]["TransactionAmt"].to_numpy(dtype=float) for s in raw}
y = {s: raw[s]["isFraud"].to_numpy() for s in raw}
threshold = best_threshold(y["valid"], proba["valid"], amt["valid"], costs)
if scorer.policy == "expected_loss":
    flagged = flag_by_expected_loss(proba["test"], amt["test"], costs)
    rule_text = "alert when probability x (amount + chargeback) exceeds the review cost"
else:
    flagged = proba["test"] >= threshold
    rule_text = f"threshold {threshold:.4f}, chosen on the validation period to minimise total cost"

# --------------------------------------------------------------------------- KPIs

res = outcome(y["test"], flagged, amt["test"], costs)
no_model = outcome(y["test"], np.zeros_like(y["test"]), amt["test"], costs)["total_cost"]
st.title("Fraud alert queue")
st.caption(f"{DATASETS[dataset]} · held-out test period · {rule_text}")

k = st.columns(5)
k[0].metric("Alerts", f"{res['alerts']:,}")
k[1].metric("Alert precision", f"{res['tp'] / max(res['alerts'], 1):.1%}")
k[2].metric("Frauds caught", f"{res['tp'] / max(res['tp'] + res['fn'], 1):.1%}")
k[3].metric("Fraud $ caught", f"${res['fraud_dollars_caught']:,.0f}")
k[4].metric("Total cost", f"${res['total_cost']:,.0f}", f"-${no_model - res['total_cost']:,.0f} vs no model",
            delta_color="inverse")

# --------------------------------------------------------------------------- cost curve

with st.expander("Why this threshold? Cost by threshold on the validation period"):
    curve = cost_curve(y["valid"], proba["valid"], amt["valid"], costs, thresholds=np.linspace(0, 1, 401))
    line = alt.Chart(curve).mark_line().encode(
        x=alt.X("threshold:Q", title="Alert threshold"),
        y=alt.Y("total_cost:Q", title="Total cost ($)"),
        tooltip=["threshold", "alerts", "tp", "fp", "fn", alt.Tooltip("total_cost:Q", format=",.0f")])
    rule = alt.Chart(pd.DataFrame({"threshold": [threshold]})).mark_rule(strokeDash=[4, 4]).encode(x="threshold:Q")
    st.altair_chart(line + rule, width="stretch")
    st.caption("A missed fraud costs the amount plus the chargeback fee; every alert costs a review. "
               "Accuracy would pick a much higher threshold and miss most fraud.")

# --------------------------------------------------------------------------- queue

queue = build_queue(raw["test"], proba["test"], flagged, costs, dataset)
dec = decisions(dataset)
queue = queue.merge(dec, how="left", left_on="TransactionID", right_on="transaction_id").drop(columns="transaction_id")
queue["status"] = queue["status"].fillna("open")

left, right = st.columns([3, 2])
with left:
    st.subheader("Queue")
    shown = st.multiselect("Status", STATUSES, default=["open"])
    view = queue[queue["status"].isin(shown)]
    cols = [c for c in view.columns if c != "note" and (show_truth or c != "actual_fraud")]
    st.dataframe(view[cols].head(500), hide_index=True, width="stretch",
                 column_config={"fraud_probability": st.column_config.ProgressColumn("fraud probability", min_value=0, max_value=1, format="%.3f"),
                                "expected_loss": st.column_config.NumberColumn("expected loss", format="$%.2f"),
                                "TransactionAmt": st.column_config.NumberColumn("amount", format="$%.2f")})
    st.caption(f"{len(view):,} alerts shown (first 500), highest expected loss first.")

with right:
    st.subheader("Review")
    if view.empty:
        st.info("Nothing left in this view.")
    else:
        tx_id = st.selectbox("Transaction", view["TransactionID"].head(500).tolist())
        row = raw["test"][raw["test"]["TransactionID"] == tx_id]
        alert = queue[queue["TransactionID"] == tx_id].iloc[0]
        st.write(f"**${alert['TransactionAmt']:,.2f}**, fraud probability **{alert['fraud_probability']:.3f}**, "
                 f"expected loss **${alert['expected_loss']:,.2f}**")
        if show_truth:
            st.write("Actual label: " + ("**fraud**" if alert["actual_fraud"] else "legit"))
        st.write("Top reasons for this score")
        st.dataframe(pd.DataFrame(scorer.reasons(row)[0]), hide_index=True, width="stretch")
        note = st.text_input("Note", value=alert["note"] if isinstance(alert["note"], str) else "")
        b = st.columns(3)
        for col, status in zip(b, ["confirmed fraud", "dismissed", "escalated"]):
            if col.button(status.capitalize(), width="stretch"):
                save_decision(dataset, tx_id, status, note)
                st.rerun()

if show_truth and not dec.empty:
    worked = queue[queue["status"].isin(["confirmed fraud", "dismissed"])]
    agree = ((worked["status"] == "confirmed fraud") == worked["actual_fraud"].astype(bool)).mean()
    st.caption(f"Analyst decisions so far: {len(worked):,}; agreement with actual labels {agree:.1%}.")
