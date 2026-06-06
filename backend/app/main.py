import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.api.v1.api import api_router
from app.db.session import engine, SessionLocal
from app.db.base_class import Base
from app.db.init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Ensure local uploads directory exists
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    # 2. Create tables if they do not exist
    Base.metadata.create_all(bind=engine)
    
    # 3. Seed database categories, subcategories, questions, and officers
    db = SessionLocal()
    try:
        init_db(db)
    except Exception as e:
        print(f"Error seeding database: {e}")
    finally:
        db.close()
        
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
