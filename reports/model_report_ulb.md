# Model report: ulb

Costs: missed fraud = amount x 1.0 + $15 chargeback; every alert = $5 review; false alarm friction = $0.
Test set: 68,567 transactions, 89 frauds ($9,401). Thresholds are chosen on valid and applied unchanged to test.

Policies: `min_cost` is the single threshold with the lowest validation cost; `expected_loss` alerts when p x (amount + chargeback) > review cost, so the bar drops as the amount at risk grows. The production policy is whichever of the two was cheaper on validation.

## Headline (LightGBM, `expected_loss` policy, test split)
- Total cost **$3,467** vs **$10,736** with no model (67.7% saved).
- Catches 76.4% of frauds (68 of 89), 74.4% of fraud dollars, with 149 alerts (45.6% of alerts are fraud).
- Best LightGBM iteration: 278.

## Ranking quality and overfitting check (train vs valid vs test)
PR-AUC is the main metric under heavy imbalance. A large train-test gap means overfitting.

|                       |   roc_auc |   pr_auc |   brier |   log_loss |
|:----------------------|----------:|---------:|--------:|-----------:|
| ('lightgbm', 'train') |    1.0000 |   0.9992 |  0.0001 |     0.0004 |
| ('lightgbm', 'valid') |    0.9868 |   0.7562 |  0.0003 |     0.0020 |
| ('lightgbm', 'test')  |    0.9834 |   0.8017 |  0.0004 |     0.0025 |
| ('logistic', 'train') |    0.9789 |   0.7885 |  0.0009 |     0.0048 |
| ('logistic', 'valid') |    0.9646 |   0.5746 |  0.0006 |     0.0031 |
| ('logistic', 'test')  |    0.9726 |   0.6528 |  0.0008 |     0.0038 |

## Error at each threshold policy (test split)
`max_accuracy` shows why accuracy misleads: it barely flags anything.

|                               |   threshold |   accuracy |   precision |   recall |     f1 |   alerts |   tp |   fp |   fn |   fraud_dollars_missed |   valid_total_cost |   total_cost |
|:------------------------------|------------:|-----------:|------------:|---------:|-------:|---------:|-----:|-----:|-----:|-----------------------:|-------------------:|-------------:|
| ('lightgbm', 'default_0.5')   |      0.5000 |     0.9996 |      0.8933 |   0.7528 | 0.8171 |       75 |   67 |    8 |   22 |             2,644.2800 |         5,551.7101 |   3,349.2800 |
| ('lightgbm', 'max_accuracy')  |      0.8831 |     0.9994 |      1.0000 |   0.5730 | 0.7286 |       51 |   51 |    0 |   38 |             4,731.7800 |         7,548.9101 |   5,556.7800 |
| ('lightgbm', 'max_f1')        |      0.2668 |     0.9994 |      0.7791 |   0.7528 | 0.7657 |       86 |   67 |   19 |   22 |             2,644.2800 |         5,584.9401 |   3,404.2800 |
| ('lightgbm', 'min_cost')      |      0.0060 |     0.9963 |      0.2366 |   0.8427 | 0.3695 |      317 |   75 |  242 |   14 |             2,374.6900 |         5,382.7901 |   4,169.6900 |
| ('lightgbm', 'expected_loss') |    nan      |     0.9985 |      0.4564 |   0.7640 | 0.5714 |      149 |   68 |   81 |   21 |             2,407.0200 |         5,133.5001 |   3,467.0200 |
| ('logistic', 'default_0.5')   |      0.5000 |     0.9991 |      0.6812 |   0.5281 | 0.5949 |       69 |   47 |   22 |   42 |             5,767.4300 |         8,496.8301 |   6,742.4300 |
| ('logistic', 'max_accuracy')  |      0.1831 |     0.9989 |      0.5794 |   0.6966 | 0.6327 |      107 |   62 |   45 |   27 |             4,193.5600 |         5,848.2301 |   5,133.5600 |
| ('logistic', 'max_f1')        |      0.1831 |     0.9989 |      0.5794 |   0.6966 | 0.6327 |      107 |   62 |   45 |   27 |             4,193.5600 |         5,848.2301 |   5,133.5600 |
| ('logistic', 'min_cost')      |      0.0260 |     0.9970 |      0.2782 |   0.8315 | 0.4169 |      266 |   74 |  192 |   15 |             2,621.3400 |         5,458.5101 |   4,176.3400 |
| ('logistic', 'expected_loss') |    nan      |     0.9963 |      0.2158 |   0.7079 | 0.3307 |      292 |   63 |  229 |   26 |             2,768.4100 |         5,640.5601 |   4,618.4100 |

## Top features (LightGBM gain)

|                |        gain |
|:---------------|------------:|
| V14            | 35,600.9831 |
| V17            | 23,229.0736 |
| V10            |  9,828.9892 |
| V12            |  8,867.4632 |
| V4             |  4,012.4908 |
| V26            |  1,385.0637 |
| V8             |  1,238.1096 |
| TransactionAmt |  1,119.2954 |
| V3             |  1,010.9376 |
| V11            |    882.9337 |
| V13            |    865.7348 |
| V20            |    852.9848 |
| V21            |    848.7104 |
| V7             |    848.4988 |
| V19            |    825.9781 |
