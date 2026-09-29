"""TestContract — does the endpoint accept and reject exactly what it promised? A failure is a bug."""
import pytest

VALID = {"hour_of_day": 2, "failed_attempts_24h": 9, "distinct_ips_24h": 5, "country_changed": 1,
         "is_vpn_exit": 1, "device_is_new": 1, "mfa_used": 0, "session_minutes": 22,
         "privileged_action": 1, "bytes_downloaded_mb": 210.0, "department": "engineering"}


def test_valid_event_scores(client):
    client.get("/readyz")
    r = client.post("/predict", json=VALID)
    assert r.status_code == 200 and "risk_score" in r.json()


@pytest.mark.parametrize("mutate,field", [
    ({"hour_of_day": 24}, "hour_of_day"),
    ({"mfa_used": 2}, "mfa_used"),
    ({"department": "legal"}, "department"),
    ({"admin_override": True}, "admin_override"),
])
def test_out_of_contract_is_422(client, mutate, field):
    r = client.post("/predict", json={**VALID, **mutate})
    assert r.status_code == 422
    assert r.json()["detail"][0]["loc"][-1] == field


def test_missing_field_is_422(client):
    payload = {k: v for k, v in VALID.items() if k != "session_minutes"}
    assert client.post("/predict", json=payload).status_code == 422


@pytest.mark.parametrize("hour", [0, 23])
def test_contract_limits_are_valid(client, hour):
    client.get("/readyz")
    assert client.post("/predict", json={**VALID, "hour_of_day": hour}).status_code == 200
