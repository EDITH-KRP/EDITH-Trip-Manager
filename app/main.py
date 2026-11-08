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

    # Bootstrap the first administrator once. Never overwrite an existing account.
    admin_email = settings.admin_email.lower()
    existing_admin = await db.users.find_one({"email": admin_email})
    if not existing_admin:
        await db.users.insert_one({
            "name": settings.admin_name,
            "email": admin_email,
            "phone": None,
            "password_hash": hash_password(settings.admin_password),
            "role": "admin",
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "must_change_password": True,
        })

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
