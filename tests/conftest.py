"""Synthetic fixtures. These are hand-built toy frames, not samples of any dataset."""
import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def toy_flows() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    n = 400
    label = np.where(np.arange(n) % 4 == 0, "ATTACK", "BENIGN")
    df = pd.DataFrame({
        "Flow ID": [f"f{i}" for i in range(n)],
        "Source IP": rng.choice(["10.0.0.1", "10.0.0.2", "10.0.0.3"], n),
        "Destination Port": np.where(label == "ATTACK", 80, rng.choice([22, 443, 53], n)),
        "Timestamp": pd.date_range("2017-07-03", periods=n, freq="min").astype(str),
        "Flow Duration": rng.integers(0, 10_000, n).astype(float),
        "Flow Bytes/s": rng.random(n) * 1e5,
        "Bwd URG Flags": np.zeros(n),
        "proto": rng.choice(["tcp", "udp"], n),
        "Label": label,
    })
    df.loc[3, "Flow Bytes/s"] = np.inf
    df.loc[5, "Flow Bytes/s"] = np.nan
    df.loc[7, "Flow Duration"] = -1.0
    return df
