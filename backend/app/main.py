import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.scheduler.jobs import start_scheduler, shutdown_scheduler

from app.auth.router import router as auth_router
from app.taxes.router import router as taxes_router
from app.products.router import router as products_router
from app.plans.router import router as plans_router
from app.templates.router import router as templates_router
from app.subscriptions.router import router as subscriptions_router
from app.invoices.router import router as invoices_router
from app.payments.router import router as payments_router
from app.discounts.router import router as discounts_router
from app.dashboard.router import router as dashboard_router
from app.portal.router import router as portal_router
from app.export.router import router as export_router
from app.audit.router import router as audit_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure all database tables exist on startup
    Base.metadata.create_all(bind=engine)

    # Auto-seed basic seed records if database is completely empty
    try:
        from app.models import User
        from app.core.security import get_password_hash
        with SessionLocal() as db:
            if db.query(User).count() == 0:
                print("Database is empty. Auto-seeding core demo users...", flush=True)
                admin = User(
                    name="Global Administrator",
                    email="admin@brightloop.com",
                    hashed_password=get_password_hash("Admin@123!"),
                    role="admin",
                    is_active=True,
                )
                staff = User(
                    name="Operations Staff",
                    email="staff@brightloop.com",
                    hashed_password=get_password_hash("Staff@123!"),
                    role="staff",
                    is_active=True,
                )
                cust = User(
                    name="Acme Corporation",
                    email="customer@brightloop.com",
                    hashed_password=get_password_hash("Cust@1234!"),
                    role="customer",
                    is_active=True,
                )
                db.add_all([admin, staff, cust])
                db.commit()
                print("Core demo accounts provisioned: admin@brightloop.com, staff@brightloop.com, customer@brightloop.com", flush=True)
    except Exception as e:
        print(f"Auto-seed check note: {e}", flush=True)

    if not os.getenv("TESTING"):
        try:
            start_scheduler()
        except Exception:
            pass

    yield

    try:
        shutdown_scheduler()
    except Exception:
        pass


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Brightloop Software — Unified Platform for Subscriptions, Recurring Billing, Invoicing & Financial Analytics.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration supporting localhost, Vercel deployments (*.vercel.app), and production HTTPS domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_origin_regex=r"https://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

prefix = settings.API_V1_STR
app.include_router(auth_router, prefix=prefix)
app.include_router(taxes_router, prefix=prefix)
app.include_router(products_router, prefix=prefix)
app.include_router(plans_router, prefix=prefix)
app.include_router(templates_router, prefix=prefix)
app.include_router(subscriptions_router, prefix=prefix)
app.include_router(invoices_router, prefix=prefix)
app.include_router(payments_router, prefix=prefix)
app.include_router(discounts_router, prefix=prefix)
app.include_router(dashboard_router, prefix=prefix)
app.include_router(portal_router, prefix=prefix)
app.include_router(export_router, prefix=prefix)
app.include_router(audit_router, prefix=prefix)

frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
index_html = os.path.join(frontend_dir, "index.html")

@app.get("/", tags=["Root"])
def root_endpoint():
    if os.path.exists(index_html):
        return FileResponse(index_html)
    return {
        "service": settings.PROJECT_NAME,
        "status": "online",
        "docs": "/docs",
        "api": settings.API_V1_STR,
        "health": "/health",
    }

@app.get("/health", tags=["Health"])
@app.get("/api/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "docs": "/docs",
        "version": "1.0.0",
    }
