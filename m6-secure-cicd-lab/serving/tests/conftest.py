import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(__file__)
SERVING = os.path.abspath(os.path.join(HERE, ".."))


@pytest.fixture(scope="session", autouse=True)
def _build_package():
    """Build a clean, verified package once before the suite runs."""
    sys.path.insert(0, SERVING)
    subprocess.run([sys.executable, "-m", "model.package_model"], cwd=SERVING, check=True)


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("MODEL_VERIFY", "1")
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)
