from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import connect_to_db, close_db_connection, get_database
from app.security import hash_password
from app.routes import auth, admin, groups, expenses, kitty, notifications
from app.routes.kitty import ensure_group_contributions


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_db()
    db = get_database()

    # Create optimized database indexes
    await db.users.create_index("email", unique=True)
    await db.groups.create_index("group_code", unique=True)
    await db.memberships.create_index([("group_id", 1), ("user_id", 1)], unique=True)
    await db.contributions.create_index([("group_id", 1), ("month_index", 1), ("user_id", 1)], unique=True)
    await db.contributions.create_index([("group_id", 1), ("utr_reference", 1)], sparse=True)
    await db.kitty_transactions.create_index([("group_id", 1), ("created_at", -1)])
    await db.expenses.create_index([("group_id", 1), ("expense_date", -1)])
    await db.settlements.create_index([("group_id", 1), ("status", 1)])
    await db.audit_logs.create_index([("timestamp", -1)])
    await db.notifications.create_index([("recipient_user_id", 1), ("created_at", -1)])

    # Bootstrap the 4 official EDITH crew members and group
    now = datetime.now(timezone.utc)
    crew = [
        {"name": "Prajwal", "email": "prajwal@edith.travel", "role": "admin", "password": "Prajwal784"},
        {"name": "Parichay", "email": "parichay@edith.travel", "role": "member", "password": "Parichay392"},
        {"name": "Srujan", "email": "srujan@edith.travel", "role": "member", "password": "Srujan516"},
        {"name": "Nitish", "email": "nitish@edith.travel", "role": "member", "password": "Nitish628"},
    ]

    user_map = {}
    for member in crew:
        user = await db.users.find_one({"email": member["email"]})
        if not user:
            res = await db.users.insert_one({
                "name": member["name"],
                "email": member["email"],
                "phone": None,
                "password_hash": hash_password(member["password"]),
                "role": member["role"],
                "is_active": True,
                "created_at": now,
                "must_change_password": False,
            })
            user = await db.users.find_one({"_id": res.inserted_id})
        user_map[member["name"]] = user

    # Ensure group EDITH-TRIP-01 exists
    group = await db.groups.find_one({"group_code": "EDITH-TRIP-01"})
    if not group:
        prajwal_user = user_map.get("Prajwal")
        prajwal_id = str(prajwal_user["_id"]) if prajwal_user else "admin"
        res = await db.groups.insert_one({
            "name": "EDITH Annual Trip",
            "group_code": "EDITH-TRIP-01",
            "monthly_contribution": 2000,
            "duration_months": 12,
            "start_date": now,
            "custody_holder_name": "Prajwal",
            "currency": "INR",
            "created_by": prajwal_id,
            "trip_destination": "Manali & Spiti Valley",
            "trip_start_date": "2027-04-15",
            "trip_end_date": "2027-04-25",
            "planned_trip_budget": 96000,
            "trip_notes": "Official 4-member road trip through Himachal & Ladakh.",
            "trip_stops": [
                {"stop_number": 1, "destination_name": "Delhi", "arrival_date": "2027-04-15", "nights": 1, "transit_mode": "flight"},
                {"stop_number": 2, "destination_name": "Manali", "arrival_date": "2027-04-16", "nights": 3, "transit_mode": "van"},
                {"stop_number": 3, "destination_name": "Kaza / Spiti", "arrival_date": "2027-04-19", "nights": 4, "transit_mode": "suv"},
                {"stop_number": 4, "destination_name": "Shimla", "arrival_date": "2027-04-23", "nights": 2, "transit_mode": "suv"}
            ],
            "trip_title": "EDITH Northern Expedition",
            "is_active": True,
            "created_at": now,
        })
        group = await db.groups.find_one({"_id": res.inserted_id})

    # Link all 4 members to EDITH-TRIP-01
    group_id_str = str(group["_id"])
    for name, user in user_map.items():
        uid_str = str(user["_id"])
        membership = await db.memberships.find_one({"group_id": group_id_str, "user_id": uid_str})
        if not membership:
            await db.memberships.insert_one({
                "group_id": group_id_str,
                "user_id": uid_str,
                "role": user.get("role", "member"),
                "joined_at": now,
                "is_active": True,
            })

    # Ensure 12-month savings kitty schedules exist for all 4 members
    await ensure_group_contributions(db, group)

    yield
    await close_db_connection()


app = FastAPI(
    title=settings.app_name,
    version="2.0.0",
    description="Private group trip savings, multi-destination itinerary, and expense ledger.",
    lifespan=lifespan,
)

# Cloudflare Zero Trust / Access Middleware
@app.middleware("http")
async def cloudflare_access_middleware(request: Request, call_next):
    if settings.cloudflare_access_enabled:
        path = request.url.path
        # Exclude public probes and health checks
        if not path.startswith(("/health", "/docs", "/openapi.json", "/redoc", "/css", "/js")):
            cf_email = request.headers.get("Cf-Access-Authenticated-User-Email")
            if not cf_email:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Cloudflare Access verification required"},
                )
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(admin.router, prefix=settings.api_prefix)
app.include_router(groups.router, prefix=settings.api_prefix)
app.include_router(kitty.router, prefix=settings.api_prefix)
app.include_router(expenses.router, prefix=settings.api_prefix)
app.include_router(notifications.router, prefix=settings.api_prefix)

# Serve static frontend files directly from FastAPI for single-service cloud deployments
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    css_dir = frontend_dir / "css"
    js_dir = frontend_dir / "js"
    if css_dir.exists():
        app.mount("/css", StaticFiles(directory=str(css_dir)), name="css")
    if js_dir.exists():
        app.mount("/js", StaticFiles(directory=str(js_dir)), name="js")

    @app.get("/", include_in_schema=False)
    async def serve_index():
        return FileResponse(str(frontend_dir / "index.html"))


@app.get("/health")
@app.get("/api/v1/health")
async def health():
    return {
        "status": "healthy",
        "service": settings.app_name,
        "database": "supabase_postgresql" if get_database().is_supabase else "local_sqlite",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/v1/info")
async def info():
    return {
        "application": settings.app_name,
        "version": "2.0.0",
        "database": "Supabase PostgreSQL" if get_database().is_supabase else "Local SQLite (data/edith.db)",
        "docs": "/docs",
    }
