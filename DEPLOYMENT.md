# 🚀 EDITH Trip Manager — Live Deployment & Cloud Hosting Guide

This guide walks you through taking **EDITH Trip Manager** live on the cloud with **Supabase PostgreSQL** and free cloud hosting so all 4 members can access it securely from any mobile phone or browser.

---

## 🏗️ Architecture Overview

| Component | Technology | Free Tier Provider |
| :--- | :--- | :--- |
| **Database** | PostgreSQL 15+ (ACID relational) | [Supabase](https://supabase.com) (500MB free database) |
| **Backend & Frontend** | FastAPI + Static HTML5/Vanilla JS | [Render.com](https://render.com) (Free Web Service) |
| **Alternative Hosts** | Docker Container | [Railway](https://railway.app) / [Koyeb](https://koyeb.com) / [Fly.io](https://fly.io) |
| **Zero Trust Security** | Private access protection | [Cloudflare Zero Trust](https://one.dash.cloudflare.com) |

---

## Part 1: Supabase Database Setup (3 Minutes)

### Step 1: Create a Supabase Project
1. Go to [https://supabase.com](https://supabase.com) and log in (or sign in with GitHub).
2. Click **New Project**.
3. Choose:
   - **Name:** `EDITH-Trip-Manager`
   - **Database Password:** Enter a secure password (e.g. `Ammapappais123` or your own strong password). *Note this down!*
   - **Region:** Choose the region closest to your group (e.g., `South Asia (Mumbai)` or `Southeast Asia (Singapore)`).
   - **Pricing Plan:** Free Tier ($0/month).
4. Click **Create new project** and wait ~90 seconds for initialization.

### Step 2: Run the Schema Migration
1. In your Supabase project dashboard, click on the **SQL Editor** tab (left sidebar icon with `>_`).
2. Click **New query**.
3. Open the file `supabase_schema.sql` from this codebase, copy all contents, paste it into the Supabase SQL editor.
4. Click the green **Run** button.
5. You will see `Success. No rows returned`. All 9 relational tables (`users`, `groups`, `memberships`, `contributions`, `kitty_transactions`, `expenses`, `settlements`, `notifications`, `audit_logs`) and performance indexes are now active!

### Step 3: Get Your Connection String
1. Go to **Project Settings** (gear icon at the bottom left) ➔ **Database**.
2. Scroll to the **Connection string** section.
3. Select **URI** mode:
   - **Direct (port 5432):**
     ```text
     postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
     ```
   - **Transaction Pooler (port 6543, recommended for cloud apps & IPv4 networks):**
     ```text
     postgresql://postgres.[PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
     ```
4. Replace `[YOUR-PASSWORD]` with your actual Supabase database password.
5. In your `.env` file, set:
   ```env
   SUPABASE_DB_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
   ```

---

## Part 2: Hosting the Application Live (Render.com — Recommended)

Render hosts Python web apps on a free tier with automatic SSL (`https://`), auto-git deploys, and zero maintenance.
Since the FastAPI backend directly serves the mobile-optimized frontend from `/`, **a single Render service hosts the entire app**!

### Step 1: Connect your GitHub Repo
1. Go to [https://render.com](https://render.com) and log in with your GitHub account.
2. Click **New +** (top right) ➔ **Web Service**.
3. Under *Connect a repository*, choose `EDITH-Trip-Manager` (`https://github.com/EDITH-KRP/EDITH-Trip-Manager.git`).

### Step 2: Configure the Service
Fill out the fields as follows:
- **Name:** `edith-trip-manager` (your URL will be `https://edith-trip-manager.onrender.com`)
- **Region:** Singapore or Frankfurt (closest to your users)
- **Branch:** `main`
- **Runtime:** `Python 3`
- **Build Command:**
  ```bash
  pip install -r requirements.txt
  ```
- **Start Command:**
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port $PORT
  ```
- **Instance Type:** `Free`

### Step 3: Add Environment Variables
Under the **Environment Variables** tab on Render, add:

| Key | Example Value | Description |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `production` | Production mode |
| `SECRET_KEY` | *(generate a random 64-char string)* | JWT signing secret |
| `SUPABASE_DB_URL` | `postgresql://postgres:...@db...supabase.co:5432/postgres` | Your Supabase connection URI |
| `ADMIN_NAME` | `EDITH Trip Admin` | Your administrator display name |
| `ADMIN_EMAIL` | `admin@example.com` | Administrator login email |
| `ADMIN_PASSWORD` | `SetAStrongPasswordHere!` | Initial admin login password |

### Step 4: Click Deploy!
1. Click **Create Web Service**.
2. Render will install dependencies, connect to Supabase, bootstrap your admin user, and launch the service.
3. Once live, open your public URL: `https://edith-trip-manager.onrender.com`!

---

## Part 3: Alternative Cloud Platforms

### Alternative A: Railway.app
1. Go to [https://railway.app](https://railway.app) and click **New Project** ➔ **Deploy from GitHub repo**.
2. Select `EDITH-Trip-Manager`.
3. Add environment variables under **Variables**:
   - `SUPABASE_DB_URL`
   - `SECRET_KEY`
   - `ADMIN_EMAIL`
   - `ADMIN_PASSWORD`
4. Click **Generate Domain** under Settings ➔ Networking to get your public HTTPS URL.

### Alternative B: Docker / Self-Hosted VPS (DigitalOcean / AWS / Hetzner)
On any Linux server with Docker and Docker Compose installed:
```bash
git clone https://github.com/EDITH-KRP/EDITH-Trip-Manager.git
cd EDITH-Trip-Manager
cp .env.example .env
# Edit .env with nano to set your SUPABASE_DB_URL and secrets
docker compose up -d --build
```
The application will be live on port `8000`. Put Nginx or Caddy in front with Let's Encrypt SSL.

---

## Part 4: Privacy & Zero-Trust Access (Optional)

To ensure **only your 4 crew members** can even see the login screen:
1. Set up a free **Cloudflare Zero Trust** team at [https://one.dash.cloudflare.com](https://one.dash.cloudflare.com).
2. Add an Application pointing to your domain (e.g. `trip.yourdomain.com` or CNAME to Render).
3. Add an Access Policy allowing only the 4 member email addresses via One-Time PIN (OTP).
4. In your `.env`:
   ```env
   CLOUDFLARE_ACCESS_ENABLED=true
   CLOUDFLARE_ACCESS_TEAM=your-team-slug
   ```
This blocks all internet crawlers and unauthorized traffic at Cloudflare's edge before reaching your application.

---

## 📱 Mobile App Experience
Members can open the live HTTPS URL on Safari (iOS) or Chrome (Android) and tap:
- **iOS Safari:** Share button ➔ **Add to Home Screen**
- **Android Chrome:** Three dots menu ➔ **Install App / Add to Home screen**

The app behaves like a native progressive mobile app with bottom navigation, touch chips, and full-screen layout!

