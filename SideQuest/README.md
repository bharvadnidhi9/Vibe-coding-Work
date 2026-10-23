# SideQuest
*Your next coding adventure starts here.*

A gamified coding-project generator. Users pick a difficulty, category and time budget, receive a quest, work through its checklist, and earn XP, levels, streaks and badges.

## Stack
HTML/CSS/JavaScript (frontend) | Python + FastAPI (backend) | SQLite (database) | pytest (tests)

## Run
```bash
pip install -r requirements.txt
uvicorn main:app --reload
```
Open http://127.0.0.1:8000. The SQLite file `sidequest.db` is created and seeded automatically on first start.

## Test
```bash
pytest -q
```
Covers: quest filters, checklist rule, XP awarded exactly once, level calculation, badges, and persistence after a simulated restart.

## Structure
```
main.py        FastAPI app, database logic, XP/streak/badge rules
seed.py        Predefined quest data
static/        index.html, style.css, app.js (hash-routed single page app)
tests/         API tests
```

## API
| Method | Endpoint | Purpose |
|---|---|---|
| GET | /api/quests?difficulty=&category=&max_minutes= | Filtered quest list |
| GET | /api/quests/{id} | Quest details and progress |
| POST | /api/quests/{id}/status | saved / started / completed / none |
| POST | /api/quests/{id}/checklist | Tick or untick a checklist item |
| GET | /api/my-quests | Saved, started, completed quests |
| GET | /api/dashboard | XP, level, streak, activity, active quests |
| GET | /api/achievements | Badge list with unlock state |
| POST | /api/reset | Clear progress (demo) |

## Rules
- XP per quest: Beginner 50, Intermediate 100, Advanced 200. 100 XP = 1 level.
- A quest can be completed only when every checklist item is ticked; XP is awarded once.
- Streak increases for each consecutive day with activity and resets after a missed day.
