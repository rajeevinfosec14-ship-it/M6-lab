"""FastAPI model endpoint. Liveness and readiness are DIFFERENT questions; verification is a refusal."""
import json
import os

import joblib
import pandas as pd
from fastapi import FastAPI, Response

from app.contract import Event, FEATURES
from model.package_model import PKG, verify

app = FastAPI(title="auth-anomaly-api")
_MODEL = {"pipe": None}


def _digest():
    return json.load(open(os.path.join(PKG, "manifest.json")))["files"]["model.joblib"][:16]


@app.get("/healthz")
def healthz():
    """LIVENESS — is the process up? Never touches the model, so a model fault does not trigger a restart loop."""
    return {"status": "alive"}


@app.get("/readyz")
def readyz(resp: Response):
    """READINESS — should traffic be routed here? Re-verifies the package; refuses on mismatch."""
    verify_on = os.environ.get("MODEL_VERIFY", "1") == "1"
    ok = verify()
    if verify_on and not ok:
        _MODEL["pipe"] = None
        resp.status_code = 503
        return {"status": "unverified"}
    _MODEL["pipe"] = joblib.load(os.path.join(PKG, "model.joblib"))
    return {"status": "ready", "verified": ok, "model_digest": _digest()}


@app.post("/predict")
def predict(ev: Event, resp: Response):
    if _MODEL["pipe"] is None:
        resp.status_code = 503
        return {"detail": "model not ready — call /readyz first"}
    x = pd.DataFrame([ev.model_dump()])[FEATURES]
    score = float(_MODEL["pipe"].predict_proba(x)[:, 1][0])
    return {"risk_score": round(score, 4), "flagged": score >= 0.5, "model_digest": _digest()}
