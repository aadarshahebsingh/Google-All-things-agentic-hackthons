"""API tests using FastAPI TestClient (demo/in-memory backends)."""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_and_activity():
    r = client.post("/api/startup", json={"idea": "AI platform for engineering student internships"})
    assert r.status_code == 200
    sid = r.json()["startup_id"]
    a = client.get(f"/api/startup/{sid}/activity").json()
    assert len(a["events"]) >= 1


def test_full_validation_workflow():
    r = client.post("/api/start-validation",
                    json={"idea": "I want to build an AI platform that helps engineering students find relevant internships."})
    sid = r.json()["startup_id"]
    # Background thread needs time; poll up to ~60s (10k personas + scenarios)
    deadline = time.time() + 60
    status = ""
    while time.time() < deadline:
        status = client.get(f"/api/startup/{sid}").json().get("status", "")
        if status == "COMPLETE":
            break
        time.sleep(2)
    assert status == "COMPLETE"

    fit = client.get(f"/api/startup/{sid}/market-fit").json()
    assert fit["market_fit_score"] > 0

    sim = client.get(f"/api/startup/{sid}/simulation").json()
    assert sim["participant_count"] == 10000

    assets = client.get(f"/api/startup/{sid}/assets").json()
    assert assets["deck"]["slides"]

    opps = client.get(f"/api/startup/{sid}/opportunities").json()["opportunities"]
    assert opps and opps[0]["data_label"] == "DEMO"
