"""TestOps — do health, readiness and the model card behave? A failure means an ops integration will misbehave."""
import json
import os

from model.package_model import PKG


def test_healthz_is_liveness_only(client):
    assert client.get("/healthz").json()["status"] == "alive"


def test_readyz_reports_ready_and_a_digest(client):
    body = client.get("/readyz").json()
    assert body["status"] == "ready" and body["verified"] is True
    assert len(body["model_digest"]) == 16


def test_model_card_states_its_limitations_and_null_approval():
    card = json.load(open(os.path.join(PKG, "model_card.json")))
    assert len(card["limitations"]) >= 4
    assert card["approval"]["approved_by"] is None  # nobody has approved this artifact yet
    assert len(card["contract"]["features"]) == 11
