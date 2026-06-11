import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.core.config import settings
from app.api.v1.api import api_router
from app.db.session import engine, SessionLocal
from app.db.base import Base
from app.db.init_db import init_db


def validate_postgres_connection() -> bool:
    """Check PostgreSQL is reachable before proceeding."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.close()
        print("[STARTUP] PostgreSQL connection verified successfully.")
        return True
    except Exception as e:
        print(f"[STARTUP] ERROR: Cannot connect to PostgreSQL at: {settings.DATABASE_URL}")
        print(f"[STARTUP] Details: {e}")
        print("[STARTUP] Please ensure PostgreSQL is running and the 'ccrms' database exists.")
        print("[STARTUP] Run 'psql -U postgres -f setup_database.sql' to create the database.")
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Validate PostgreSQL connection
    if not validate_postgres_connection():
        print("[STARTUP] FATAL: Exiting due to database connection failure.")
        sys.exit(1)

    # 2. Create tables if they do not exist
    Base.metadata.create_all(bind=engine)
    print("[STARTUP] Database tables synchronized.")

    # 4. Seed database categories, subcategories, questions, and officers
    db = SessionLocal()
    try:
        init_db(db)
        print("[STARTUP] Database seeded with NCRP categories and default accounts.")
    except Exception as e:
        print(f"[STARTUP] Warning: Seeding error (may already be seeded): {e}")
    finally:
        db.close()

    print("[STARTUP] CCRMS Backend is ready!")
    print(f"[STARTUP] API Docs: http://localhost:8000/docs")
    print(f"[STARTUP] Admin Login: admin@ccrms.gov.in / adminpassword")
    print(f"[STARTUP] Officer Login: officer@ccrms.gov.in / officerpassword")

    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Ensure uploads directory exists before mounting (StaticFiles validates at construction)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Serve static uploads (for viewing evidence screenshots/PDFs)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Include central router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    return {
        "status": "online",
        "project": settings.PROJECT_NAME,
        "docs_url": "/docs"
    }
