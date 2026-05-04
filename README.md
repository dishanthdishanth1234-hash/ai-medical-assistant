
# AI Medical Assistant (production-style demo)

Full-stack demo: **FastAPI + MySQL + JWT** backend and a **vanilla HTML/CSS/JS** frontend with a medical-themed dashboard, AI chat, symptom checker, health tracking, and local appointment notes.

## Quick start

### 1) MySQL database

1. Install MySQL 8+ and start the service.
2. Create schema and tables:

```bash
mysql -u root -p < database/schema.sql
```

3. Create a user (optional) and grant privileges, or use `root` locally.

### 2) Python backend

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Copy `backend/.env.example` to **`backend/.env`** (same folder as `app.py`). Settings are always read from that path.

**MySQL:** set `MYSQL_PASSWORD` to the password for `MYSQL_USER` (error `using password: NO` means the password is empty in `.env` or `.env` is missing). Create the database with `database/schema.sql` first.

**SQLite (no MySQL):** in `backend/.env` set `DB_BACKEND=sqlite`. Tables are created automatically in `backend/medical_assistant.db`. If that file already exists from an older build and APIs fail with “no such table”, delete `medical_assistant.db` and restart so `create_all` can recreate tables.

Also set:

- `JWT_SECRET_KEY` (use a long random string)
- `OPENAI_API_KEY` (optional — if empty, the server uses safe **mock** responses)

Run the API + static UI:

```bash
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Open **`http://127.0.0.1:8000/`** (redirects to **`http://127.0.0.1:8000/app/`**).

### Running in VS Code

1. **Open the project folder** in VS Code: `File → Open Folder…` → choose **`ai-medical-assistant`** (the folder that contains `backend/` and `frontend/`), not only `backend/`.
2. Install the **Python** extension if prompted.
3. **Pick the interpreter** that has your dependencies: `Ctrl+Shift+P` → **Python: Select Interpreter** → choose the venv under `backend\.venv` (create the venv and `pip install -r backend/requirements.txt` first if you have not).
4. **Terminal (manual):** `Terminal → New Terminal`, then:
   ```powershell
   cd backend
   ..\.venv\Scripts\Activate.ps1   # if you use a venv
   uvicorn app:app --reload --host 127.0.0.1 --port 8000
   ```
5. **Run and Debug (F5):** open **Run and Debug** (`Ctrl+Shift+D`), choose **FastAPI: Uvicorn (backend)**, press **F5**. This uses `.vscode/launch.json` and sets `cwd` to `backend` automatically.

> The UI is served from `/app/` so API calls stay on the **same origin** (simpler CORS). You can still open `frontend/index.html` directly, but your browser may block requests unless CORS is widened further.

### 3) Register and use

1. On **Register**, **step 1:** enter your email and click **Send verification code**. **Step 2** unlocks after a code is generated. If **SMTP is not configured** (or sending fails), the API returns **`dev_otp`** in the JSON and the UI shows the code in a green box so you can still register. With SMTP configured, the code is only emailed. Optional: `SHOW_OTP_IN_DEV=true` also returns the code in JSON when email *was* sent (for debugging only).
2. Enter the **6-digit code**, name, and password, then **Create account**.
3. Sign in → **Dashboard** (chat, single-symptom checker with structured JSON, doctors, **appointments stored in MySQL**), **Diet plan** page, and Emergency (sample hospitals).

**Upgrading an existing database:** run `database/migration_v2.sql` once so `registration_otps`, `doctors`, and `appointments` exist (fresh installs already include these in `schema.sql`).

**MySQL ERROR 3780 on `fk_appt_doctor`:** `doctors.id` and `appointments.doctor_id` must match exactly (including `UNSIGNED`). If `doctors` was created earlier by the app as signed `INT`, run `database/fix_error_3780_doctor_fk.sql`, then create `appointments` again from `migration_v2.sql` if that table is missing. The ORM now uses **unsigned** types for `doctors.id` / `appointments.doctor_id` on MySQL so new `create_all` matches the SQL files.

## API map

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| POST | `/register/send-otp` | No | Email OTP for registration |
| POST | `/register` | No | Create user after OTP verification |
| POST | `/login` | No | JWT access token |
| GET | `/me` | Yes | Profile |
| PATCH | `/me` | Yes | Update profile |
| POST | `/chat` | Yes | AI reply + store `chat_history` |
| GET | `/chat/history` | Yes | Recent chat rows |
| POST | `/symptoms` | Yes | **One symptom** → structured JSON + `chat_history` |
| GET | `/doctors` | No | Doctor directory (seeded) |
| GET/POST | `/appointments` | Yes | List / book appointments |
| DELETE | `/appointments/{id}` | Yes | Cancel appointment |
| GET | `/diet-plan` | Yes | Diet sections (AI-enriched if OpenAI key set) |
| POST | `/health-data` | Yes | Add BMI/weight record |
| GET | `/health-data` | Yes | List records |
| GET | `/healthz` | No | Health probe |

## AI behavior

- **Chat:** If `OPENAI_API_KEY` is set, OpenAI is used with a safety-oriented prompt; otherwise **mock** text.
- **Symptom checker:** Returns **JSON** fields `condition`, `doctor_type`, `precautions[]`, `disclaimer`. With OpenAI, **`response_format: json_object`** is used; without a key, **rule-based mock** fills the same shape.
- **Diet plan:** Base template plus optional OpenAI JSON merge when a key is present.

## Project layout

```
ai-medical-assistant/
  backend/
    app.py
    config.py
    database.py
    deps.py
    security.py
    requirements.txt
    models/
    routes/
    services/
  frontend/
    index.html
    dashboard.html
    diet.html
    styles.css
    script.js
  database/
    schema.sql
    migration_v2.sql
```

## Notes

- `Base.metadata.create_all` in `app.py` helps local development; production deployments should use migrations (Alembic).
- This project is an **educational assistant**, not a regulated medical device.
=======
# ai-medical-assistant
AI Medical Assistant with symptom analysis, doctor recommendation, diet plan and appointment system
