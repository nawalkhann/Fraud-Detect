# ULB (European card transactions) data report

## Overview
- Transactions: 284,807 (36 columns after the identity join)
- Period: 2013-09-01 to 2013-09-02 (assumed reference date; TransactionDT is relative)
- Fraud: 492 transactions, rate 0.17%, $60,128 of $25,162,590 volume (0.24%)

## Out-of-time splits
| split   |        rows |   frauds |   fraud_rate |   first_hour |   last_hour |   fraud_dollars |
|:--------|------------:|---------:|-------------:|-------------:|------------:|----------------:|
| train   | 156380.0000 | 350.0000 |       0.0022 |       0.0000 |     29.0000 |      38970.5703 |
| valid   |  59860.0000 |  53.0000 |       0.0009 |      30.0000 |     38.0000 |      11756.3799 |
| test    |  68567.0000 |  89.0000 |       0.0013 |      39.0000 |     47.0000 |       9401.0205 |

## Fraud rate by 6-hour block
|   6-hour block |       rows |   frauds |   fraud_rate |
|---------------:|-----------:|---------:|-------------:|
|              0 | 12340.0000 |  55.0000 |       0.0045 |
|              6 | 35061.0000 |  91.0000 |       0.0026 |
|             12 | 46850.0000 |  71.0000 |       0.0015 |
|             18 | 50535.0000 |  64.0000 |       0.0013 |
|             24 | 11594.0000 |  69.0000 |       0.0060 |
|             30 | 35851.0000 |  27.0000 |       0.0008 |
|             36 | 49585.0000 |  63.0000 |       0.0013 |
|             42 | 42991.0000 |  52.0000 |       0.0012 |

## Transaction amount by class
| isFraud   |     count |   mean |    std |   min |   50% |    95% |     99% |      max |
|:----------|----------:|-------:|-------:|------:|------:|-------:|--------:|---------:|
| legit     | 284315.00 |  88.29 | 250.11 |  0.00 | 22.00 | 364.41 | 1016.97 | 25691.16 |
| fraud     |    492.00 | 122.21 | 256.68 |  0.00 |  9.25 | 640.90 | 1357.43 |  2125.87 |

## Missing values by column group
| group   |   columns |   mean_missing |   cols_over_90pct_missing |
|:--------|----------:|---------------:|--------------------------:|
| V       |   28.0000 |         0.0000 |                    0.0000 |

## Fraud rate by category (top 8 by volume)
## Drift (population stability index)
PSI under 0.1 is stable, 0.1 to 0.25 is a moderate shift, over 0.25 is a large shift.

| feature        |   psi_train_vs_valid |   psi_train_vs_test |
|:---------------|---------------------:|--------------------:|
| TransactionAmt |               0.0041 |              0.0053 |
| V1             |               1.5234 |              1.5300 |
| V3             |               1.2319 |              1.3045 |
| V4             |               0.1667 |              0.2164 |
| V10            |               0.0761 |              0.0639 |
| V12            |               0.0711 |              0.2682 |
| V14            |               0.0733 |              0.1116 |
| V17            |               0.0515 |              0.0597 |
