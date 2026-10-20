import numpy as np
import pandas as pd

from fraud.features import FeatureBuilder


def _frame(days, card1):
    n = len(days)
    return pd.DataFrame({
        "TransactionID": np.arange(n), "isFraud": 0, "TransactionDT": np.array(days) * 86_400 + 3600,
        "day": days, "TransactionAmt": np.linspace(10, 100, n), "card1": card1, "addr1": 300.0,
        "D1": 0.0, "ProductCD": pd.Categorical(["W"] * n),
    })


def test_ieee_features_are_fitted_on_train_only():
    train = _frame([0, 1, 2, 3], [1, 1, 2, 2])
    test = _frame([10, 11], [1, 99])            # card 99 never appears in train
    fb = FeatureBuilder("ieee").fit(train)
    X = fb.transform(test)
    assert list(X.columns) == fb.columns_
    assert X["card1_freq"].tolist() == [2.0, 0.0]
    assert "isFraud" not in X and "TransactionID" not in X
    assert X["uid_TransactionAmt_mean"].isna().tolist() == [True, True]  # new day -> new uid
