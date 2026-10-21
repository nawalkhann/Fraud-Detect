# Model report: ieee

Costs: missed fraud = amount x 1.0 + $15 chargeback; every alert = $5 review; false alarm friction = $0.
Test set: 89,326 transactions, 3,114 frauds ($477,356). Thresholds are chosen on valid and applied unchanged to test.

Policies: `min_cost` is the single threshold with the lowest validation cost; `expected_loss` alerts when p x (amount + chargeback) > review cost, so the bar drops as the amount at risk grows. The production policy is whichever of the two was cheaper on validation.

## Headline (LightGBM, `expected_loss` policy, test split)
- Total cost **$138,481** vs **$524,066** with no model (73.6% saved).
- Catches 68.4% of frauds (2,131 of 3,114), 83.4% of fraud dollars, with 8,943 alerts (23.8% of alerts are fraud).
- Best LightGBM iteration: 482.

## Ranking quality and overfitting check (train vs valid vs test)
PR-AUC is the main metric under heavy imbalance. A large train-test gap means overfitting.

|                       |   roc_auc |   pr_auc |   brier |   log_loss |
|:----------------------|----------:|---------:|--------:|-----------:|
| ('lightgbm', 'train') |    0.9997 |   0.9941 |  0.0031 |     0.0155 |
| ('lightgbm', 'valid') |    0.9443 |   0.6758 |  0.0183 |     0.0743 |
| ('lightgbm', 'test')  |    0.9168 |   0.5729 |  0.0212 |     0.0890 |
| ('logistic', 'train') |    0.8662 |   0.4813 |  0.0238 |     0.1010 |
| ('logistic', 'valid') |    0.8230 |   0.3978 |  0.0258 |     0.1131 |
| ('logistic', 'test')  |    0.7999 |   0.1637 |  0.0421 |     0.3467 |

## Error at each threshold policy (test split)
`max_accuracy` shows why accuracy misleads: it barely flags anything.

|                               |   threshold |   accuracy |   precision |   recall |     f1 |   alerts |   tp |    fp |   fn |   fraud_dollars_missed |   valid_total_cost |   total_cost |
|:------------------------------|------------:|-----------:|------------:|---------:|-------:|---------:|-----:|------:|-----:|-----------------------:|-------------------:|-------------:|
| ('lightgbm', 'default_0.5')   |      0.5000 |     0.9756 |      0.8482 |   0.3661 | 0.5114 |     1344 | 1140 |   204 | 1974 |           372,730.4097 |       387,472.8940 | 409,060.4097 |
| ('lightgbm', 'max_accuracy')  |      0.2800 |     0.9755 |      0.7496 |   0.4451 | 0.5585 |     1849 | 1386 |   463 | 1728 |           342,051.3777 |       333,296.4909 | 377,216.3777 |
| ('lightgbm', 'max_f1')        |      0.1915 |     0.9735 |      0.6633 |   0.4852 | 0.5605 |     2278 | 1511 |   767 | 1603 |           323,787.8326 |       307,300.8100 | 359,222.8326 |
| ('lightgbm', 'min_cost')      |      0.0139 |     0.8325 |      0.1534 |   0.8420 | 0.2595 |    17093 | 2622 | 14471 |  492 |            79,906.2426 |       143,111.4818 | 172,751.2426 |
| ('lightgbm', 'expected_loss') |    nan      |     0.9127 |      0.2383 |   0.6843 | 0.3535 |     8943 | 2131 |  6812 |  983 |            79,020.7097 |       116,646.4350 | 138,480.7097 |
| ('logistic', 'default_0.5')   |      0.5000 |     0.9545 |      0.3102 |   0.2482 | 0.2758 |     2492 |  773 |  1719 | 2341 |           406,903.1737 |       489,427.7338 | 454,478.1737 |
| ('logistic', 'max_accuracy')  |      0.6407 |     0.9549 |      0.2996 |   0.2193 | 0.2532 |     2280 |  683 |  1597 | 2431 |           413,816.2107 |       498,526.9288 | 461,681.2107 |
| ('logistic', 'max_f1')        |      0.1871 |     0.9458 |      0.2802 |   0.3536 | 0.3127 |     3929 | 1101 |  2828 | 2013 |           363,649.6097 |       413,917.1859 | 413,489.6097 |
| ('logistic', 'min_cost')      |      0.0335 |     0.7523 |      0.0951 |   0.7174 | 0.1680 |    23479 | 2234 | 21245 |  880 |           127,022.2186 |       234,774.5720 | 257,617.2186 |
| ('logistic', 'expected_loss') |    nan      |     0.7825 |      0.0957 |   0.6198 | 0.1657 |    20176 | 1930 | 18246 | 1184 |            81,108.0538 |       192,123.4268 | 199,748.0538 |

## Top features (LightGBM gain)

|                         |        gain |
|:------------------------|------------:|
| uid_C13_mean            | 58,966.9899 |
| V257                    | 53,465.9060 |
| C1                      | 51,388.1341 |
| V258                    | 49,506.7976 |
| uid_TransactionAmt_mean | 48,865.3482 |
| uid_C13_std             | 41,060.0834 |
| C14                     | 39,905.3898 |
| card1_freq              | 37,079.1686 |
| V294                    | 36,471.8674 |
| uid_dist1_mean          | 33,972.4635 |
| uid_D15_std             | 33,913.8765 |
| uid_TransactionAmt_std  | 33,208.9752 |
| card1                   | 32,496.2182 |
| DeviceInfo              | 30,982.5400 |
| C13                     | 30,953.9492 |
