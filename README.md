# ✈️ EDITH-TRIP MANAGER — Private Group Edition

A private cloud-hosted trip savings kitty, multi-destination itinerary planner, and shared expense manager designed specifically for **four friends total, including the administrator**.

Powered by **FastAPI**, **Supabase PostgreSQL** (with zero-config SQLite local fallback), and a **mobile-optimized responsive frontend**.

---

## 🌟 Core Features

- **Supabase PostgreSQL Database**: Cloud relational ledger with strict foreign keys, integer paise arithmetic, and immutable audit trails.
- **Mobile-Optimized UX**:
  - Touch-friendly participant selection chips (`[✓ You] [✓ Member]`) replacing clumsy select boxes.
  - Native-style bottom navigation bar with 44px+ touch targets and iOS safe area padding.
  - Slide-up bottom sheet drawers for all action forms.
  - `inputmode="numeric"` for mobile number keypads on currency & UTR inputs.
- **Privacy By Design**:
  - Personal monthly savings records remain private between the member and the administrator.
  - Group dashboard displays only the verified aggregate fund total and target pool.
- **Savings Kitty Engine**:
  - 12-month savings cycles (default ₹2,000/mo × 4 members = ₹96,000 target pool).
  - 12-digit UTR payment submission and administrator verification/rejection workflows.
  - Common kitty disbursements (stays, advance bookings) deducted directly from the pool.
  - Bank balance reconciliation with variance detection.
- **Splitwise-Style Kitty Split**:
  - Equal, custom amounts, and percentage splits.
  - Minimum Cash Flow debt simplification algorithm.
  - Two-phase settlement flow (debtor proposes ➔ creditor confirms).
- **Multi-Stop Itinerary Planner**: Up to 20 destinations with travel dates, transit modes, stays, and budget tracking.
- **Clean Starting State**: Zero mock or seed data. Bootstraps cleanly with your administrator account ready to invite your real crew.

---

## 🚀 Quick Start (Local Windows)

### Option 1: One-Click Launcher
Double-click **`run_all.bat`** in the project folder.
- Automatically connects to your local database (or Supabase if configured in `.env`).
- Automatically launches FastAPI on `http://127.0.0.1:8000`.
- Automatically launches the web frontend and opens your browser at **`http://127.0.0.1:5500`**.

### Option 2: Manual Terminal
```bash
# Install dependencies
pip install -r requirements.txt

# Start backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# In another terminal, start frontend
cd frontend
python -m http.server 5500
```

---

## 👥 Official Crew Member Accounts

On first launch, the system automatically bootstraps the 4 crew members and links them to the group (`EDITH-TRIP-01`):

| Name | Role | Username / Email | Password |
| :--- | :--- | :--- | :--- |
| **Prajwal** | **Administrator** | `Prajwal` or `prajwal@edith.travel` | `Prajwal784` |
| **Parichay** | Group Member | `Parichay` or `parichay@edith.travel` | `Parichay392` |
| **Srujan** | Group Member | `Srujan` or `srujan@edith.travel` | `Srujan516` |
| **Nitish** | Group Member | `Nitish` or `nitish@edith.travel` | `Nitish628` |

*(Note: Members can log in using either their simple first name or their full email address.)*

---

## 🌐 Supabase Database Setup

1. Create a free project at [https://supabase.com](https://supabase.com).
2. Open the **SQL Editor** in your Supabase dashboard and run the entire `supabase_schema.sql` file.
3. In **Project Settings ➔ Database ➔ Connection string**, copy your URI:
   ```env
   SUPABASE_DB_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
   ```
4. Paste it into your `.env` file. The backend automatically switches to your live Supabase cloud database!

*(Note: If `SUPABASE_DB_URL` is empty, the app runs locally on SQLite at `data/edith.db` with 100% functionality.)*

---

## ☁️ Live Cloud Hosting

You can host EDITH live on **Render.com** (recommended - 100% free single service):
1. Push to your GitHub repository: `https://github.com/EDITH-KRP/EDITH-Trip-Manager.git`.
2. Connect your repo to [Render.com](https://render.com) as a Web Service.
3. Build command: `pip install -r requirements.txt`.
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
5. Add your `SUPABASE_DB_URL` environment variable.

For full step-by-step instructions (including Railway, Docker, and Cloudflare Zero Trust), see [**`DEPLOYMENT.md`**](file:///DEPLOYMENT.md).

---

## 📂 Project Structure

```text
edith-trp/
├── app/
│   ├── routes/              # Modular API endpoints
│   │   ├── admin.py         # Member provisioning and audit trails
│   │   ├── auth.py          # JWT authentication and password changes
│   │   ├── expenses.py      # Kitty Split expenses & debt settlement
│   │   ├── groups.py        # Group management & itinerary routes
│   │   ├── kitty.py         # Savings contributions & disbursements
│   │   └── notifications.py # Notification dispatch & history
│   ├── services/            # Business logic
│   │   ├── audit.py         # Immutable audit ledger
│   │   └── notifications.py # SMS / DLT gateway delivery
│   ├── config.py            # Environment settings & credentials
│   ├── database.py          # Supabase PostgreSQL / SQLite adapter
│   ├── dependencies.py      # Auth guards & role validation
│   ├── main.py              # FastAPI app & static file server
│   ├── schemas.py           # Pydantic validation schemas
│   └── security.py          # Argon2 / bcrypt hashing & JWT tokens
├── frontend/                # Mobile-first web application
│   ├── css/style.css        # Responsive dark theme, bottom nav & sheets
│   ├── js/app.js            # Client-side state & participant chips
│   └── index.html           # Accessible HTML5 interface
├── data/                    # Local database storage (git-ignored)
├── edith_tests/             # Automated test suite
├── supabase_schema.sql      # Supabase PostgreSQL DDL
├── DEPLOYMENT.md            # Cloud deployment guide
├── requirements.txt         # Production dependencies
├── Dockerfile               # Multi-stage production container
├── docker-compose.yml       # Containerized stack
├── run_all.bat              # One-click Windows runner
├── start_backend.bat        # Backend runner
└── start_frontend.bat       # Frontend runner
```

---

## 📄 License & Confidentiality
Private, invite-only software intended for private group travel management.
GitHub: [https://github.com/EDITH-KRP/EDITH-Trip-Manager.git](https://github.com/EDITH-KRP/EDITH-Trip-Manager.git)
