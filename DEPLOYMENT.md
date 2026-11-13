# 🚀 EDITH Trip Manager — Live Production Deployment & Hosting Guide

This guide walks you through taking **EDITH Trip Manager** live to production with **Supabase PostgreSQL** and free cloud hosting so all 4 members can access it securely from any mobile phone or browser.

---

## 🏗️ Architecture Overview

| Component | Technology | Free Tier Provider |
| :--- | :--- | :--- |
| **Database** | PostgreSQL 15+ (ACID relational) | [Supabase](https://supabase.com) (500MB free managed Postgres) |
| **Backend & Frontend** | FastAPI + Monochrome HTML5/CSS3/Vanilla JS | [Render.com](https://render.com) (Free 750 hrs/month) or [Railway](https://railway.app) |
| **Alternative Hosts** | Docker Container | [Koyeb](https://koyeb.com) / [Fly.io](https://fly.io) / [Hetzner VPS](https://hetzner.com) |
| **Security** | Argon2id + JWT + Role Guard | Built-in (Admin vs Member RBAC) |

> **Single-Service Architecture:** FastAPI directly serves both the high-performance JSON API (`/api/v1/*`) and the static monochrome web application from the root `/`. You only deploy **one single service** — zero CORS issues, instant HTTPS, and single-click deploys.

---

## 👥 Production Crew Credentials

The production database is clean with zero dummy expenses, zero test disbursements, and zero fake settlements. The 4 official members and their login credentials are:

| Name | Role | Email Identifier | First Name Login | Password | Monthly Target |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Prajwal** | **Admin** | `prajwal@edith.travel` | `Prajwal` | `Prajwal784` | ₹2,000 / month |
| **Parichay** | **Member** | `parichay@edith.travel` | `Parichay` | `Parichay392` | ₹2,000 / month |
| **Srujan** | **Member** | `srujan@edith.travel` | `Srujan` | `Srujan516` | ₹2,000 / month |
| **Nitish** | **Member** | `nitish@edith.travel` | `Nitish` | `Nitish628` | ₹2,000 / month |

*(Members can log in by entering simply their first name `Prajwal` or full email `prajwal@edith.travel`)*.

---

## Part 1: Supabase Database Setup (3 Minutes)

### Step 1: Create a Supabase Project
1. Go to [https://supabase.com](https://supabase.com) and log in (or sign in with GitHub).
2. Click **New Project**.
3. Fill in:
   - **Name:** `EDITH-Trip-Manager`
   - **Database Password:** Set a strong password (e.g. `Ammapappais123`). *Save this password!*
   - **Region:** Choose `South Asia (Mumbai)` or `Southeast Asia (Singapore)` (closest to India).
   - **Pricing Plan:** Free Tier ($0/month).
4. Click **Create new project** and wait ~60 seconds for initialization.

### Step 2: Run the Schema Migration (Zero Dummy Data)
1. In your Supabase dashboard, click the **SQL Editor** tab (left sidebar icon with `>_`).
2. Click **New query**.
3. Open the file `supabase_schema.sql` from this codebase, copy all contents, paste it into the SQL editor.
4. Click the green **Run** button.
5. All 9 relational tables (`users`, `groups`, `memberships`, `contributions`, `kitty_transactions`, `expenses`, `settlements`, `notifications`, `audit_logs`) and the 4 crew members are initialized. **There are zero dummy expenses or test transactions.**

### Step 3: Get Your Supabase Connection String
1. Go to **Project Settings** (gear icon) ➔ **Database**.
2. Under **Connection string**, select **URI**:
   - **Direct (port 5432):**
     ```text
     postgresql://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
     ```
   - **Transaction Pooler (port 6543, recommended for IPv4 cloud hosts):**
     ```text
     postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
     ```
3. Copy this URI string for Step 2 below.

---

## Part 2: Host on Render.com (Recommended — 100% Free & Automatic)

Render is the simplest and best host for FastAPI. It provides automatic HTTPS (`https://*.onrender.com`), continuous deployment on every git push, and zero infrastructure maintenance.

### Method A: 1-Click Blueprint Deploy (Fastest)
1. Log in to [https://render.com](https://render.com) using your GitHub account.
2. Click **New +** (top right) ➔ **Blueprint**.
3. Connect your repository: `https://github.com/EDITH-KRP/EDITH-Trip-Manager.git`.
4. Render will read the `render.yaml` file in the repository automatically.
5. In the environment variables prompt, paste your `SUPABASE_DB_URL`.
6. Click **Apply**.
7. In ~2 minutes, your live site will be ready at:
   ```
   https://edith-trip-manager.onrender.com
   ```

### Method B: Manual Web Service Setup
1. On [Render.com](https://render.com), click **New +** ➔ **Web Service**.
2. Connect `https://github.com/EDITH-KRP/EDITH-Trip-Manager.git`.
3. Configure the service:
   - **Name:** `edith-trip-manager`
   - **Region:** Singapore
   - **Branch:** `main`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2 --proxy-headers`
   - **Instance Type:** `Free`
4. Under **Environment Variables**, add:
   - `ENVIRONMENT`: `production`
   - `SECRET_KEY`: *(click generate or enter random 64-char string)*
   - `SUPABASE_DB_URL`: *(your Supabase PostgreSQL URI)*
   - `ADMIN_NAME`: `Prajwal`
   - `ADMIN_EMAIL`: `prajwal@edith.travel`
   - `ADMIN_PASSWORD`: `Prajwal784`
5. Click **Deploy Web Service**!

---

## Part 3: Host on Railway.app (Alternative)

Railway provides native Docker container hosting with ultra-fast builds:
1. Log in to [https://railway.app](https://railway.app) with GitHub.
2. Click **New Project** ➔ **Deploy from GitHub repo**.
3. Select `EDITH-KRP/EDITH-Trip-Manager`.
4. Under **Variables**, add:
   - `SUPABASE_DB_URL` = your Supabase connection URI
   - `SECRET_KEY` = random secret string
   - `ADMIN_EMAIL` = `prajwal@edith.travel`
   - `ADMIN_PASSWORD` = `Prajwal784`
5. Under **Settings** ➔ **Networking**, click **Generate Domain**.
6. Railway assigns a public URL like `https://edith-trip-manager-production.up.railway.app`.

---

## Part 4: Self-Hosted Docker VPS (DigitalOcean / Hetzner / AWS Lightsail)

If you prefer hosting on your own Linux server or VPS ($4–$5/month):
```bash
# Clone the repository
git clone https://github.com/EDITH-KRP/EDITH-Trip-Manager.git
cd EDITH-Trip-Manager

# Clean any test data
python scripts/clean_production_data.py

# Create production environment file
cp .env.example .env
nano .env

# Build and start the production container in background
docker compose up -d --build
```
The app runs on port `8000`. You can configure Caddy or Nginx with Let's Encrypt for automatic HTTPS:
```caddy
trip.yourdomain.com {
    reverse_proxy localhost:8000
}
```

---

## 📱 Installing on Mobile Phones (Crew App Experience)

The frontend is fully mobile-optimized with a dark obsidian & graphite craft aesthetic, bottom navigation, and touch-friendly chips.

Once live, send the link to Parichay, Srujan, Nitish, and Prajwal:
* **iOS (Safari):** Open the link ➔ Tap **Share** icon (box with up arrow) ➔ Tap **Add to Home Screen**.
* **Android (Chrome):** Open the link ➔ Tap **Three dots** (top right) ➔ Tap **Install App** or **Add to Home screen**.

The app opens full-screen without URL bars, looking and behaving like a native iOS/Android application.
