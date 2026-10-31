import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base
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
    # Ensure all tables exist on startup
    Base.metadata.create_all(bind=engine)
    
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
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


@app.get("/", tags=["Health"])
def root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "docs": "/docs",
        "version": "1.0.0",
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy"}
