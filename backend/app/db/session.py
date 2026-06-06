from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# For PostgreSQL, check and configure pool settings if needed
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # checks connection health before executing queries
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
