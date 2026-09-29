"""Deterministic synthetic login dataset — the Module 4 data, seed 42. Same numbers every run."""
import random
import pandas as pd

DEPTS = ['finance', 'engineering', 'support', 'sales', 'hr', 'operations']
COLS = ['event_id', 'hour_of_day', 'failed_attempts_24h', 'distinct_ips_24h', 'country_changed',
        'is_vpn_exit', 'device_is_new', 'mfa_used', 'session_minutes', 'privileged_action',
        'bytes_downloaded_mb', 'department', 'label']


def _normal(rng, i):
    hour = rng.randint(8, 19) if rng.random() < 0.85 else rng.choice([0, 1, 2, 3, 4, 5, 6, 7, 20, 21, 22, 23])
    failed = rng.choices([0, 1, 2, 3, 7], weights=[70, 18, 7, 4, 1])[0]
    ips = rng.choices([1, 2, 3, 5], weights=[75, 18, 6, 1])[0]
    return [i, hour, failed, ips, 1 if rng.random() < 0.04 else 0, 1 if rng.random() < 0.09 else 0,
            1 if rng.random() < 0.08 else 0, 0 if rng.random() < 0.06 else 1, max(1, int(rng.gauss(52, 30))),
            1 if rng.random() < 0.11 else 0, round(abs(rng.gauss(24, 30)), 1), rng.choice(DEPTS), 0]


def _compromised(rng, i):
    if rng.random() < 0.30:
        hour = rng.randint(8, 19)
        failed = rng.choices([0, 1, 2], weights=[60, 30, 10])[0]
        ips = rng.choices([1, 2], weights=[70, 30])[0]
        cc = 1 if rng.random() < 0.35 else 0
        vpn = 1 if rng.random() < 0.45 else 0
        nd = 1 if rng.random() < 0.55 else 0
        mfa = 1 if rng.random() < 0.55 else 0
        sess = max(1, int(rng.gauss(40, 25)))
        priv = 1 if rng.random() < 0.40 else 0
        dl = round(abs(rng.gauss(70, 60)), 1)
    else:
        hour = rng.choice([0, 1, 2, 3, 4, 5, 22, 23, 14, 15])
        failed = rng.choices([0, 3, 6, 12, 30], weights=[10, 25, 30, 25, 10])[0]
        ips = rng.choices([1, 3, 5, 9], weights=[15, 30, 35, 20])[0]
        cc = 1 if rng.random() < 0.80 else 0
        vpn = 1 if rng.random() < 0.70 else 0
        nd = 1 if rng.random() < 0.85 else 0
        mfa = 1 if rng.random() < 0.18 else 0
        sess = max(1, int(rng.gauss(22, 20)))
        priv = 1 if rng.random() < 0.65 else 0
        dl = round(abs(rng.gauss(210, 190)), 1)
    return [i, hour, failed, ips, cc, vpn, nd, mfa, sess, priv, dl, rng.choice(DEPTS), 1]


def generate(rows=6000, seed=42, rate=0.06):
    rng = random.Random(seed)
    out = [(_compromised if rng.random() < rate else _normal)(rng, i) for i in range(1, rows + 1)]
    rng.shuffle(out)
    for n, row in enumerate(out, 1):
        row[0] = n
    return pd.DataFrame(out, columns=COLS)
