"""SideQuest backend: FastAPI + SQLite. Run: uvicorn main:app --reload"""
import json, os, sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from seed import QUESTS

BASE = Path(__file__).parent
DB_PATH = os.environ.get("SIDEQUEST_DB", str(BASE / "sidequest.db"))
XP_BY_DIFFICULTY = {"Beginner": 50, "Intermediate": 100, "Advanced": 200}
XP_PER_LEVEL = 100

SCHEMA = """
CREATE TABLE IF NOT EXISTS quests(id INTEGER PRIMARY KEY, title TEXT, description TEXT, problem TEXT,
  features TEXT, tech TEXT, difficulty TEXT, category TEXT, minutes INTEGER, xp INTEGER, checklist TEXT);
CREATE TABLE IF NOT EXISTS progress(quest_id INTEGER PRIMARY KEY REFERENCES quests(id),
  status TEXT NOT NULL, checked TEXT DEFAULT '[]', updated TEXT, completed_at TEXT);
CREATE TABLE IF NOT EXISTS profile(id INTEGER PRIMARY KEY CHECK(id=1), xp INTEGER DEFAULT 0,
  streak INTEGER DEFAULT 0, best_streak INTEGER DEFAULT 0, last_active TEXT);
CREATE TABLE IF NOT EXISTS activity(id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT, ts TEXT);
"""
Q_SQL = ("SELECT q.*, g.status AS pstatus, g.checked AS pchecked FROM quests q "
         "LEFT JOIN progress g ON g.quest_id = q.id")

def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def now():
    return datetime.now().isoformat(timespec="seconds")

def init_db():
    with db() as c:
        c.executescript(SCHEMA)
        c.execute("INSERT OR IGNORE INTO profile(id) VALUES (1)")
        if c.execute("SELECT COUNT(*) FROM quests").fetchone()[0] == 0:
            for t, d, p, f, tech, diff, cat, mins in QUESTS:
                checklist = ["Set up the project folder"] + f + ["Test everything and commit to Git"]
                c.execute("INSERT INTO quests(title,description,problem,features,tech,difficulty,category,minutes,xp,checklist)"
                          " VALUES (?,?,?,?,?,?,?,?,?,?)",
                          (t, d, p, json.dumps(f), json.dumps(tech), diff, cat, mins,
                           XP_BY_DIFFICULTY[diff], json.dumps(checklist)))

init_db()
app = FastAPI(title="SideQuest API")

# ---------- helpers ----------
def quest_out(row):
    q = dict(row)
    for k in ("features", "tech", "checklist"):
        q[k] = json.loads(q[k])
    q["status"] = q.pop("pstatus")
    q["checked"] = json.loads(q.pop("pchecked") or "[]")
    return q

def get_row(c, qid):
    row = c.execute(Q_SQL + " WHERE q.id=?", (qid,)).fetchone()
    if not row:
        raise HTTPException(404, "Quest not found")
    return row

def log(c, text):
    c.execute("INSERT INTO activity(text, ts) VALUES (?,?)", (text, now()))

def touch(c):
    """Update the daily streak whenever the user does something."""
    p = c.execute("SELECT * FROM profile WHERE id=1").fetchone()
    today = date.today()
    if p["last_active"] == today.isoformat():
        return
    yesterday = (today - timedelta(days=1)).isoformat()
    streak = p["streak"] + 1 if p["last_active"] == yesterday else 1
    c.execute("UPDATE profile SET streak=?, best_streak=MAX(best_streak,?), last_active=? WHERE id=1",
              (streak, streak, today.isoformat()))

def stats(c):
    p = c.execute("SELECT * FROM profile WHERE id=1").fetchone()
    rows = c.execute("SELECT q.category cat, q.difficulty diff, g.status st FROM progress g "
                     "JOIN quests q ON q.id=g.quest_id").fetchall()
    done = [r for r in rows if r["st"] == "completed"]
    today = date.today()
    active = p["last_active"] in (today.isoformat(), (today - timedelta(days=1)).isoformat())
    return {"xp": p["xp"], "level": p["xp"] // XP_PER_LEVEL + 1,
            "streak": p["streak"] if active else 0, "best": p["best_streak"],
            "saved": sum(r["st"] == "saved" for r in rows),
            "started": sum(r["st"] in ("started", "completed") for r in rows),
            "completed": len(done),
            "web": sum(r["cat"] == "Web Development" for r in done),
            "python": sum(r["cat"] == "Python" for r in done),
            "adv": sum(r["diff"] == "Advanced" for r in done)}

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

def badges(s):
    return [{"id": i, "name": n, "desc": d, "unlocked": bool(f(s))} for i, n, d, f in BADGES]

def unlocked(c):
    return {b["id"] for b in badges(stats(c)) if b["unlocked"]}

def result(c, qid, before, gained=0):
    new = [b["name"] for b in badges(stats(c)) if b["unlocked"] and b["id"] not in before]
    return {"quest": quest_out(get_row(c, qid)), "xp_gained": gained, "new_badges": new}

# ---------- models ----------
class StatusIn(BaseModel):
    status: str

class CheckIn(BaseModel):
    index: int
    done: bool

# ---------- routes ----------
@app.get("/api/quests")
def list_quests(difficulty: Optional[str] = None, category: Optional[str] = None,
                max_minutes: Optional[int] = None):
    sql, args = Q_SQL + " WHERE 1=1", []
    if difficulty:
        sql += " AND q.difficulty=?"; args.append(difficulty)
    if category:
        sql += " AND q.category=?"; args.append(category)
    if max_minutes:
        sql += " AND q.minutes<=?"; args.append(max_minutes)
    with db() as c:
        return [quest_out(r) for r in c.execute(sql + " ORDER BY q.id", args)]

@app.get("/api/quests/{qid}")
def quest_detail(qid: int):
    with db() as c:
        return quest_out(get_row(c, qid))

@app.post("/api/quests/{qid}/status")
def set_status(qid: int, body: StatusIn):
    if body.status not in ("saved", "started", "completed", "none"):
        raise HTTPException(400, "Invalid status")
    with db() as c:
        q = get_row(c, qid)
        before, gained = unlocked(c), 0
        g = c.execute("SELECT * FROM progress WHERE quest_id=?", (qid,)).fetchone()
        cur = g["status"] if g else None
        up = ("INSERT INTO progress(quest_id,status,updated) VALUES(?,?,?) ON CONFLICT(quest_id) "
              "DO UPDATE SET status=excluded.status, updated=excluded.updated")
        if body.status == "saved" and cur is None:
            c.execute(up, (qid, "saved", now())); log(c, f"Saved quest: {q['title']}")
        elif body.status == "none" and cur == "saved":
            c.execute("DELETE FROM progress WHERE quest_id=?", (qid,))
        elif body.status == "started" and cur in (None, "saved"):
            c.execute(up, (qid, "started", now())); log(c, f"Started quest: {q['title']}"); touch(c)
        elif body.status == "completed" and cur != "completed":
            checked = set(json.loads(g["checked"])) if g else set()
            if len(checked) < len(json.loads(q["checklist"])):
                raise HTTPException(400, "Finish every checklist item before completing this quest")
            c.execute("UPDATE progress SET status='completed', completed_at=?, updated=? WHERE quest_id=?",
                      (now(), now(), qid))
            c.execute("UPDATE profile SET xp = xp + ? WHERE id=1", (q["xp"],))
            gained = q["xp"]
            log(c, f"Completed quest: {q['title']} (+{gained} XP)"); touch(c)
        return result(c, qid, before, gained)

@app.post("/api/quests/{qid}/checklist")
def toggle_item(qid: int, body: CheckIn):
    with db() as c:
        q = get_row(c, qid)
        before = unlocked(c)
        if not 0 <= body.index < len(json.loads(q["checklist"])):
            raise HTTPException(400, "Invalid checklist item")
        g = c.execute("SELECT * FROM progress WHERE quest_id=?", (qid,)).fetchone()
        if g and g["status"] == "completed":
            raise HTTPException(400, "Quest already completed")
        checked = set(json.loads(g["checked"])) if g else set()
        (checked.add if body.done else checked.discard)(body.index)
        c.execute("INSERT INTO progress(quest_id,status,checked,updated) VALUES(?,?,?,?) ON CONFLICT(quest_id) "
                  "DO UPDATE SET status='started', checked=excluded.checked, updated=excluded.updated",
                  (qid, "started", json.dumps(sorted(checked)), now()))
        if g is None or g["status"] == "saved":
            log(c, f"Started quest: {q['title']}")
        touch(c)
        return result(c, qid, before)

@app.get("/api/my-quests")
def my_quests():
    with db() as c:
        return [quest_out(r) for r in c.execute(Q_SQL + " WHERE g.status IS NOT NULL ORDER BY g.updated DESC")]

@app.get("/api/dashboard")
def dashboard():
    with db() as c:
        s = stats(c)
        total = c.execute("SELECT COUNT(*) FROM quests").fetchone()[0]
        return {**s, "total_quests": total, "overall_pct": round(100 * s["completed"] / total),
                "xp_in_level": s["xp"] % XP_PER_LEVEL, "xp_per_level": XP_PER_LEVEL,
                "recent": [dict(r) for r in c.execute("SELECT text, ts FROM activity ORDER BY id DESC LIMIT 8")],
                "active": [quest_out(r) for r in c.execute(Q_SQL + " WHERE g.status='started' ORDER BY g.updated DESC")]}

@app.get("/api/achievements")
def achievements():
    with db() as c:
        b = badges(stats(c))
        return {"badges": b, "unlocked": sum(x["unlocked"] for x in b)}

@app.post("/api/reset")
def reset():
    """Clear all progress (handy for demos)."""
    with db() as c:
        c.execute("DELETE FROM progress"); c.execute("DELETE FROM activity")
        c.execute("UPDATE profile SET xp=0, streak=0, best_streak=0, last_active=NULL")
    return {"ok": True}

app.mount("/", StaticFiles(directory=BASE / "static", html=True), name="static")
