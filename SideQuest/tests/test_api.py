import os, sys, tempfile
os.environ["SIDEQUEST_DB"] = os.path.join(tempfile.mkdtemp(), "test.db")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from fastapi.testclient import TestClient
import main

client = TestClient(main.app)

def complete(qid):
    q = client.get(f"/api/quests/{qid}").json()
    for i in range(len(q["checklist"])):
        client.post(f"/api/quests/{qid}/checklist", json={"index": i, "done": True})
    return client.post(f"/api/quests/{qid}/status", json={"status": "completed"})

def test_filters():
    r = client.get("/api/quests", params={"difficulty": "Beginner"}).json()
    assert r and all(q["difficulty"] == "Beginner" for q in r)
    r = client.get("/api/quests", params={"max_minutes": 30, "category": "Python"}).json()
    assert r and all(q["minutes"] <= 30 and q["category"] == "Python" for q in r)

def test_cannot_complete_early():
    assert client.post("/api/quests/2/status", json={"status": "completed"}).status_code == 400

def test_xp_awarded_once_and_persists():
    client.post("/api/reset")
    assert complete(1).json()["xp_gained"] == 50
    assert complete(1).json()["xp_gained"] == 0          # no double XP
    assert client.get("/api/dashboard").json()["xp"] == 50
    main.init_db()                                        # simulate restart
    d = client.get("/api/dashboard").json()
    assert d["xp"] == 50 and d["completed"] == 1 and d["streak"] == 1

def test_badges_and_level():
    client.post("/api/reset")
    r = complete(4)                                       # Intermediate = 100 XP
    assert "Quest Finisher" in r.json()["new_badges"]
    assert client.get("/api/dashboard").json()["level"] == 2
