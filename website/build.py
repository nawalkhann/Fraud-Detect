"""Build the static project website into website/public from the model reports.

    python3 website/build.py https://fraud-detect-ml.vercel.app
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd

SITE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "https://fraud-detect-ml.vercel.app"
REPO = "https://github.com/nawalkhann/fraud-detect"
REPORTS = Path(__file__).resolve().parents[1] / "reports"
OUT = Path(__file__).parent / "public"
TODAY = date.today().isoformat()
NAME = "Fraud Detect"

CSS = """
:root{--bg:#fbfaf7;--fg:#1d2128;--muted:#5b6270;--line:#e3e0d8;--card:#fff;--accent:#0f6b5c;--accent2:#b5462f;--code:#f1efe9}
@media (prefers-color-scheme:dark){:root{--bg:#14171c;--fg:#e8e6e1;--muted:#a3a8b2;--line:#2c313a;--card:#1b1f26;--accent:#4fc0a8;--accent2:#e8826b;--code:#222730}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font:17px/1.65 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--accent)}a:hover{text-decoration-thickness:2px}
.wrap{max-width:860px;margin:0 auto;padding:0 16px}
header{border-bottom:1px solid var(--line);background:var(--card)}
header .wrap{display:flex;flex-wrap:wrap;align-items:center;gap:8px 20px;padding-top:12px;padding-bottom:12px}
.brand{font-weight:700;text-decoration:none;color:var(--fg);font-size:18px;display:flex;align-items:center;gap:8px}
nav{display:flex;flex-wrap:wrap;gap:4px 16px;font-size:15px}nav a{text-decoration:none;color:var(--muted);padding:6px 0}
nav a[aria-current]{color:var(--fg);font-weight:600}
main{padding:28px 0 48px}
h1{font-size:clamp(28px,5vw,40px);line-height:1.2;margin:8px 0 12px}
h2{font-size:24px;line-height:1.3;margin:36px 0 10px}h3{font-size:19px;margin:24px 0 6px}
.lede{font-size:19px;color:var(--muted);margin-top:0}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:24px 0}
.stat{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.stat b{display:block;font-size:28px;line-height:1.2;color:var(--accent)}.stat span{font-size:14px;color:var(--muted)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px;margin:16px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;text-decoration:none;color:var(--fg);display:block}
.card strong{color:var(--accent)}.card p{margin:6px 0 0;color:var(--muted);font-size:15px}
.table{overflow-x:auto;border:1px solid var(--line);border-radius:10px;margin:12px 0;background:var(--card)}
table{border-collapse:collapse;width:100%;font-size:15px;font-variant-numeric:tabular-nums}
th,td{padding:8px 12px;text-align:right;border-bottom:1px solid var(--line);white-space:nowrap}
th:first-child,td:first-child{text-align:left}thead th{background:var(--code);font-weight:600}tr:last-child td{border-bottom:0}
tr.hl td{font-weight:600;color:var(--accent)}
code{background:var(--code);padding:1px 5px;border-radius:4px;font-size:.9em}
pre{background:var(--code);padding:14px;border-radius:8px;overflow-x:auto;font-size:14px;line-height:1.5}
.note{border-left:3px solid var(--accent2);padding:4px 14px;color:var(--muted);margin:16px 0}
ol.steps{padding-left:22px}ol.steps li{margin:8px 0}
footer{border-top:1px solid var(--line);color:var(--muted);font-size:14px;padding:20px 0 32px}
footer .wrap{display:flex;flex-wrap:wrap;gap:8px 20px;justify-content:space-between}
.calc{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;margin:16px 0}
.calc .stats{grid-template-columns:repeat(2,minmax(0,1fr))}.calc .stat b{font-size:22px}.calc label{font-weight:600;display:block;margin:8px 0 4px}.calc input[type=range]{width:100%}
.seg{display:flex;gap:8px;flex-wrap:wrap}.seg button{font:inherit;padding:6px 14px;border-radius:8px;border:1px solid var(--line);background:var(--bg);color:var(--fg);cursor:pointer;min-height:40px}
.seg button[aria-pressed=true]{background:var(--accent);color:var(--bg);border-color:var(--accent)}
svg.chart{width:100%;height:auto;display:block;margin-top:12px}
.breadcrumb{font-size:14px;color:var(--muted)}
"""

LOGO = ('<svg width="22" height="22" viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="7" fill="#0f6b5c"/>'
        '<path d="M9 21l5-6 4 4 6-9" stroke="#fff" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>')

NAV = [("/", "Home"), ("/how-it-works", "How it works"), ("/results", "Results"),
       ("/threshold-calculator", "Threshold calculator"), ("/guides", "Guides"), ("/about", "About")]

PAGES = []  # (path, priority) for the sitemap


def page(path, title, description, keywords, body, *, schema=None, priority="0.8", crumbs=None):
    url = SITE + (path if path != "/" else "/")
    nav = "".join(f'<a href="{h}"{" aria-current=page" if h == path or (h != "/" and path.startswith(h + "/")) else ""}>{t}</a>'
                  for h, t in NAV)
    ld = [{"@context": "https://schema.org", "@type": "WebSite", "name": NAME, "url": SITE + "/"}] if path == "/" else []
    if schema:
        ld.append(schema)
    if crumbs:
        ld.append({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": SITE + h} for i, (h, n) in enumerate(crumbs)]})
    ld_html = "".join(f'<script type="application/ld+json">{json.dumps(x)}</script>' for x in ld)
    crumb_html = ""
    if crumbs:
        crumb_html = '<p class="breadcrumb">' + " / ".join(
            f'<a href="{h}">{n}</a>' if i < len(crumbs) - 1 else n for i, (h, n) in enumerate(crumbs)) + "</p>"
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<meta name="keywords" content="{keywords}">
<meta name="robots" content="index, follow">
<link rel="canonical" href="{url}">
<meta property="og:type" content="{"article" if path.startswith("/guides/") else "website"}">
<meta property="og:site_name" content="{NAME}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{url}">
<meta name="twitter:card" content="summary">
<meta name="theme-color" content="#0f6b5c">
<!--GSC-->
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<style>{CSS}</style>
{ld_html}
</head>
<body>
<header><div class="wrap"><a class="brand" href="/">{LOGO}{NAME}</a><nav aria-label="Main">{nav}</nav></div></header>
<main><div class="wrap">
{crumb_html}
{body}
</div></main>
<footer><div class="wrap"><span>{NAME}: cost-sensitive fraud detection on real transaction data.</span>
<span><a href="{REPO}">Source code on GitHub</a> · <a href="/about">About the data</a> · <a href="/sitemap.xml">Sitemap</a></span></div></footer>
</body>
</html>
"""
    target = OUT / ("index.html" if path == "/" else path.strip("/") + ".html")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(re.sub(r"\n\s*", "\n", html))
    PAGES.append((path, priority))


def table(headers, rows, hl=None):
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join(f'<tr{" class=hl" if i == hl else ""}>' + "".join(f"<td>{c}</td>" for c in r) + "</tr>"
                   for i, r in enumerate(rows))
    return f'<div class="table"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def article(headline, description, path):
    return {"@context": "https://schema.org", "@type": "Article", "headline": headline, "description": description,
            "datePublished": TODAY, "dateModified": TODAY, "mainEntityOfPage": SITE + path,
            "author": {"@type": "Person", "name": "Nawal", "url": "https://github.com/nawalkhann"}}


# --------------------------------------------------------------------------- pages

def home():
    body = f"""
<h1>Fraud detection that minimises cost, not just errors</h1>
<p class="lede">An end-to-end machine learning system trained on two real, labelled transaction datasets. It picks who to alert
by the dollars at risk, explains every alert, and ships with a scoring API, an analyst queue, CI and drift monitoring.</p>
<div class="stats">
<div class="stat"><b>74%</b><span>fraud losses saved on the IEEE-CIS test month vs no model</span></div>
<div class="stat"><b>83%</b><span>of fraud dollars caught on unseen e-commerce data</span></div>
<div class="stat"><b>0.917</b><span>ROC-AUC on the held-out month (PR-AUC 0.573)</span></div>
<div class="stat"><b>875k</b><span>real transactions across two public datasets</span></div>
</div>
<h2>What this project does</h2>
<p>Card and e-commerce fraud is rare (3.5% of transactions in IEEE-CIS, 0.17% in the ULB card data), so a model that
predicts "not fraud" for everything is over 96% accurate and catches nothing. This project treats fraud detection as a cost
problem instead. A missed fraud costs the transaction amount plus a $15 chargeback fee, and every alert costs $5 of analyst
time. The model scores each transaction, and the system alerts only when the expected loss is larger than the cost of
reviewing it.</p>
<p>Everything is evaluated out of time: the model trains on earlier months, is tuned on the next month and is reported on a
final month it has never seen, which is how fraud models actually meet new data in production.</p>
<div class="cards">
<a class="card" href="/how-it-works"><strong>How it works</strong><p>Data, out-of-time splits, features, LightGBM, the cost rule, the API and monitoring.</p></a>
<a class="card" href="/results"><strong>Results</strong><p>Accuracy, precision, recall, PR-AUC and dollars for every threshold policy on both datasets.</p></a>
<a class="card" href="/threshold-calculator"><strong>Threshold calculator</strong><p>Move the cut-off and watch alerts, frauds caught and total cost change on the real test month.</p></a>
<a class="card" href="/guides/why-accuracy-fails-for-fraud-detection"><strong>Why accuracy fails</strong><p>A plain-language guide to evaluating models on imbalanced fraud data.</p></a>
</div>
<h2>Built like a production system</h2>
<ul>
<li><strong>Two real datasets:</strong> IEEE-CIS (590,540 Vesta e-commerce transactions) and ULB (284,807 European card transactions).</li>
<li><strong>Models:</strong> LightGBM against a logistic regression baseline, with train, validation and test metrics to expose overfitting.</li>
<li><strong>Decisions:</strong> an amount-aware expected-loss rule that beat every single fixed threshold on both datasets.</li>
<li><strong>Explanations:</strong> the top three reasons for every alert, from SHAP values.</li>
<li><strong>Serving:</strong> a FastAPI <code>/score</code> endpoint and a Streamlit alert queue for analysts.</li>
<li><strong>Operations:</strong> Docker, GitHub Actions CI, a model registry file per run and a PSI drift check.</li>
</ul>
<p><a href="{REPO}">Read the source code on GitHub</a>.</p>
"""
    page("/", "Fraud Detect: Cost-Sensitive Fraud Detection with Machine Learning",
         "End-to-end fraud detection on real IEEE-CIS and ULB credit card data. LightGBM, cost-based thresholds, "
         "explainable alerts, FastAPI and drift monitoring. Saves 74% of fraud losses.",
         "fraud detection, machine learning fraud detection, credit card fraud detection, IEEE-CIS fraud, "
         "cost-sensitive learning, LightGBM, fraud alert queue, imbalanced classification",
         body, priority="1.0",
         schema={"@context": "https://schema.org", "@type": "SoftwareSourceCode", "name": NAME, "codeRepository": REPO,
                 "programmingLanguage": "Python", "description": "Cost-sensitive fraud detection pipeline on real data.",
                 "author": {"@type": "Person", "name": "Nawal", "url": "https://github.com/nawalkhann"}})


def how():
    body = """
<h1>How the fraud detection pipeline works</h1>
<p class="lede">From raw transactions to a ranked alert queue, in six steps. Each step is a module in the repository and is covered by tests.</p>
<h2>1. Real, labelled data</h2>
<p><strong>IEEE-CIS</strong> holds 590,540 e-commerce transactions from Vesta over about six months, with more than 400 columns:
amount, product code, card and address fields, email domains, device data, counting features (C1 to C14), time deltas (D1 to D15)
and 339 engineered Vesta features. A separate identity table covers 24% of transactions, and those transactions have a fraud
rate of 7.85% against 2.09% without one. <strong>ULB</strong> holds 284,807 European card transactions from two days in September 2013,
whose 28 features are PCA components, so it tests whether the decision rule generalises to a very different fraud profile.</p>
<h2>2. Out-of-time validation</h2>
<p>Random train/test splits leak the future into training and overstate performance. Every split here is by time:</p>
<ul>
<li>IEEE-CIS: train on days 1 to 119, tune on days 120 to 151, report on days 152 to 182.</li>
<li>ULB: train on hours 0 to 29, tune on hours 30 to 38, report on hours 39 to 47.</li>
</ul>
<p>Thresholds and policies are chosen on the validation period and applied unchanged to the test period.</p>
<h2>3. Features fitted on training data only</h2>
<p>Frequency encodings for high-cardinality fields such as <code>card1</code> and email domain, and a customer proxy built from card,
address and the account-start date (<code>card1 + addr1 + (day − D1)</code>). Per-customer means and standard deviations of amount,
distance and counting features let the model ask "is this unusual for this customer?" All statistics come from the training months,
so no information leaks from the future.</p>
<h2>4. LightGBM against a baseline</h2>
<p>A gradient boosted tree model (LightGBM, early stopping on log loss, no class reweighting so probabilities stay calibrated)
is compared with a regularised logistic regression. On IEEE-CIS the test PR-AUC is 0.573 for LightGBM against 0.164 for the
baseline. Train PR-AUC is 0.99, so the model does overfit; the out-of-time test numbers are the honest ones.</p>
<h2>5. A decision rule based on cost</h2>
<p>A probability is not a decision. The production rule alerts on a transaction when</p>
<pre>p(fraud) × (amount + chargeback fee)  &gt;  review cost</pre>
<p>so a $2,000 order is reviewed at a much lower probability than a $10 one. With a $15 chargeback and a $5 review, this
rule cost $138,481 on the test month against $172,751 for the best single threshold and $409,060 for the usual 0.5 cut-off.
See it for yourself in the <a href="/threshold-calculator">threshold calculator</a> or read
<a href="/guides/choosing-a-fraud-threshold-by-cost">how to choose a threshold by cost</a>.</p>
<h2>6. Serving and monitoring</h2>
<ul>
<li><strong>Scoring API:</strong> FastAPI <code>POST /score</code> returns the probability, the alert decision, the expected loss and the top three reasons from SHAP values.</li>
<li><strong>Alert queue:</strong> a Streamlit dashboard ranks alerts by expected loss, lets analysts change costs live and records confirm or dismiss decisions.</li>
<li><strong>Model registry:</strong> each training run writes metadata with the git commit, costs, thresholds and test metrics.</li>
<li><strong>Drift check:</strong> the population stability index and mean score shift against a training reference; the job exits non-zero when drift crosses the alert level.</li>
<li><strong>Delivery:</strong> Docker and docker-compose for the API and dashboard, and GitHub Actions running the tests on every push.</li>
</ul>
<pre>make install
make data &amp;&amp; make data-ulb
make train      # writes reports/model_report_{ieee,ulb}.md
make serve      # scoring API on :8000
make dashboard  # analyst alert queue
make drift BATCH=recent.parquet</pre>
"""
    d = "How the Fraud Detect pipeline works: out-of-time splits, customer features, LightGBM, an expected-loss alert rule, FastAPI scoring and PSI drift monitoring."
    page("/how-it-works", "How the Fraud Detection Pipeline Works | Fraud Detect", d,
         "fraud detection pipeline, out-of-time validation, feature engineering fraud, LightGBM fraud model, "
         "expected loss, FastAPI model serving, model drift PSI, MLOps",
         body, schema=article("How the fraud detection pipeline works", d, "/how-it-works"),
         crumbs=[("/", "Home"), ("/how-it-works", "How it works")])


def results():
    ieee = [
        ["Expected-loss rule (production)", "8,943", "2,131 (68%)", "24%", "$79,021", "$138,481"],
        ["Best single threshold (0.014)", "17,093", "2,622 (84%)", "15%", "$79,906", "$172,751"],
        ["Max F1 threshold (0.19)", "2,278", "1,511 (49%)", "66%", "$323,788", "$359,223"],
        ["Max accuracy threshold (0.28)", "1,849", "1,386 (45%)", "75%", "$342,051", "$377,216"],
        ["Default 0.5 cut-off", "1,344", "1,140 (37%)", "85%", "$372,730", "$409,060"],
        ["No model", "0", "0 (0%)", "–", "$477,356", "$524,066"],
    ]
    ulb = [
        ["Expected-loss rule (production)", "149", "68 (76%)", "46%", "$2,407", "$3,467"],
        ["Best single threshold (0.006)", "317", "75 (84%)", "24%", "$2,375", "$4,170"],
        ["Max F1 threshold (0.27)", "86", "67 (75%)", "78%", "$2,644", "$3,404"],
        ["Max accuracy threshold (0.88)", "51", "51 (57%)", "100%", "$4,732", "$5,557"],
        ["Default 0.5 cut-off", "75", "67 (75%)", "89%", "$2,644", "$3,349"],
        ["No model", "0", "0 (0%)", "–", "$9,401", "$10,736"],
    ]
    hdr = ["Policy", "Alerts", "Frauds caught", "Precision", "Fraud $ missed", "Total cost"]
    auc_hdr = ["Model / split", "ROC-AUC", "PR-AUC", "Brier", "Log loss"]
    ieee_auc = [["LightGBM train", "0.9997", "0.9941", "0.0031", "0.0155"],
                ["LightGBM valid", "0.9443", "0.6758", "0.0183", "0.0743"],
                ["LightGBM test", "0.9168", "0.5729", "0.0212", "0.0890"],
                ["Logistic test", "0.7999", "0.1637", "0.0421", "0.3467"]]
    ulb_auc = [["LightGBM train", "1.0000", "0.9992", "0.0001", "0.0004"],
               ["LightGBM valid", "0.9868", "0.7562", "0.0003", "0.0020"],
               ["LightGBM test", "0.9834", "0.8017", "0.0004", "0.0025"],
               ["Logistic test", "0.9726", "0.6528", "0.0008", "0.0038"]]
    body = f"""
<h1>Fraud detection results on real data</h1>
<p class="lede">All numbers are on the final, held-out time period, using thresholds chosen on the period before it.
Total cost = fraud dollars missed + $15 chargeback per missed fraud + $5 per alert reviewed.</p>
<h2>IEEE-CIS: Vesta e-commerce, last month (89,326 transactions, 3,114 frauds)</h2>
{table(hdr, ieee, hl=0)}
<p>The expected-loss rule saves 74% of the no-model cost and catches 83% of fraud dollars. It uses half the alerts of the best
single threshold for a lower total cost, because it spends review time on the expensive transactions. The thresholds that
maximise accuracy or F1 look better on paper and miss more than $320,000 of fraud.</p>
{table(auc_hdr, ieee_auc, hl=2)}
<p class="note">The model overfits: train PR-AUC is 0.99 against 0.57 on the test month. The test numbers are the ones to trust, and
the gap is the main thing to work on next (fewer V features, stronger regularisation, more customer history).</p>
<h2>ULB: European card transactions, last 9 hours (68,567 transactions, 89 frauds)</h2>
{table(hdr, ulb, hl=0)}
<p>The expected-loss rule was the cheapest policy on validation and saves 68% on test. On test the 0.5 cut-off came out $118 cheaper,
which is within noise when there are only 89 frauds; the best single threshold from validation did worse ($4,170), which is why the
production rule is chosen by validation cost rather than tuned to one number.</p>
{table(auc_hdr, ulb_auc, hl=2)}
<h2>What drives the IEEE-CIS model</h2>
<p>The strongest features by LightGBM gain are customer-level aggregates (<code>uid_C13_mean</code>, <code>uid_TransactionAmt_mean</code>,
<code>uid_C13_std</code>), Vesta's engineered features <code>V257</code> and <code>V258</code>, the counting features <code>C1</code>,
<code>C13</code> and <code>C14</code>, how common the card is (<code>card1_freq</code>) and the device string. Customer behaviour over time
matters more than any single field on the transaction.</p>
<p>Try other cut-offs in the <a href="/threshold-calculator">threshold calculator</a>, or see the full reports in the
<a href="https://github.com/nawalkhann/fraud-detect/tree/main/reports">repository</a>.</p>
"""
    d = "Test results for fraud detection on IEEE-CIS and ULB credit card data: precision, recall, PR-AUC, ROC-AUC and total cost for each threshold policy. 74% of losses saved."
    page("/results", "Fraud Detection Model Results: Precision, Recall and Cost | Fraud Detect", d,
         "fraud detection results, fraud model accuracy, precision recall fraud, PR-AUC, ROC-AUC, IEEE-CIS results, "
         "credit card fraud detection accuracy, LightGBM vs logistic regression",
         body, schema=article("Fraud detection model results", d, "/results"),
         crumbs=[("/", "Home"), ("/results", "Results")])


def calculator():
    data = {}
    for ds in ("ieee", "ulb"):
        c = pd.read_csv(REPORTS / f"cost_curve_{ds}.csv")
        c = c.iloc[::max(1, len(c) // 150)]
        data[ds] = {k: [round(float(v), 4 if k == "threshold" else 0) for v in c[k]] for k in ("threshold", "alerts", "tp", "fn", "total_cost")}
    data["ieee"]["frauds"], data["ulb"]["frauds"] = 3114, 89
    data["ieee"]["el"], data["ulb"]["el"] = 138481, 3467
    body = f"""
<h1>Fraud threshold calculator</h1>
<p class="lede">Move the cut-off and see what it does on a real test period the model never trained on: how many alerts
analysts must review, how many frauds are caught and what it all costs.</p>
<div class="calc">
<div class="seg" role="group" aria-label="Dataset"><button type="button" data-ds="ieee" aria-pressed="true">IEEE-CIS e-commerce</button><button type="button" data-ds="ulb" aria-pressed="false">ULB card data</button></div>
<label for="t">Alert when fraud probability is at least <span id="tv"></span></label>
<input id="t" type="range" min="0" max="1000" value="500" aria-describedby="tv">
<div class="stats" aria-live="polite">
<div class="stat"><b id="a"></b><span>alerts to review</span></div>
<div class="stat"><b id="c"></b><span>frauds caught</span></div>
<div class="stat"><b id="k"></b><span>total cost</span></div>
<div class="stat"><b id="e"></b><span>expected-loss rule, for comparison</span></div>
</div>
<svg class="chart" id="chart" viewBox="0 0 640 260" role="img" aria-label="Total cost by threshold"></svg>
</div>
<h2>How to read this</h2>
<p>A low cut-off alerts on almost everything, so review cost dominates. A high cut-off alerts on almost nothing, so missed fraud
dominates. The cheapest single cut-off sits in between, and it is usually far below 0.5 because a missed fraud costs much more
than a review. On IEEE-CIS the amount-aware expected-loss rule beats every single cut-off
because it uses a lower bar for larger transactions. On the small ULB set a few cut-offs come out slightly cheaper on test, within
the noise of 89 frauds. Read the full reasoning in <a href="/guides/choosing-a-fraud-threshold-by-cost">choosing a fraud threshold by cost</a>.</p>
<p>Costs: missed fraud = amount + $15 chargeback, alert = $5 review. The curve is computed on the IEEE-CIS last month (days 152 to 182)
and the ULB last 9 hours.</p>
<script>
const D={json.dumps(data, separators=(",", ":"))};
let ds="ieee";const $=id=>document.getElementById(id);const f=n=>n.toLocaleString("en-US");
function idx(t){{const T=D[ds].threshold;let i=0;while(i<T.length-1&&T[i+1]<=t)i++;return i}}
function draw(t){{const d=D[ds],W=640,H=260,P=44,cap=d.total_cost[d.total_cost.length-1]*1.6;
const x=v=>P+v*(W-P-10),y=v=>H-28-Math.min(v,cap)/cap*(H-48);
let p=d.threshold.map((v,i)=>(i?"L":"M")+x(v).toFixed(1)+" "+y(d.total_cost[i]).toFixed(1)).join("");
const i=idx(t),mn=Math.min(...d.total_cost),j=d.total_cost.indexOf(mn);
$("chart").innerHTML=`<line x1="${{P}}" y1="${{H-28}}" x2="${{W-10}}" y2="${{H-28}}" stroke="currentColor" opacity=".3"/>`+
`<text x="${{P}}" y="${{H-8}}" font-size="15" fill="currentColor">0</text><text x="${{W-30}}" y="${{H-8}}" font-size="15" fill="currentColor">1.0</text>`+
`<text x="${{(W)/2-40}}" y="${{H-8}}" font-size="15" fill="currentColor">cut-off</text>`+
`<text x="4" y="16" font-size="15" fill="currentColor">total cost</text>`+
`<line x1="${{P}}" x2="${{W-10}}" y1="${{y(d.el)}}" y2="${{y(d.el)}}" stroke="#b5462f" stroke-dasharray="4 4"/>`+
`<path d="${{p}}" fill="none" stroke="#0f6b5c" stroke-width="2.5"/>`+
`<circle cx="${{x(d.threshold[j])}}" cy="${{y(mn)}}" r="4" fill="#0f6b5c"/>`+
`<line x1="${{x(t)}}" x2="${{x(t)}}" y1="20" y2="${{H-28}}" stroke="currentColor" opacity=".5"/>`+
`<circle cx="${{x(t)}}" cy="${{y(d.total_cost[i])}}" r="6" fill="#b5462f"/>`}}
function upd(){{const t=$("t").value/1000,d=D[ds],i=idx(t);$("tv").textContent=t.toFixed(3);
$("a").textContent=f(d.alerts[i]);$("c").textContent=f(d.tp[i])+" of "+f(d.frauds);
$("k").textContent="$"+f(d.total_cost[i]);$("e").textContent="$"+f(d.el);draw(t)}}
document.querySelectorAll(".seg button").forEach(b=>b.onclick=()=>{{ds=b.dataset.ds;
document.querySelectorAll(".seg button").forEach(o=>o.setAttribute("aria-pressed",o===b));upd()}});
$("t").oninput=upd;upd();
</script>
"""
    page("/threshold-calculator", "Fraud Detection Threshold Calculator: Cost vs Cut-off | Fraud Detect",
         "Interactive calculator: choose a fraud probability cut-off and see alerts, frauds caught and total cost on real "
         "held-out IEEE-CIS and credit card test data.",
         "fraud threshold, classification threshold calculator, cost-sensitive threshold, fraud alert threshold, "
         "precision recall tradeoff, optimal cut-off",
         body, crumbs=[("/", "Home"), ("/threshold-calculator", "Threshold calculator")])


GUIDES = [
    ("why-accuracy-fails-for-fraud-detection", "Why Accuracy Fails for Fraud Detection (and What to Use Instead)",
     "Why a 97% accurate fraud model can be useless, and how to evaluate fraud detection with precision, recall, PR-AUC and dollar cost instead.",
     "accuracy paradox, imbalanced data, fraud detection metrics, precision vs recall, PR-AUC vs ROC-AUC, evaluating fraud models",
     """
<h1>Why accuracy fails for fraud detection</h1>
<p class="lede">On real fraud data, the most accurate threshold was one of the most expensive. Here is why, and what to measure instead.</p>
<h2>The accuracy paradox</h2>
<p>In the IEEE-CIS data 3.5% of transactions are fraud. A "model" that says every transaction is legitimate is 96.5% accurate and
catches nothing. On the ULB card data, where 0.17% is fraud, the same trick scores 99.8%. Accuracy rewards the majority class, and in
fraud the majority class is the one nobody cares about.</p>
<p>It gets worse with a real model. On the IEEE-CIS test month, the threshold that maximised accuracy (0.28) reached 97.6% accuracy,
caught only 45% of frauds and cost $377,216. The cost-based rule had lower accuracy (91.3%), caught 68% of frauds and 83% of fraud
dollars, and cost $138,481. Accuracy pointed at the wrong answer by almost a quarter of a million dollars.</p>
<h2>Metrics that work on imbalanced data</h2>
<ul>
<li><strong>Precision:</strong> of the transactions you alerted on, how many were fraud. This is the analysts' hit rate.</li>
<li><strong>Recall:</strong> of all frauds, how many you caught. Track it by count and by dollars, because a missed $3,000 fraud is not the same as a missed $3 one.</li>
<li><strong>PR-AUC:</strong> the area under the precision-recall curve. Unlike ROC-AUC it is not flattered by the huge number of easy legitimate transactions, so it is the better single number for comparing fraud models. Our LightGBM model scores ROC-AUC 0.917 but PR-AUC 0.573 on the same data.</li>
<li><strong>Total cost:</strong> fraud dollars missed, plus chargeback fees, plus review time. This is the metric the business pays, and it is the one to choose a threshold with.</li>
</ul>
<h2>Check for overfitting with time</h2>
<p>Evaluate on a later period than you trained on. Our model's PR-AUC was 0.99 on its training months, 0.68 on the next month and
0.57 on the month after. A random split would have hidden most of that gap.</p>
<h2>A checklist for evaluating a fraud model</h2>
<ol class="steps">
<li>Split by time, never randomly.</li>
<li>Report PR-AUC alongside ROC-AUC.</li>
<li>Put a dollar cost on a missed fraud and on a review.</li>
<li>Choose the threshold (or decision rule) on the validation period by total cost.</li>
<li>Report recall in dollars, precision and alert volume at that threshold on the test period.</li>
</ol>
<p>Next: <a href="/guides/choosing-a-fraud-threshold-by-cost">how to choose a fraud threshold by cost</a>, or see the
<a href="/results">full results</a>.</p>
"""),
    ("choosing-a-fraud-threshold-by-cost", "How to Choose a Fraud Detection Threshold by Cost",
     "A practical guide to setting a fraud alert threshold from business costs: the expected-loss rule, why 0.5 is wrong, and real results on IEEE-CIS data.",
     "fraud detection threshold, cost-sensitive classification, expected loss, decision threshold, chargeback cost, alert review cost",
     """
<h1>How to choose a fraud detection threshold by cost</h1>
<p class="lede">A fraud model outputs a probability. Turning it into a yes-or-no alert is a business decision, and the default 0.5 is almost never right.</p>
<h2>Start with what each mistake costs</h2>
<ul>
<li><strong>Missed fraud (false negative):</strong> you lose the transaction amount and pay a chargeback fee. This project uses amount + $15.</li>
<li><strong>Alert (true or false positive):</strong> an analyst spends time reviewing it. This project uses $5.</li>
<li><strong>False alarm friction:</strong> optionally, the cost of annoying a good customer. Set to $0 here, but worth adding if you block payments rather than review them.</li>
</ul>
<h2>Option 1: the cheapest single threshold</h2>
<p>Score the validation period, try every cut-off from 0 to 1, add up the cost at each, and keep the cheapest. On IEEE-CIS this landed at
0.014, far below 0.5, because missing an average $150 fraud is about 30 times more expensive than a review. On the test month it cost
$172,751 against $409,060 for the 0.5 cut-off. You can try this yourself in the <a href="/threshold-calculator">threshold calculator</a>.</p>
<h2>Option 2: the expected-loss rule</h2>
<p>A single threshold treats a $5 purchase and a $5,000 purchase the same. The expected-loss rule alerts when the expected cost of letting the
transaction through is higher than the cost of reviewing it:</p>
<pre>alert if  p × (amount + chargeback)  &gt;  review cost + (1 − p) × friction</pre>
<p>With a $5 review and $15 chargeback, a $10 order needs a fraud probability above 20% to be reviewed, while a $1,000 order needs only
0.5%. On the IEEE-CIS test month this rule cost <strong>$138,481</strong>, 20% less than the best single threshold, with roughly half the alerts.</p>
<h2>Two things that make it work</h2>
<ol class="steps">
<li><strong>Calibrated probabilities.</strong> The rule multiplies the probability by dollars, so the probability has to mean what it says. Avoid heavy class reweighting, or recalibrate afterwards.</li>
<li><strong>Choose on validation, report on test.</strong> On the small ULB set, the best validation threshold did worse on test than the 0.5 cut-off. Pick the policy by validation cost and accept the test result, rather than tuning to the test set.</li>
</ol>
<h2>When to revisit the threshold</h2>
<p>Recompute when costs change (a new chargeback fee, more analysts), when the fraud rate moves, or when a drift check fires. This project's
drift job compares feature distributions and the mean score with a training reference, using the population stability index.</p>
<p>See <a href="/how-it-works">how the whole pipeline fits together</a> or the <a href="/results">results for every policy</a>.</p>
"""),
]


def guides():
    cards = "".join(f'<a class="card" href="/guides/{s}"><strong>{t}</strong><p>{d}</p></a>' for s, t, d, _, _ in GUIDES)
    page("/guides", "Fraud Detection Guides: Metrics, Thresholds and Costs | Fraud Detect",
         "Practical guides to building fraud detection models: evaluating imbalanced data, choosing a threshold by cost and "
         "measuring what fraud really costs.",
         "fraud detection guide, fraud analytics, machine learning guide, imbalanced classification, fraud threshold",
         f'<h1>Fraud detection guides</h1><p class="lede">Lessons from building this project on real data, written for analysts and engineers.</p><div class="cards">{cards}</div>',
         crumbs=[("/", "Home"), ("/guides", "Guides")], priority="0.7")
    for s, t, d, k, body in GUIDES:
        path = f"/guides/{s}"
        page(path, f"{t} | Fraud Detect", d, k, body, schema=article(t, d, path),
             crumbs=[("/", "Home"), ("/guides", "Guides"), (path, t.split(" (")[0])], priority="0.7")


def about():
    body = f"""
<h1>About the project and the data</h1>
<p>Fraud Detect is an open-source portfolio project by <a href="https://github.com/nawalkhann">Nawal</a>, built to show
what an end-to-end fraud detection system looks like on real data: honest out-of-time evaluation, decisions driven by cost,
explanations for analysts and the engineering needed to run it.</p>
<h2>Datasets</h2>
<h3>IEEE-CIS Fraud Detection</h3>
<p>Real e-commerce transactions provided by Vesta Corporation for the IEEE Computational Intelligence Society
<a href="https://www.kaggle.com/c/ieee-fraud-detection">Kaggle competition</a>. 590,540 labelled transactions, 3.5% fraud, joined with an identity
table. This site shows only aggregate results from it; no transaction-level data is published.</p>
<h3>ULB Credit Card Fraud</h3>
<p>284,807 transactions made by European cardholders over two days in September 2013, released by the Machine Learning Group of the
Université Libre de Bruxelles (<a href="https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud">dataset page</a>). 492 frauds (0.17%).
Features V1 to V28 are PCA components; only time and amount are in their original form.</p>
<h2>Source code</h2>
<p>The full pipeline, tests, Dockerfile and CI configuration are on <a href="{REPO}">GitHub</a>. To reproduce the results, download both
datasets, then run <code>make data</code>, <code>make data-ulb</code> and <code>make train</code>.</p>
<h2>Limitations</h2>
<ul>
<li>The cost figures ($15 chargeback, $5 review) are assumptions; change them in <code>configs/default.yaml</code> to match a real business.</li>
<li>The IEEE-CIS model overfits (train PR-AUC 0.99, test 0.57).</li>
<li>The ULB test period has only 89 frauds, so differences of a few hundred dollars between policies are noise.</li>
</ul>
"""
    page("/about", "About Fraud Detect: IEEE-CIS and ULB Credit Card Fraud Data",
         "About the Fraud Detect project: the IEEE-CIS (Vesta) and ULB credit card fraud datasets, source code, assumptions and limitations.",
         "IEEE-CIS dataset, ULB credit card fraud dataset, Vesta fraud data, fraud detection project, open source fraud detection",
         body, crumbs=[("/", "Home"), ("/about", "About")], priority="0.5")


def extras():
    page("/404", "Page not found | Fraud Detect", "This page does not exist.", "fraud detect",
         '<h1>Page not found</h1><p>That page does not exist. Try the <a href="/">home page</a>, '
         '<a href="/results">results</a> or <a href="/guides">guides</a>.</p>')
    PAGES.pop()  # keep 404 out of the sitemap
    (OUT / "404.html").write_text((OUT / "404.html").read_text().replace(
        '<meta name="robots" content="index, follow">', '<meta name="robots" content="noindex">'))
    (OUT / "favicon.svg").write_text(LOGO.replace(' width="22" height="22"', ' xmlns="http://www.w3.org/2000/svg"').replace(' aria-hidden="true"', ""))
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n")
    urls = "".join(f"<url><loc>{SITE}{p if p != '/' else '/'}</loc><lastmod>{TODAY}</lastmod><priority>{pr}</priority></url>"
                   for p, pr in PAGES)
    (OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
                                     f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n')
    (OUT / "vercel.json").write_text(json.dumps({
        "cleanUrls": True, "trailingSlash": False,
        "headers": [{"source": "/(.*)", "headers": [
            {"key": "X-Content-Type-Options", "value": "nosniff"},
            {"key": "Cache-Control", "value": "public, max-age=0, must-revalidate"}]},
            {"source": "/favicon.svg", "headers": [{"key": "Cache-Control", "value": "public, max-age=604800"}]}]}, indent=1))


if __name__ == "__main__":
    import shutil
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir()
    home(); how(); results(); calculator(); guides(); about(); extras()
    print(f"built {len(PAGES)} pages for {SITE}")
