# SideQuest

**Learn a little, build a little, grow a little.**

SideQuest is a gamified project-learning website. Learners pick small coding quests, work through a checklist, submit code and proof of output, earn XP, track goals and streaks, grow their Skill Garden, and compare progress with accepted friends.

## Features

### Learning
- Quest catalogue with difficulty, category, and time filters.
- Individual quest briefs, required features, suggested technologies, and checklists.
- Learning roadmaps for Python, web development, and general problem solving.
- Weekly targets for number of completed quests and XP.
- Daily streaks, activity heatmap, estimated learning time, XP levels, ranks, and achievements.

### Skill Garden and style
- A plant for each skill category that grows as quests are completed.
- Original anime-adventure ranks, guild styling, icons, and reward feedback.
- Four saved visual treatments: Light, Dark, Anime, and Cute, all based on Palette 1's slate blue, white, and warm gold colors.
- Professional Inter typography with a system-font fallback and text-based skill/avatar labels instead of emoji.
- Profile with username, display name, avatar, and short bio.

### Project submissions
- Submit source code or a GitHub repository URL.
- Add terminal output, an output screenshot, or a live demo URL.
- Include a short reflection on what you learned.
- Submission history is private to the submitting account. Screenshot uploads are restricted to PNG, JPEG, and WebP and capped at 3 MB. Submitted files are stored, never executed by the app.
- A quest cannot be completed until its checklist is finished and a project submission exists. When the learner marks it complete, SideQuest records the submission as accepted automatically. This is a self-directed learning tracker, not an instructor moderation system.

### Social
- User accounts with password hashing and session tokens.
- Send and accept friend requests by username.
- A leaderboard containing only the current learner and accepted friends. There is no global leaderboard.

### Daily topic
- A rotating technology learning topic with a mini challenge and reference link.
- **Current limitation:** the topic list is curated and changes by date. It is not a live global trend detector yet.

## Visual design

The interface follows the first reference palette: slate blue `#4E598C`, white `#FFFFFF`, and warm gold `#F9C784`. Panels, hero sections, buttons, forms, and status tags use variations of those colors to keep the interface consistent. Inter is used as the primary font with system fallbacks.

## Technology stack

- Frontend: HTML, CSS, JavaScript
- Backend: Python, FastAPI, Uvicorn
- Database: SQLite
- Uploads: private files in the configured upload directory
- Tests: pytest and FastAPI TestClient

## Run locally on Windows

Open this folder in VS Code. In **Terminal → New Terminal**, run:

```powershell
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Open **http://127.0.0.1:8000**. FastAPI's interactive documentation is at **http://127.0.0.1:8000/docs**.

If PowerShell blocks environment activation, run the environment Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

The app creates `sidequest.db` and seeds the quests the first time it runs. If the database is an older SideQuest v1 database, the app keeps the legacy tables as a backup and imports the single existing profile, quest progress, and activity into the default Guest profile once. Back up your local `.db` file before upgrading any existing installation.

## Run tests

Stop the server if it is running, then run:

```powershell
python -m pytest -q
```

The test suite uses a separate temporary database. It checks quest filters and completion rules, XP idempotency, accounts and data isolation, friend-only leaderboard behavior, weekly goals, themes, roadmaps, garden, daily topic, and submissions.

## Deploy on Render

Create a **Web Service** from the GitHub repository that contains this project. If the repository root is the `sidequest` folder, use these settings:

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

If SideQuest lives inside a larger repository, set Render's **Root Directory** to `sidequest`.

### Persistent storage matters

SQLite and uploaded screenshots are local files. On Render, attach a persistent disk mounted at `/var/data` for production-like use and set:

```text
SIDEQUEST_DB=/var/data/sidequest.db
SIDEQUEST_UPLOAD_DIR=/var/data/uploads
```

Without persistent storage, SQLite progress and screenshot uploads may disappear when the service is replaced or redeployed. A free web service may not support persistent disks, depending on the host's current plan rules. Check the hosting plan before relying on it for real user data.

## Privacy and security notes

- Passwords are stored as PBKDF2-SHA256 hashes, not plain text.
- Session tokens are random bearer tokens stored as SHA-256 hashes in SQLite.
- The guest session is local to the browser token. Create an account from the Profile page to attach that progress to a username and make it easier to recover later.
- Private screenshot endpoints require the submitting user's session.
- URLs submitted as repository/demo links must use HTTP or HTTPS.
- Do not submit API keys, passwords, or private information in code or screenshots.
- This is a learning-project MVP. It currently has no email verification, password reset flow, automatic code execution, instructor moderation, rate limiting, or real-time trend aggregation. Add these before positioning it as a production service for untrusted public users.

## Repository hygiene

`.gitignore` excludes SQLite databases, uploads, Python caches, virtual environments, and local environment files. Keep your working database and any personal submissions out of Git. Do not commit `.env` or credentials.

---

**SideQuest — one quest at a time.**
## What's New in SideQuest

SideQuest has evolved into a gamified learning platform that helps developers turn their learning goals into practical coding projects. It combines structured learning, progress tracking, project submissions, and game-inspired rewards in one place.

### Features

- **Learning Roadmaps:** Follow structured learning paths and progress through coding quests.
- **Weekly Goals:** Set learning targets and track your progress throughout the week.
- **Streak Tracking:** Build consistency by maintaining daily learning streaks.
- **Skill Garden:** Visualize your learning journey as your skills grow with your progress.
- **Anime-Inspired Gamification:** Earn XP, advance through ranks, and unlock achievements.
- **Trending Topic of the Day:** Discover technology topics and related learning challenges.
- **Learning Statistics:** Track quest completion, XP, streaks, and learning progress.
- **Project Submissions:** Submit source code, output screenshots, project links, and notes to demonstrate completed work.
- **Custom Themes:** Choose between Light, Dark, Anime, and Cute visual styles.
- **Personal Profiles:** Showcase your learning progress, skills, and achievements.
- **Friends-Only Leaderboard:** Compare progress with accepted friends instead of competing on a public global leaderboard.

### Project Submission Workflow

SideQuest encourages users to build real projects instead of simply marking tasks as complete.

1. Select a coding quest.
2. Follow its requirements and checklist.
3. Build and test the project locally.
4. Submit the relevant code, output evidence, or project links.
5. Track the submission and completion status.

For example, a user completing a Number Guessing Game can submit the source code and a screenshot of the program running.

### Design Philosophy

SideQuest combines a professional interface with playful, game-inspired progression.

The updated design uses the following primary color palette:

| Color | Hex Code | Purpose |
|---|---|---|
| Slate Blue | `#4E598C` | Primary interface elements |
| White | `#FFFFFF` | Clean surfaces and readability |
| Warm Gold | `#F9C784` | Highlights and visual accents |

The interface also supports multiple themes so users can personalize their learning environment.

### Technology Stack

- **Frontend:** HTML, CSS, JavaScript
- **Backend:** Python, FastAPI
- **Server:** Uvicorn
- **Database:** SQLite
- **Testing:** pytest and httpx
- **Version Control:** Git and GitHub

### Run Locally

Clone the repository and open the SideQuest directory:

```bash
git clone https://github.com/bharvadnidhi9/Vibe-coding-Work.git
cd Vibe-coding-Work/SideQuest
```

Create and activate a virtual environment:

```bash
python -m venv .venv
```

On Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Start the development server:

```bash
python -m uvicorn main:app --reload
```

Open `http://127.0.0.1:8000` in your browser.

FastAPI's interactive API documentation is available at `http://127.0.0.1:8000/docs`.

### Run Tests

Run the automated test suite from the SideQuest directory:

```bash
python -m pytest -q
```

### Development Roadmap

Potential future improvements include:

- Persistent cloud database storage for reliable progress tracking.
- Automated checks and reviewer feedback for project submissions.
- Live technology-trend integrations.
- Expanded roadmap customization and
