"""SideQuest: a gamified learning tracker powered by FastAPI and SQLite.
Run locally with: python -m uvicorn main:app --reload
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from seed import QUESTS

BASE = Path(__file__).parent
DB_PATH = os.environ.get("SIDEQUEST_DB", str(BASE / "sidequest.db"))
UPLOAD_DIR = Path(os.environ.get("SIDEQUEST_UPLOAD_DIR", str(BASE / "uploads"))).resolve()
XP_BY_DIFFICULTY = {"Beginner": 50, "Intermediate": 100, "Advanced": 200}
XP_PER_LEVEL = 100
MAX_SCREENSHOT_BYTES = 3 * 1024 * 1024
ALLOWED_THEMES = {"light", "dark", "anime", "cute"}
AVATAR_CHOICES = {"SQ", "PY", "WEB", "AI", "DSA", "DATA", "UI", "LAB", "DEV", "CODE"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS app_meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS quests(
  id INTEGER PRIMARY KEY, title TEXT, description TEXT, problem TEXT,
  features TEXT, tech TEXT, difficulty TEXT, category TEXT, minutes INTEGER,
  xp INTEGER, checklist TEXT
);
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE COLLATE NOCASE,
  password_hash TEXT,
  is_guest INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions(
  token_hash TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS user_profiles(
  user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  display_name TEXT NOT NULL DEFAULT 'Adventurer', bio TEXT NOT NULL DEFAULT '',
  avatar TEXT NOT NULL DEFAULT 'SQ', theme TEXT NOT NULL DEFAULT 'light',
  xp INTEGER NOT NULL DEFAULT 0, streak INTEGER NOT NULL DEFAULT 0,
  best_streak INTEGER NOT NULL DEFAULT 0, last_active TEXT
);
CREATE TABLE IF NOT EXISTS user_progress(
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  quest_id INTEGER NOT NULL REFERENCES quests(id) ON DELETE CASCADE,
  status TEXT NOT NULL, checked TEXT NOT NULL DEFAULT '[]', updated TEXT,
  completed_at TEXT, PRIMARY KEY(user_id, quest_id)
);
CREATE TABLE IF NOT EXISTS user_activity(
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  text TEXT NOT NULL, ts TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS weekly_goals(
  user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  target_quests INTEGER NOT NULL DEFAULT 3, target_xp INTEGER NOT NULL DEFAULT 300,
  week_start TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS roadmap_enrollments(
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  roadmap_id TEXT NOT NULL, enrolled_at TEXT NOT NULL,
  PRIMARY KEY(user_id, roadmap_id)
);
CREATE TABLE IF NOT EXISTS submissions(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  quest_id INTEGER NOT NULL REFERENCES quests(id) ON DELETE CASCADE,
  code_text TEXT NOT NULL DEFAULT '', output_text TEXT NOT NULL DEFAULT '',
  github_url TEXT NOT NULL DEFAULT '', demo_url TEXT NOT NULL DEFAULT '',
  screenshot_path TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'submitted', created_at TEXT NOT NULL,
  reviewed_at TEXT, feedback TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS friend_requests(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sender_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  receiver_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'pending', created_at TEXT NOT NULL,
  UNIQUE(sender_id, receiver_id), CHECK(sender_id <> receiver_id)
);
CREATE INDEX IF NOT EXISTS idx_progress_user_status ON user_progress(user_id, status);
CREATE INDEX IF NOT EXISTS idx_activity_user_ts ON user_activity(user_id, ts);
CREATE INDEX IF NOT EXISTS idx_submissions_user_quest ON submissions(user_id, quest_id, id);
"""


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def week_start(d: Optional[date] = None) -> str:
    day = d or date.today()
    return (day - timedelta(days=day.weekday())).isoformat()


@contextmanager
def db():
    """Connection helper that always commits/rolls back and closes the connection."""
    path = Path(DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def hash_password(password: str, salt: Optional[str] = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), 240_000).hex()
    return f"pbkdf2_sha256${salt}${digest}"


def verify_password(password: str, stored: Optional[str]) -> bool:
    if not stored:
        return False
    try:
        scheme, salt, expected = stored.split("$", 2)
    except ValueError:
        return False
    if scheme != "pbkdf2_sha256":
        return False
    actual = hash_password(password, salt).split("$", 2)[2]
    return secrets.compare_digest(actual, expected)


def issue_token(c: sqlite3.Connection, user_id: int) -> str:
    token = secrets.token_urlsafe(36)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    c.execute("INSERT INTO sessions(token_hash,user_id,created_at) VALUES(?,?,?)", (token_hash, user_id, now()))
    return token


def user_from_authorization(c: sqlite3.Connection, authorization: Optional[str]) -> Optional[sqlite3.Row]:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(401, "Invalid authorization header")
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    user = c.execute("SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=?", (token_hash,)).fetchone()
    if not user:
        raise HTTPException(401, "Session expired. Please sign in again.")
    return user


def current_user_id(authorization: Optional[str] = Header(default=None)) -> int:
    with db() as c:
        user = user_from_authorization(c, authorization)
        if user:
            return int(user["id"])
        # Compatibility for direct local API use and the existing API test suite.
        guest = c.execute("SELECT id FROM users WHERE username='guest' COLLATE NOCASE").fetchone()
        if not guest:
            raise HTTPException(401, "Create a guest session to continue")
        return int(guest["id"])


def init_db() -> None:
    with db() as c:
        c.executescript(SCHEMA)
        if c.execute("SELECT COUNT(*) FROM quests").fetchone()[0] == 0:
            for title, desc, problem, features, tech, difficulty, category, minutes in QUESTS:
                checklist = ["Set up the project folder"] + features + ["Test everything and commit to Git"]
                c.execute(
                    "INSERT INTO quests(title,description,problem,features,tech,difficulty,category,minutes,xp,checklist) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (title, desc, problem, json.dumps(features), json.dumps(tech), difficulty, category,
                     minutes, XP_BY_DIFFICULTY[difficulty], json.dumps(checklist)),
                )
        # Old versions stored a single profile/progress table. Keep those legacy tables untouched;
        # all new per-user data lives in user_profiles/user_progress so existing databases can open safely.
        c.execute("INSERT OR IGNORE INTO users(username,password_hash,is_guest,created_at) VALUES('guest',NULL,1,?)", (now(),))
        guest_id = c.execute("SELECT id FROM users WHERE username='guest' COLLATE NOCASE").fetchone()[0]
        c.execute("INSERT OR IGNORE INTO user_profiles(user_id) VALUES(?)", (guest_id,))
        c.execute("INSERT OR IGNORE INTO weekly_goals(user_id,target_quests,target_xp,week_start) VALUES(?,3,300,?)",
                  (guest_id, week_start()))

        # One-time migration from SideQuest v1's single-profile schema. The old tables are
        # intentionally left in place as a backup; new routes use only the user-scoped tables.
        tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        migrated = c.execute("SELECT value FROM app_meta WHERE key='v1_single_profile_migrated'").fetchone()
        if not migrated and {'profile', 'progress'}.issubset(tables):
            old_profile = c.execute("SELECT xp,streak,best_streak,last_active FROM profile WHERE id=1").fetchone()
            if old_profile:
                c.execute("UPDATE user_profiles SET xp=?,streak=?,best_streak=?,last_active=? WHERE user_id=?",
                          (old_profile['xp'], old_profile['streak'], old_profile['best_streak'], old_profile['last_active'], guest_id))
            c.execute("INSERT OR IGNORE INTO user_progress(user_id,quest_id,status,checked,updated,completed_at) "
                      "SELECT ?,quest_id,status,COALESCE(checked,'[]'),updated,completed_at FROM progress "
                      "WHERE quest_id IN (SELECT id FROM quests)", (guest_id,))
            if 'activity' in tables:
                c.execute("INSERT INTO user_activity(user_id,text,ts) SELECT ?,text,ts FROM activity", (guest_id,))
            c.execute("INSERT OR REPLACE INTO app_meta(key,value) VALUES('v1_single_profile_migrated',?)", (now(),))

        # Normalize avatars saved by older emoji-based builds to text labels.
        placeholders = ",".join("?" for _ in AVATAR_CHOICES)
        c.execute(f"UPDATE user_profiles SET avatar='SQ' WHERE avatar NOT IN ({placeholders})", tuple(AVATAR_CHOICES))


init_db()
app = FastAPI(title="SideQuest API", version="2.0.0")

# ---------- curated content ----------
ROADMAPS = [
    {"id": "python-starter", "title": "Python Adventurer", "description": "Learn Python by building small command-line projects.",
     "level": "Beginner", "icon": "PY", "quest_ids": [1, 2, 3, 4, 5, 6]},
    {"id": "web-builder", "title": "Web Builder Path", "description": "Move from your first page to apps backed by an API.",
     "level": "Beginner → Advanced", "icon": "WEB", "quest_ids": [7, 8, 9, 10, 11]},
    {"id": "problem-solver", "title": "Problem Solver Guild", "description": "Practice core programming ideas through games and data structures.",
     "level": "Mixed", "icon": "DSA", "quest_ids": [12, 13, 14, 15, 16]},
]
TOPICS = [
    {"title": "AI agents", "category": "Artificial Intelligence", "why": "Systems that use tools and multi-step plans to complete tasks.", "challenge": "Build a tiny agent that chooses one of three tools from a user request.", "resource": "https://platform.openai.com/docs/guides/agents"},
    {"title": "Retrieval-Augmented Generation (RAG)", "category": "AI Engineering", "why": "Grounding model answers in documents or trusted data sources.", "challenge": "Create a small FAQ search that retrieves the best matching paragraph.", "resource": "https://www.pinecone.io/learn/retrieval-augmented-generation/"},
    {"title": "Passkeys and passwordless login", "category": "Web Security", "why": "Authentication methods designed to reduce reliance on reusable passwords.", "challenge": "Write a threat-model checklist for a login screen.", "resource": "https://passkeys.dev/"},
    {"title": "Local language models", "category": "AI Engineering", "why": "Running model inference locally can improve control over data and costs.", "challenge": "Compare the memory and latency needs of two small models.", "resource": "https://huggingface.co/docs/transformers/index"},
    {"title": "MCP and tool interoperability", "category": "Developer Tools", "why": "Standardized ways for applications to expose tools and context to AI clients.", "challenge": "Sketch a tool schema for a weather lookup function.", "resource": "https://modelcontextprotocol.io/introduction"},
    {"title": "WebAssembly", "category": "Web Platform", "why": "A portable compilation target that can run code in web environments.", "challenge": "Research one use case where WebAssembly fits better than plain JavaScript.", "resource": "https://webassembly.org/"},
    {"title": "Type-safe API contracts", "category": "Backend Development", "why": "Schemas reduce ambiguity between frontend and backend code.", "challenge": "Document the request and response shape of one API endpoint.", "resource": "https://fastapi.tiangolo.com/"},
    {"title": "Vector search", "category": "Data & AI", "why": "Finding semantically similar information is useful for search and recommendations.", "challenge": "Represent five short sentences and group them by meaning.", "resource": "https://www.sbert.net/"},
    {"title": "Software supply-chain security", "category": "Security", "why": "Dependencies, build systems, and package provenance affect application safety.", "challenge": "Audit a project's dependencies and document update risks.", "resource": "https://owasp.org/www-project-top-10/"},
    {"title": "Accessible UI patterns", "category": "Frontend Development", "why": "Keyboard support, contrast, and semantics make interfaces more usable.", "challenge": "Navigate a form using only the keyboard and fix one barrier.", "resource": "https://www.w3.org/WAI/fundamentals/accessibility-intro/"},
    {"title": "Event-driven architecture", "category": "Backend Development", "why": "Events help systems react to work without tightly coupling every component.", "challenge": "Draw a simple flow for a quest-completed event.", "resource": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Events"},
    {"title": "Python typing", "category": "Python", "why": "Type hints make code intent easier to understand and tools can catch mistakes sooner.", "challenge": "Add type hints to a function and describe its accepted values.", "resource": "https://docs.python.org/3/library/typing.html"},
    {"title": "Data visualization", "category": "Data", "why": "Good charts help people interpret trends instead of staring at raw numbers.", "challenge": "Chart seven days of fictional study minutes and label the axes.", "resource": "https://matplotlib.org/stable/tutorials/index.html"},
    {"title": "Progressive Web Apps", "category": "Web Platform", "why": "Web apps can offer installability and offline-friendly experiences.", "challenge": "List which screens of SideQuest should be usable offline.", "resource": "https://web.dev/learn/pwa/"},
]


def quest_sql() -> str:
    return ("SELECT q.*, up.status AS pstatus, up.checked AS pchecked FROM quests q "
            "LEFT JOIN user_progress up ON up.quest_id=q.id AND up.user_id=?")


def quest_out(row: sqlite3.Row) -> dict:
    q = dict(row)
    for key in ("features", "tech", "checklist"):
        q[key] = json.loads(q[key] or "[]")
    q["status"] = q.pop("pstatus", None)
    q["checked"] = json.loads(q.pop("pchecked", None) or "[]")
    return q


def get_row(c: sqlite3.Connection, qid: int, user_id: int) -> sqlite3.Row:
    row = c.execute(quest_sql() + " WHERE q.id=?", (user_id, qid)).fetchone()
    if not row:
        raise HTTPException(404, "Quest not found")
    return row


def log(c: sqlite3.Connection, user_id: int, text: str) -> None:
    c.execute("INSERT INTO user_activity(user_id,text,ts) VALUES(?,?,?)", (user_id, text, now()))


def touch(c: sqlite3.Connection, user_id: int) -> None:
    p = c.execute("SELECT * FROM user_profiles WHERE user_id=?", (user_id,)).fetchone()
    today = date.today()
    if p["last_active"] == today.isoformat():
        return
    yesterday = (today - timedelta(days=1)).isoformat()
    streak = p["streak"] + 1 if p["last_active"] == yesterday else 1
    c.execute("UPDATE user_profiles SET streak=?, best_streak=MAX(best_streak,?), last_active=? WHERE user_id=?",
              (streak, streak, today.isoformat(), user_id))


def stats(c: sqlite3.Connection, user_id: int) -> dict:
    p = c.execute("SELECT * FROM user_profiles WHERE user_id=?", (user_id,)).fetchone()
    rows = c.execute("SELECT q.category cat,q.difficulty diff,up.status st FROM user_progress up "
                     "JOIN quests q ON q.id=up.quest_id WHERE up.user_id=?", (user_id,)).fetchall()
    done = [r for r in rows if r["st"] == "completed"]
    today = date.today()
    active = p["last_active"] in (today.isoformat(), (today - timedelta(days=1)).isoformat())
    return {"xp": p["xp"], "level": p["xp"] // XP_PER_LEVEL + 1,
            "rank": rank_for_xp(p["xp"]), "streak": p["streak"] if active else 0,
            "best": p["best_streak"], "saved": sum(r["st"] == "saved" for r in rows),
            "started": sum(r["st"] in ("started", "completed") for r in rows),
            "completed": len(done), "web": sum(r["cat"] == "Web Development" for r in done),
            "python": sum(r["cat"] == "Python" for r in done),
            "adv": sum(r["diff"] == "Advanced" for r in done)}


def rank_for_xp(xp: int) -> str:
    if xp >= 2000: return "Legendary Hero"
    if xp >= 1000: return "Guild Master"
    if xp >= 500: return "Elite Adventurer"
    if xp >= 200: return "Quest Knight"
    if xp >= 100: return "Apprentice"
    return "Rookie Adventurer"


BADGES = [
    ("first_step", "First Step", "Start your first quest", lambda s: s["started"] >= 1),
    ("finisher", "Quest Finisher", "Complete a quest", lambda s: s["completed"] >= 1),
    ("triple", "Triple Threat", "Complete 3 quests", lambda s: s["completed"] >= 3),
    ("veteran", "Veteran", "Complete 10 quests", lambda s: s["completed"] >= 10),
    ("streak3", "On a Roll", "Reach a 3-day streak", lambda s: s["best"] >= 3),
    ("streak7", "Week Warrior", "Reach a 7-day streak", lambda s: s["best"] >= 7),
    ("level3", "Rising Star", "Reach level 3", lambda s: s["level"] >= 3),
    ("web", "Web Wizard", "Complete 2 Web Development quests", lambda s: s["web"] >= 2),
    ("py", "Pythonista", "Complete 2 Python quests", lambda s: s["python"] >= 2),
    ("adv", "Challenger", "Complete an Advanced quest", lambda s: s["adv"] >= 1),
]


def badges(s: dict) -> list[dict]:
    return [{"id": key, "name": name, "desc": desc, "unlocked": bool(check(s))}
            for key, name, desc, check in BADGES]


def unlocked(c: sqlite3.Connection, user_id: int) -> set[str]:
    return {b["id"] for b in badges(stats(c, user_id)) if b["unlocked"]}


def latest_submission(c: sqlite3.Connection, user_id: int, qid: int) -> Optional[dict]:
    row = c.execute("SELECT * FROM submissions WHERE user_id=? AND quest_id=? ORDER BY id DESC LIMIT 1",
                    (user_id, qid)).fetchone()
    return submission_out(row) if row else None


def submission_out(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["screenshot_url"] = f"/api/submissions/{d['id']}/screenshot" if d.get("screenshot_path") else ""
    d.pop("screenshot_path", None)
    return d


def result(c: sqlite3.Connection, qid: int, user_id: int, before: set[str], gained: int = 0) -> dict:
    new = [b["name"] for b in badges(stats(c, user_id)) if b["unlocked"] and b["id"] not in before]
    return {"quest": quest_out(get_row(c, qid, user_id)), "xp_gained": gained, "new_badges": new}


def ensure_weekly_goal(c: sqlite3.Connection, user_id: int) -> sqlite3.Row:
    current_week = week_start()
    row = c.execute("SELECT * FROM weekly_goals WHERE user_id=?", (user_id,)).fetchone()
    if not row:
        c.execute("INSERT INTO weekly_goals(user_id,target_quests,target_xp,week_start) VALUES(?,3,300,?)",
                  (user_id, current_week))
    elif row["week_start"] != current_week:
        c.execute("UPDATE weekly_goals SET week_start=? WHERE user_id=?", (current_week, user_id))
    return c.execute("SELECT * FROM weekly_goals WHERE user_id=?", (user_id,)).fetchone()


def weekly_progress(c: sqlite3.Connection, user_id: int) -> dict:
    goal = ensure_weekly_goal(c, user_id)
    start = goal["week_start"] + "T00:00:00"
    completions = c.execute("SELECT COUNT(*) n, COALESCE(SUM(q.xp),0) xp FROM user_progress up "
                            "JOIN quests q ON q.id=up.quest_id WHERE up.user_id=? AND up.status='completed' "
                            "AND up.completed_at>=?", (user_id, start)).fetchone()
    return {"target_quests": goal["target_quests"], "target_xp": goal["target_xp"],
            "week_start": goal["week_start"], "completed_quests": completions["n"], "earned_xp": completions["xp"],
            "quests_pct": min(100, round(100 * completions["n"] / max(1, goal["target_quests"]))),
            "xp_pct": min(100, round(100 * completions["xp"] / max(1, goal["target_xp"])))}


def profile_out(c: sqlite3.Connection, user_id: int) -> dict:
    user = c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    p = c.execute("SELECT * FROM user_profiles WHERE user_id=?", (user_id,)).fetchone()
    s = stats(c, user_id)
    return {"id": user_id, "username": user["username"], "is_guest": bool(user["is_guest"]),
            "display_name": p["display_name"], "bio": p["bio"], "avatar": p["avatar"], "theme": p["theme"],
            "joined_at": user["created_at"], "xp": s["xp"], "level": s["level"], "rank": s["rank"],
            "streak": s["streak"], "best_streak": s["best"], "completed": s["completed"]}


# ---------- request models ----------
class StatusIn(BaseModel):
    status: str

class CheckIn(BaseModel):
    index: int
    done: bool

class AuthIn(BaseModel):
    username: str = Field(min_length=3, max_length=20)
    password: str = Field(min_length=8, max_length=128)
    display_name: Optional[str] = Field(default=None, max_length=30)

class GoalIn(BaseModel):
    target_quests: int = Field(ge=1, le=30)
    target_xp: int = Field(ge=50, le=5000)

class ProfileIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=30)
    bio: str = Field(default="", max_length=180)
    avatar: str = Field(default="SQ", max_length=16)
    theme: str = "light"

class FriendRequestIn(BaseModel):
    username: str = Field(min_length=3, max_length=20)


# ---------- authentication ----------
@app.post("/api/auth/guest")
def create_guest():
    with db() as c:
        username = "wanderer_" + secrets.token_hex(4)
        cur = c.execute("INSERT INTO users(username,password_hash,is_guest,created_at) VALUES(?,NULL,1,?)", (username, now()))
        user_id = int(cur.lastrowid)
        c.execute("INSERT INTO user_profiles(user_id,display_name,avatar,theme) VALUES(?,?,?,?)", (user_id, "Wandering Adventurer", "SQ", "light"))
        c.execute("INSERT INTO weekly_goals(user_id,target_quests,target_xp,week_start) VALUES(?,3,300,?)", (user_id, week_start()))
        token = issue_token(c, user_id)
        return {"token": token, "user": profile_out(c, user_id)}


@app.post("/api/auth/register")
def register(body: AuthIn, authorization: Optional[str] = Header(default=None)):
    username = body.username.strip()
    if not re.fullmatch(r"[A-Za-z0-9_]{3,20}", username):
        raise HTTPException(400, "Username must be 3-20 characters using letters, numbers, or underscores")
    with db() as c:
        existing_user = user_from_authorization(c, authorization)
        if existing_user and not existing_user["is_guest"]:
            raise HTTPException(409, "This session already belongs to a registered account. Log out first to create another account.")
        clash = c.execute("SELECT id FROM users WHERE username=? COLLATE NOCASE", (username,)).fetchone()
        if clash and (not existing_user or clash["id"] != existing_user["id"]):
            raise HTTPException(409, "That username is already taken")
        if existing_user:
            user_id = int(existing_user["id"])
            c.execute("UPDATE users SET username=?,password_hash=?,is_guest=0 WHERE id=?", (username, hash_password(body.password), user_id))
            c.execute("UPDATE user_profiles SET display_name=? WHERE user_id=?",
                      ((body.display_name or username).strip() or username, user_id))
            token = authorization.partition(" ")[2]
        else:
            cur = c.execute("INSERT INTO users(username,password_hash,is_guest,created_at) VALUES(?,?,0,?)",
                            (username, hash_password(body.password), now()))
            user_id = int(cur.lastrowid)
            c.execute("INSERT INTO user_profiles(user_id,display_name) VALUES(?,?)",
                      (user_id, (body.display_name or username).strip() or username))
            c.execute("INSERT INTO weekly_goals(user_id,target_quests,target_xp,week_start) VALUES(?,3,300,?)",
                      (user_id, week_start()))
            token = issue_token(c, user_id)
        return {"token": token, "user": profile_out(c, user_id)}


@app.post("/api/auth/login")
def login(body: AuthIn):
    with db() as c:
        user = c.execute("SELECT * FROM users WHERE username=? COLLATE NOCASE AND is_guest=0", (body.username.strip(),)).fetchone()
        if not user or not verify_password(body.password, user["password_hash"]):
            raise HTTPException(401, "Incorrect username or password")
        token = issue_token(c, int(user["id"]))
        return {"token": token, "user": profile_out(c, int(user["id"]))}


@app.post("/api/auth/logout")
def logout(authorization: Optional[str] = Header(default=None)):
    if not authorization:
        return {"ok": True}
    with db() as c:
        token = authorization.partition(" ")[2]
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        c.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash,))
    return {"ok": True}


@app.get("/api/auth/me")
def auth_me(user_id: int = Depends(current_user_id)):
    with db() as c:
        return profile_out(c, user_id)


# ---------- quests ----------
@app.get("/api/quests")
def list_quests(difficulty: Optional[str] = None, category: Optional[str] = None,
                max_minutes: Optional[int] = None, user_id: int = Depends(current_user_id)):
    sql, args = quest_sql() + " WHERE 1=1", [user_id]
    if difficulty:
        sql += " AND q.difficulty=?"; args.append(difficulty)
    if category:
        sql += " AND q.category=?"; args.append(category)
    if max_minutes:
        sql += " AND q.minutes<=?"; args.append(max_minutes)
    with db() as c:
        return [quest_out(r) for r in c.execute(sql + " ORDER BY q.id", args)]


@app.get("/api/quests/{qid}")
def quest_detail(qid: int, user_id: int = Depends(current_user_id)):
    with db() as c:
        return quest_out(get_row(c, qid, user_id))


@app.post("/api/quests/{qid}/status")
def set_status(qid: int, body: StatusIn, user_id: int = Depends(current_user_id)):
    if body.status not in ("saved", "started", "completed", "none"):
        raise HTTPException(400, "Invalid status")
    with db() as c:
        q = get_row(c, qid, user_id)
        before, gained = unlocked(c, user_id), 0
        g = c.execute("SELECT * FROM user_progress WHERE user_id=? AND quest_id=?", (user_id, qid)).fetchone()
        cur = g["status"] if g else None
        if body.status == "saved" and cur is None:
            c.execute("INSERT INTO user_progress(user_id,quest_id,status,updated) VALUES(?,?,?,?)",
                      (user_id, qid, "saved", now()))
            log(c, user_id, f"Saved quest: {q['title']}")
        elif body.status == "none" and cur == "saved":
            c.execute("DELETE FROM user_progress WHERE user_id=? AND quest_id=?", (user_id, qid))
        elif body.status == "started" and cur in (None, "saved"):
            c.execute("INSERT INTO user_progress(user_id,quest_id,status,checked,updated) VALUES(?,?,?,?,?) "
                      "ON CONFLICT(user_id,quest_id) DO UPDATE SET status='started',updated=excluded.updated",
                      (user_id, qid, "started", "[]", now()))
            log(c, user_id, f"Started quest: {q['title']}"); touch(c, user_id)
        elif body.status == "completed" and cur != "completed":
            checked = set(json.loads(g["checked"])) if g else set()
            if len(checked) < len(json.loads(q["checklist"])):
                raise HTTPException(400, "Finish every checklist item before completing this quest")
            submission = c.execute("SELECT id FROM submissions WHERE user_id=? AND quest_id=? ORDER BY id DESC LIMIT 1",
                                   (user_id, qid)).fetchone()
            if not submission:
                raise HTTPException(400, "Submit your code and output before completing this quest")
            if g:
                c.execute("UPDATE user_progress SET status='completed',completed_at=?,updated=? WHERE user_id=? AND quest_id=?",
                          (now(), now(), user_id, qid))
            else:
                c.execute("INSERT INTO user_progress(user_id,quest_id,status,checked,updated,completed_at) VALUES(?,?,?,?,?,?)",
                          (user_id, qid, "completed", "[]", now(), now()))
            c.execute("UPDATE user_profiles SET xp=xp+? WHERE user_id=?", (q["xp"], user_id))
            c.execute("UPDATE submissions SET status='accepted',reviewed_at=?,feedback='Quest completed by its owner.' WHERE id=?",
                      (now(), submission["id"]))
            gained = q["xp"]
            log(c, user_id, f"Completed quest: {q['title']} (+{gained} XP)"); touch(c, user_id)
        return result(c, qid, user_id, before, gained)


@app.post("/api/quests/{qid}/checklist")
def toggle_item(qid: int, body: CheckIn, user_id: int = Depends(current_user_id)):
    with db() as c:
        q = get_row(c, qid, user_id)
        before = unlocked(c, user_id)
        if not 0 <= body.index < len(json.loads(q["checklist"])):
            raise HTTPException(400, "Invalid checklist item")
        g = c.execute("SELECT * FROM user_progress WHERE user_id=? AND quest_id=?", (user_id, qid)).fetchone()
        if g and g["status"] == "completed":
            raise HTTPException(400, "Quest already completed")
        checked = set(json.loads(g["checked"])) if g else set()
        (checked.add if body.done else checked.discard)(body.index)
        if g:
            c.execute("UPDATE user_progress SET status='started',checked=?,updated=? WHERE user_id=? AND quest_id=?",
                      (json.dumps(sorted(checked)), now(), user_id, qid))
        else:
            c.execute("INSERT INTO user_progress(user_id,quest_id,status,checked,updated) VALUES(?,?,?,?,?)",
                      (user_id, qid, "started", json.dumps(sorted(checked)), now()))
        if g is None or g["status"] == "saved":
            log(c, user_id, f"Started quest: {q['title']}")
        touch(c, user_id)
        return result(c, qid, user_id, before)


@app.get("/api/my-quests")
def my_quests(user_id: int = Depends(current_user_id)):
    with db() as c:
        sql = quest_sql() + " WHERE up.status IS NOT NULL ORDER BY up.updated DESC"
        return [quest_out(r) for r in c.execute(sql, (user_id,))]


@app.get("/api/dashboard")
def dashboard(user_id: int = Depends(current_user_id)):
    with db() as c:
        s = stats(c, user_id)
        total = c.execute("SELECT COUNT(*) FROM quests").fetchone()[0]
        return {**s, "total_quests": total, "overall_pct": round(100 * s["completed"] / total) if total else 0,
                "xp_in_level": s["xp"] % XP_PER_LEVEL, "xp_per_level": XP_PER_LEVEL,
                "recent": [dict(r) for r in c.execute("SELECT text,ts FROM user_activity WHERE user_id=? ORDER BY id DESC LIMIT 8", (user_id,))],
                "active": [quest_out(r) for r in c.execute(quest_sql() + " WHERE up.status='started' ORDER BY up.updated DESC", (user_id,))]}


@app.get("/api/achievements")
def achievements(user_id: int = Depends(current_user_id)):
    with db() as c:
        b = badges(stats(c, user_id))
        return {"badges": b, "unlocked": sum(x["unlocked"] for x in b)}


@app.post("/api/reset")
def reset(user_id: int = Depends(current_user_id)):
    """Reset the signed-in user's practice data without deleting their account or friends."""
    with db() as c:
        files = c.execute("SELECT screenshot_path FROM submissions WHERE user_id=? AND screenshot_path<>''", (user_id,)).fetchall()
        for row in files:
            path = (UPLOAD_DIR / row["screenshot_path"]).resolve()
            if path.is_relative_to(UPLOAD_DIR.resolve()) and path.exists():
                path.unlink(missing_ok=True)
        c.execute("DELETE FROM submissions WHERE user_id=?", (user_id,))
        c.execute("DELETE FROM user_progress WHERE user_id=?", (user_id,))
        c.execute("DELETE FROM user_activity WHERE user_id=?", (user_id,))
        c.execute("UPDATE user_profiles SET xp=0,streak=0,best_streak=0,last_active=NULL WHERE user_id=?", (user_id,))
    return {"ok": True}


# ---------- profile and themes ----------
@app.get("/api/profile")
def get_profile(user_id: int = Depends(current_user_id)):
    with db() as c:
        return profile_out(c, user_id)


@app.put("/api/profile")
def update_profile(body: ProfileIn, user_id: int = Depends(current_user_id)):
    if body.theme not in ALLOWED_THEMES:
        raise HTTPException(400, "Theme must be light, dark, anime, or cute")
    display_name = body.display_name.strip()
    if not display_name:
        raise HTTPException(400, "Display name cannot be empty")
    avatar = body.avatar if body.avatar in AVATAR_CHOICES else "SQ"
    with db() as c:
        c.execute("UPDATE user_profiles SET display_name=?,bio=?,avatar=?,theme=? WHERE user_id=?",
                  (display_name, body.bio.strip(), avatar, body.theme, user_id))
        log(c, user_id, "Updated adventurer profile")
        return profile_out(c, user_id)


# ---------- weekly goals and statistics ----------
@app.get("/api/weekly-goal")
def get_weekly_goal(user_id: int = Depends(current_user_id)):
    with db() as c:
        return weekly_progress(c, user_id)


@app.put("/api/weekly-goal")
def set_weekly_goal(body: GoalIn, user_id: int = Depends(current_user_id)):
    with db() as c:
        ensure_weekly_goal(c, user_id)
        c.execute("UPDATE weekly_goals SET target_quests=?,target_xp=? WHERE user_id=?",
                  (body.target_quests, body.target_xp, user_id))
        log(c, user_id, f"Updated weekly goals: {body.target_quests} quests and {body.target_xp} XP")
        return weekly_progress(c, user_id)


@app.get("/api/stats")
def detailed_stats(user_id: int = Depends(current_user_id)):
    with db() as c:
        s = stats(c, user_id)
        since = (date.today() - timedelta(days=34)).isoformat()
        active_rows = c.execute("SELECT substr(ts,1,10) day,COUNT(*) count FROM user_activity "
                                "WHERE user_id=? AND substr(ts,1,10)>=? GROUP BY substr(ts,1,10)",
                                (user_id, since)).fetchall()
        active = {r["day"]: r["count"] for r in active_rows}
        heatmap = [{"date": (date.today() - timedelta(days=34 - i)).isoformat(),
                    "count": int(active.get((date.today() - timedelta(days=34 - i)).isoformat(), 0))}
                   for i in range(35)]
        per_skill_rows = c.execute("SELECT q.category,COUNT(*) done,COALESCE(SUM(q.xp),0) xp FROM user_progress up "
                                   "JOIN quests q ON q.id=up.quest_id WHERE up.user_id=? AND up.status='completed' "
                                   "GROUP BY q.category ORDER BY done DESC", (user_id,)).fetchall()
        return {**s, "heatmap": heatmap, "completed_by_category": [dict(r) for r in per_skill_rows],
                "minutes_estimated": c.execute("SELECT COALESCE(SUM(q.minutes),0) FROM user_progress up " 
                                                "JOIN quests q ON q.id=up.quest_id WHERE up.user_id=? AND up.status='completed'",
                                                (user_id,)).fetchone()[0]}


# ---------- learning roadmaps ----------
@app.get("/api/roadmaps")
def list_roadmaps(user_id: int = Depends(current_user_id)):
    with db() as c:
        enrolled = {r["roadmap_id"] for r in c.execute("SELECT roadmap_id FROM roadmap_enrollments WHERE user_id=?", (user_id,))}
        completed = {r["quest_id"] for r in c.execute("SELECT quest_id FROM user_progress WHERE user_id=? AND status='completed'", (user_id,))}
        result_list = []
        for roadmap in ROADMAPS:
            steps = []
            for qid in roadmap["quest_ids"]:
                q = c.execute("SELECT id,title,difficulty,minutes,xp FROM quests WHERE id=?", (qid,)).fetchone()
                if q:
                    steps.append({**dict(q), "completed": qid in completed})
            result_list.append({**roadmap, "steps": steps, "enrolled": roadmap["id"] in enrolled,
                                "completed_steps": sum(x["completed"] for x in steps), "total_steps": len(steps),
                                "progress_pct": round(100 * sum(x["completed"] for x in steps) / max(1, len(steps)))})
        return result_list


@app.post("/api/roadmaps/{roadmap_id}/enroll")
def enroll_roadmap(roadmap_id: str, user_id: int = Depends(current_user_id)):
    if roadmap_id not in {r["id"] for r in ROADMAPS}:
        raise HTTPException(404, "Roadmap not found")
    with db() as c:
        c.execute("INSERT OR IGNORE INTO roadmap_enrollments(user_id,roadmap_id,enrolled_at) VALUES(?,?,?)",
                  (user_id, roadmap_id, now()))
        log(c, user_id, f"Joined roadmap: {next(r['title'] for r in ROADMAPS if r['id']==roadmap_id)}")
    return {"ok": True, "roadmap_id": roadmap_id}


# ---------- Skill Garden ----------
@app.get("/api/garden")
def skill_garden(user_id: int = Depends(current_user_id)):
    skills = [
        {"id": "Python", "name": "Python Tree", "label": "PY", "description": "Backend, scripting, and automation."},
        {"id": "Web Development", "name": "Web Blossom", "label": "WEB", "description": "HTML, CSS, JavaScript, and APIs."},
        {"id": "General Programming", "name": "Logic Crystal", "label": "LOGIC", "description": "Problem solving and core programming."},
    ]
    with db() as c:
        for plant in skills:
            row = c.execute("SELECT COUNT(*) n,COALESCE(SUM(q.xp),0) xp FROM user_progress up JOIN quests q ON q.id=up.quest_id "
                            "WHERE up.user_id=? AND up.status='completed' AND q.category=?", (user_id, plant["id"])).fetchone()
            plant["completed"] = int(row["n"])
            plant["xp"] = int(row["xp"])
            plant["level"] = min(5, 1 + row["n"] // 2)
            plant["stage"] = ["Seedling", "Sprout", "Growing", "Blooming", "Flourishing"][plant["level"] - 1]
            plant["next_at"] = min(10, (plant["level"] - 1) * 2 + 2)
            plant["progress_pct"] = 100 if plant["level"] == 5 else min(100, int((row["n"] % 2) * 50))
        total = sum(x["completed"] for x in skills)
        return {"plants": skills, "completed_quests": total,
                "message": "Every completed quest gives your garden a little more life." if total else "Your garden is waiting. Complete a quest to plant your first seed."}


# ---------- Daily tech topic (curated, rotating offline list; not a live trend feed) ----------
@app.get("/api/trending")
def trending_topic():
    today = date.today()
    index = today.toordinal() % len(TOPICS)
    topic = dict(TOPICS[index])
    topic["date"] = today.isoformat()
    topic["source_label"] = "Curated daily rotation · not a live trend tracker yet"
    return topic


# ---------- Project submissions ----------
def validate_web_url(value: str, label: str) -> str:
    value = value.strip()
    if not value:
        return ""
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise HTTPException(400, f"{label} must start with http:// or https://")
    return value


@app.post("/api/submissions")
async def create_submission(
    quest_id: int = Form(...),
    code_text: str = Form(""),
    output_text: str = Form(""),
    github_url: str = Form(""),
    demo_url: str = Form(""),
    notes: str = Form(""),
    screenshot: Optional[UploadFile] = File(default=None),
    user_id: int = Depends(current_user_id),
):
    code_text = code_text.strip()
    output_text = output_text.strip()
    notes = notes.strip()
    if len(code_text) > 200_000:
        raise HTTPException(413, "Code submission is limited to 200,000 characters")
    if len(output_text) > 20_000 or len(notes) > 2_000:
        raise HTTPException(413, "Output or notes are too long")
    github_url = validate_web_url(github_url, "GitHub URL")
    demo_url = validate_web_url(demo_url, "Demo URL")
    if not code_text and not github_url:
        raise HTTPException(400, "Add your code or a GitHub repository link")
    if not output_text and not screenshot and not demo_url:
        raise HTTPException(400, "Add output text, an output screenshot, or a live demo link")

    stored_path = ""
    if screenshot and screenshot.filename:
        allowed = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
        if screenshot.content_type not in allowed:
            raise HTTPException(400, "Screenshot must be PNG, JPEG, or WebP")
        # Read a bounded amount rather than trusting the browser-provided content length.
        data = await screenshot.read(MAX_SCREENSHOT_BYTES + 1)
        if len(data) > MAX_SCREENSHOT_BYTES:
            raise HTTPException(413, "Screenshot must be 3 MB or smaller")
        signatures = {"image/png": data.startswith(b"\x89PNG\r\n\x1a\n"),
                      "image/jpeg": data.startswith(b"\xff\xd8\xff"),
                      "image/webp": len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"}
        if not signatures.get(screenshot.content_type, False):
            raise HTTPException(400, "The uploaded file does not match its image format")
        directory = UPLOAD_DIR / f"user_{user_id}"
        directory.mkdir(parents=True, exist_ok=True)
        filename = secrets.token_hex(16) + allowed[screenshot.content_type]
        destination = directory / filename
        destination.write_bytes(data)
        stored_path = destination.relative_to(UPLOAD_DIR).as_posix()

    with db() as c:
        q = c.execute("SELECT title FROM quests WHERE id=?", (quest_id,)).fetchone()
        if not q:
            if stored_path:
                (UPLOAD_DIR / stored_path).unlink(missing_ok=True)
            raise HTTPException(404, "Quest not found")
        cur = c.execute("INSERT INTO submissions(user_id,quest_id,code_text,output_text,github_url,demo_url,screenshot_path,notes,status,created_at) "
                        "VALUES(?,?,?,?,?,?,?,?,?,?)",
                        (user_id, quest_id, code_text, output_text, github_url, demo_url, stored_path, notes, "submitted", now()))
        c.execute("INSERT INTO user_progress(user_id,quest_id,status,checked,updated) VALUES(?,?,?,?,?) "
                  "ON CONFLICT(user_id,quest_id) DO UPDATE SET status=CASE WHEN user_progress.status='completed' THEN 'completed' ELSE 'started' END,updated=excluded.updated",
                  (user_id, quest_id, "started", "[]", now()))
        log(c, user_id, f"Submitted project: {q['title']}")
        touch(c, user_id)
        row = c.execute("SELECT * FROM submissions WHERE id=?", (cur.lastrowid,)).fetchone()
        return submission_out(row)


@app.get("/api/submissions")
def list_submissions(quest_id: Optional[int] = None, user_id: int = Depends(current_user_id)):
    with db() as c:
        sql = "SELECT s.*,q.title quest_title FROM submissions s JOIN quests q ON q.id=s.quest_id WHERE s.user_id=?"
        args: list = [user_id]
        if quest_id is not None:
            sql += " AND s.quest_id=?"; args.append(quest_id)
        sql += " ORDER BY s.id DESC"
        return [submission_out(r) for r in c.execute(sql, args)]


@app.get("/api/submissions/{submission_id}/screenshot")
def get_submission_screenshot(submission_id: int, user_id: int = Depends(current_user_id)):
    with db() as c:
        row = c.execute("SELECT screenshot_path FROM submissions WHERE id=? AND user_id=?", (submission_id, user_id)).fetchone()
        if not row or not row["screenshot_path"]:
            raise HTTPException(404, "Screenshot not found")
        path = (UPLOAD_DIR / row["screenshot_path"]).resolve()
        if not path.is_relative_to(UPLOAD_DIR.resolve()) or not path.is_file():
            raise HTTPException(404, "Screenshot not found")
        return FileResponse(path, headers={"Cache-Control": "private, max-age=60"})


# ---------- friends-only social features ----------
def friend_ids(c: sqlite3.Connection, user_id: int) -> set[int]:
    rows = c.execute("SELECT sender_id,receiver_id FROM friend_requests WHERE status='accepted' AND (sender_id=? OR receiver_id=?)",
                     (user_id, user_id)).fetchall()
    ids: set[int] = set()
    for row in rows:
        ids.add(int(row["receiver_id"] if row["sender_id"] == user_id else row["sender_id"]))
    return ids


def public_friend(c: sqlite3.Connection, user_id: int, friendship_status: str = "friend") -> dict:
    row = c.execute("SELECT u.id,u.username,p.display_name,p.avatar,p.xp,p.streak,p.best_streak FROM users u "
                    "JOIN user_profiles p ON p.user_id=u.id WHERE u.id=?", (user_id,)).fetchone()
    return {"id": row["id"], "username": row["username"], "display_name": row["display_name"], "avatar": row["avatar"],
            "xp": row["xp"], "level": row["xp"] // XP_PER_LEVEL + 1, "rank": rank_for_xp(row["xp"]),
            "streak": row["streak"], "best_streak": row["best_streak"], "status": friendship_status}


@app.get("/api/friends")
def list_friends(user_id: int = Depends(current_user_id)):
    with db() as c:
        ids = friend_ids(c, user_id)
        friends = [public_friend(c, fid) for fid in ids]
        incoming_rows = c.execute("SELECT fr.id,fr.created_at,u.id user_id FROM friend_requests fr JOIN users u ON u.id=fr.sender_id "
                                  "WHERE fr.receiver_id=? AND fr.status='pending' ORDER BY fr.id DESC", (user_id,)).fetchall()
        outgoing_rows = c.execute("SELECT fr.id,fr.created_at,u.id user_id FROM friend_requests fr JOIN users u ON u.id=fr.receiver_id "
                                  "WHERE fr.sender_id=? AND fr.status='pending' ORDER BY fr.id DESC", (user_id,)).fetchall()
        return {"friends": sorted(friends, key=lambda x: (-x["xp"], x["username"].lower())),
                "incoming": [{"request_id": r["id"], "created_at": r["created_at"], **public_friend(c, r["user_id"], "pending")} for r in incoming_rows],
                "outgoing": [{"request_id": r["id"], "created_at": r["created_at"], **public_friend(c, r["user_id"], "pending")} for r in outgoing_rows]}


@app.post("/api/friends/requests")
def send_friend_request(body: FriendRequestIn, user_id: int = Depends(current_user_id)):
    with db() as c:
        requester = c.execute("SELECT is_guest FROM users WHERE id=?", (user_id,)).fetchone()
        if requester and requester["is_guest"]:
            raise HTTPException(403, "Create a profile from the Profile page before adding friends")
        target = c.execute("SELECT id,is_guest FROM users WHERE username=? COLLATE NOCASE", (body.username.strip(),)).fetchone()
        if not target or target["is_guest"]:
            raise HTTPException(404, "Registered user not found. Ask your friend for their SideQuest username.")
        receiver_id = int(target["id"])
        if receiver_id == user_id:
            raise HTTPException(400, "You cannot add yourself as a friend")
        existing = c.execute("SELECT * FROM friend_requests WHERE (sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?)",
                             (user_id, receiver_id, receiver_id, user_id)).fetchall()
        if any(r["status"] == "accepted" for r in existing):
            raise HTTPException(409, "You are already friends")
        reverse = next((r for r in existing if r["sender_id"] == receiver_id and r["receiver_id"] == user_id and r["status"] == "pending"), None)
        if reverse:
            c.execute("UPDATE friend_requests SET status='accepted' WHERE id=?", (reverse["id"],))
            return {"ok": True, "status": "accepted", "message": "Friend request accepted automatically because they already invited you."}
        sent = next((r for r in existing if r["sender_id"] == user_id and r["receiver_id"] == receiver_id), None)
        if sent:
            raise HTTPException(409, "A friend request is already pending")
        cur = c.execute("INSERT INTO friend_requests(sender_id,receiver_id,status,created_at) VALUES(?,?,'pending',?)",
                        (user_id, receiver_id, now()))
        return {"ok": True, "request_id": cur.lastrowid, "status": "pending"}


@app.post("/api/friends/requests/{request_id}/accept")
def accept_friend_request(request_id: int, user_id: int = Depends(current_user_id)):
    with db() as c:
        row = c.execute("SELECT * FROM friend_requests WHERE id=? AND receiver_id=? AND status='pending'", (request_id, user_id)).fetchone()
        if not row:
            raise HTTPException(404, "Pending friend request not found")
        c.execute("UPDATE friend_requests SET status='accepted' WHERE id=?", (request_id,))
        return {"ok": True}


@app.delete("/api/friends/{friend_user_id}")
def remove_friend(friend_user_id: int, user_id: int = Depends(current_user_id)):
    with db() as c:
        c.execute("DELETE FROM friend_requests WHERE status='accepted' AND ((sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?))",
                  (user_id, friend_user_id, friend_user_id, user_id))
    return {"ok": True}


@app.get("/api/leaderboard")
def friends_leaderboard(user_id: int = Depends(current_user_id)):
    with db() as c:
        ids = friend_ids(c, user_id) | {user_id}
        people = [public_friend(c, uid, "you" if uid == user_id else "friend") for uid in ids]
        people.sort(key=lambda p: (-p["xp"], p["username"].lower()))
        for index, person in enumerate(people, 1):
            person["position"] = index
        return {"scope": "you and accepted friends only", "entries": people}


# Static app is mounted last so /api routes are not swallowed by the frontend.
app.mount("/", StaticFiles(directory=BASE / "static", html=True), name="static")
