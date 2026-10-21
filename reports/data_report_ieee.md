# IEEE-CIS (Vesta e-commerce) data report

## Overview
- Transactions: 590,540 (438 columns after the identity join)
- Period: 2017-12-02 to 2018-06-01 (assumed reference date; TransactionDT is relative)
- Fraud: 20,663 transactions, rate 3.50%, $3,083,845 of $79,738,944 volume (3.87%)
- With identity record: 24.4% of transactions (fraud rate 7.85% vs 2.09% without)

## Out-of-time splits
| split   |   rows |   frauds |   fraud_rate |   first_day |   last_day |   fraud_dollars |
|:--------|-------:|---------:|-------------:|------------:|-----------:|----------------:|
| train   | 410601 |    14419 |       0.0351 |           1 |        119 |         2094780 |
| valid   |  90613 |     3130 |       0.0345 |         120 |        151 |          511709 |
| test    |  89326 |     3114 |       0.0349 |         152 |        182 |          477356 |

## Fraud rate by month
| month   |   rows |   frauds |   fraud_rate |
|:--------|-------:|---------:|-------------:|
| 2017-12 | 134339 |     3401 |       0.0253 |
| 2018-01 |  92510 |     3689 |       0.0399 |
| 2018-02 |  85725 |     3480 |       0.0406 |
| 2018-03 | 101968 |     4030 |       0.0395 |
| 2018-04 |  83571 |     2850 |       0.0341 |
| 2018-05 |  89673 |     3094 |       0.0345 |
| 2018-06 |   2754 |      119 |       0.0432 |

## Transaction amount by class
| isFraud   |   count |   mean |    std |   min |   50% |   95% |   99% |      max |
|:----------|--------:|-------:|-------:|------:|------:|------:|------:|---------:|
| legit     |  569877 | 134.51 | 239.40 |  0.25 | 68.50 |   435 |  1104 | 31937.39 |
| fraud     |   20663 | 149.24 | 232.21 |  0.29 | 75.00 |   500 |   994 |  5191.00 |

## Missing values by column group
| group   |   columns |   mean_missing |   cols_over_90pct_missing |
|:--------|----------:|---------------:|--------------------------:|
| C       |        14 |         0.0000 |                         0 |
| D       |        15 |         0.5815 |                         1 |
| M       |         9 |         0.4992 |                         0 |
| V       |       339 |         0.4304 |                         0 |
| id_     |        38 |         0.8482 |                        10 |

## Fraud rate by category (top 8 by volume)
### ProductCD
| ProductCD   |   rows |   fraud_rate |
|:------------|-------:|-------------:|
| W           | 439670 |       0.0204 |
| C           |  68519 |       0.1169 |
| R           |  37699 |       0.0378 |
| H           |  33024 |       0.0477 |
| S           |  11628 |       0.0590 |

### card4
| card4            |   rows |   fraud_rate |
|:-----------------|-------:|-------------:|
| visa             | 384767 |       0.0348 |
| mastercard       | 189217 |       0.0343 |
| american express |   8328 |       0.0287 |
| discover         |   6651 |       0.0773 |
| <missing>        |   1577 |       0.0260 |

### card6
| card6           |   rows |   fraud_rate |
|:----------------|-------:|-------------:|
| debit           | 439938 |       0.0243 |
| credit          | 148986 |       0.0668 |
| <missing>       |   1571 |       0.0248 |
| debit or credit |     30 |       0.0000 |
| charge card     |     15 |       0.0000 |

### DeviceType
| DeviceType   |   rows |   fraud_rate |
|:-------------|-------:|-------------:|
| <missing>    | 449730 |       0.0210 |
| desktop      |  85165 |       0.0652 |
| mobile       |  55645 |       0.1017 |

### P_emaildomain
| P_emaildomain   |   rows |   fraud_rate |
|:----------------|-------:|-------------:|
| gmail.com       | 228355 |       0.0435 |
| yahoo.com       | 100934 |       0.0228 |
| <missing>       |  94456 |       0.0295 |
| hotmail.com     |  45250 |       0.0530 |
| anonymous.com   |  36998 |       0.0232 |
| aol.com         |  28289 |       0.0218 |
| comcast.net     |   7888 |       0.0312 |
| icloud.com      |   6267 |       0.0314 |

## Drift (population stability index)
PSI under 0.1 is stable, 0.1 to 0.25 is a moderate shift, over 0.25 is a large shift.

| feature        |   psi_train_vs_valid |   psi_train_vs_test |
|:---------------|---------------------:|--------------------:|
| TransactionAmt |               0.0083 |              0.0049 |
| card1          |               0.0012 |              0.0040 |
| addr1          |               0.0027 |              0.0040 |
| dist1          |               0.0297 |              0.0203 |
| C1             |               0.0090 |              0.0129 |
| C13            |               0.0330 |              0.0254 |
| D1             |               0.0582 |              0.0233 |
| D15            |               0.0495 |              0.0904 |
