import os
import sys
import tempfile
import uuid
from pathlib import Path

TEST_ROOT = Path(tempfile.mkdtemp(prefix="sidequest-tests-"))
os.environ["SIDEQUEST_DB"] = str(TEST_ROOT / "test.db")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
import main

client = TestClient(main.app)


def submit(qid, headers=None):
    return client.post("/api/submissions", headers=headers or {}, data={
        "quest_id": str(qid),
        "code_text": "print('hello sidequest')",
        "output_text": "hello sidequest",
        "notes": "Test submission"
    })


def complete(qid, headers=None):
    q = client.get(f"/api/quests/{qid}", headers=headers or {}).json()
    for i in range(len(q["checklist"])):
        r = client.post(f"/api/quests/{qid}/checklist", headers=headers or {}, json={"index": i, "done": True})
        assert r.status_code == 200, r.text
    sr = submit(qid, headers)
    assert sr.status_code == 200, sr.text
    return client.post(f"/api/quests/{qid}/status", headers=headers or {}, json={"status": "completed"})


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def make_account(prefix):
    guest = client.post("/api/auth/guest")
    assert guest.status_code == 200, guest.text
    guest_data = guest.json()
    username = f"{prefix}_{uuid.uuid4().hex[:8]}"
    r = client.post("/api/auth/register", headers=auth_headers(guest_data["token"]), json={
        "username": username, "password": "SideQuest-test-123", "display_name": prefix.title()
    })
    assert r.status_code == 200, r.text
    return username, r.json()["token"]


def test_filters():
    r = client.get("/api/quests", params={"difficulty": "Beginner"})
    assert r.status_code == 200
    assert r.json() and all(q["difficulty"] == "Beginner" for q in r.json())
    r = client.get("/api/quests", params={"max_minutes": 30, "category": "Python"})
    assert r.status_code == 200
    assert r.json() and all(q["minutes"] <= 30 and q["category"] == "Python" for q in r.json())


def test_cannot_complete_early():
    client.post("/api/reset")
    r = client.post("/api/quests/2/status", json={"status": "completed"})
    assert r.status_code == 400


def test_submission_and_xp_awarded_once():
    client.post("/api/reset")
    early = client.post("/api/quests/1/status", json={"status": "completed"})
    assert early.status_code == 400
    assert "checklist" in early.json()["detail"].lower()
    first = complete(1)
    assert first.status_code == 200, first.text
    assert first.json()["xp_gained"] == 50
    again = client.post("/api/quests/1/status", json={"status": "completed"})
    assert again.status_code == 200
    assert again.json()["xp_gained"] == 0
    assert client.get("/api/dashboard").json()["xp"] == 50
    main.init_db()
    d = client.get("/api/dashboard").json()
    assert d["xp"] == 50 and d["completed"] == 1 and d["streak"] == 1
    submissions = client.get("/api/submissions?quest_id=1").json()
    assert submissions and submissions[0]["status"] == "accepted"


def test_badges_and_level():
    client.post("/api/reset")
    r = complete(4)  # Intermediate quest = 100 XP
    assert r.status_code == 200, r.text
    assert "Quest Finisher" in r.json()["new_badges"]
    assert client.get("/api/dashboard").json()["level"] == 2


def test_profile_themes_weekly_goals_and_roadmaps():
    goal = client.put("/api/weekly-goal", json={"target_quests": 4, "target_xp": 450})
    assert goal.status_code == 200
    assert goal.json()["target_quests"] == 4
    profile = client.get("/api/profile").json()
    update = client.put("/api/profile", json={"display_name": "Test Adventurer", "bio": "Learning by building", "avatar": "PY", "theme": "anime"})
    assert update.status_code == 200, update.text
    assert update.json()["display_name"] == "Test Adventurer"
    assert update.json()["theme"] == "anime"
    roadmaps = client.get("/api/roadmaps").json()
    assert len(roadmaps) >= 3
    join = client.post(f"/api/roadmaps/{roadmaps[0]['id']}/enroll")
    assert join.status_code == 200
    assert any(r["id"] == roadmaps[0]["id"] and r["enrolled"] for r in client.get("/api/roadmaps").json())
    assert client.get("/api/garden").status_code == 200
    topic = client.get("/api/trending").json()
    assert topic["title"] and topic["date"] and topic["resource"].startswith("https://")
    stats = client.get("/api/stats").json()
    assert len(stats["heatmap"]) == 35


def test_accounts_are_isolated_and_leaderboard_is_friends_only():
    alice_name, alice_token = make_account("alice")
    bob_name, bob_token = make_account("bob")
    alice_h, bob_h = auth_headers(alice_token), auth_headers(bob_token)
    # Each account gets its own quest status and XP.
    assert client.post("/api/quests/1/status", headers=alice_h, json={"status": "started"}).status_code == 200
    assert client.get("/api/my-quests", headers=bob_h).json() == []
    sent = client.post("/api/friends/requests", headers=alice_h, json={"username": bob_name})
    assert sent.status_code == 200, sent.text
    incoming = client.get("/api/friends", headers=bob_h).json()["incoming"]
    assert incoming and incoming[0]["username"] == alice_name
    accepted = client.post(f"/api/friends/requests/{incoming[0]['request_id']}/accept", headers=bob_h)
    assert accepted.status_code == 200
    board = client.get("/api/leaderboard", headers=alice_h).json()
    assert {entry["username"] for entry in board["entries"]} == {alice_name, bob_name}
    assert "global" not in board["scope"].lower()


def test_submission_validation_and_user_scoping():
    _, token = make_account("submitter")
    headers = auth_headers(token)
    bad = client.post("/api/submissions", headers=headers, data={"quest_id": "1", "code_text": "print(1)", "output_text": ""})
    assert bad.status_code == 400
    good = submit(1, headers)
    assert good.status_code == 200, good.text
    assert good.json()["status"] == "submitted"
    listing = client.get("/api/submissions", headers=headers).json()
    assert len(listing) == 1 and listing[0]["quest_id"] == 1
    # Another user's token must not expose these submissions.
    _, other_token = make_account("other")
    assert client.get("/api/submissions", headers=auth_headers(other_token)).json() == []


def test_private_screenshot_upload():
    _, token = make_account("screen")
    headers = auth_headers(token)
    fake_png = b"\x89PNG\r\n\x1a\n" + (b"\x00" * 24)
    upload = client.post("/api/submissions", headers=headers,
                         data={"quest_id": "2", "code_text": "print('ok')", "output_text": "ok"},
                         files={"screenshot": ("output.png", fake_png, "image/png")})
    assert upload.status_code == 200, upload.text
    screenshot_url = upload.json()["screenshot_url"]
    assert screenshot_url
    image = client.get(screenshot_url, headers=headers)
    assert image.status_code == 200
    _, other_token = make_account("noscreen")
    hidden = client.get(screenshot_url, headers=auth_headers(other_token))
    assert hidden.status_code == 404
