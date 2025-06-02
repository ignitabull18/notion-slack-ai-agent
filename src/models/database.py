"""
Database configuration and session management.
"""
import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from typing import Generator
import logging

from src.config import get_settings

logger = logging.getLogger(__name__)

# Create declarative base
Base = declarative_base()

# Database engine and session factory
engine = None
SessionLocal = None

def init_database():
    """Initialize database engine and session factory."""
    global engine, SessionLocal
    
    settings = get_settings()
    database_url = settings.database_url
    
    # Configure engine based on database type
    if database_url.startswith("sqlite"):
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=settings.debug
        )
    elif database_url.startswith("postgresql"):
        engine = create_engine(
            database_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            echo=settings.debug
        )
    else:
        raise ValueError(f"Unsupported database URL: {database_url}")
    
    # Create session factory
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    logger.info(f"Database initialized: {database_url}")

def create_tables():
    """Create all database tables."""
    global engine
    if engine is None:
        init_database()
    
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")

def get_db() -> Generator[Session, None, None]:
    """
    Dependency that provides a database session.
    
    Yields:
        Database session
    """
    if SessionLocal is None:
        init_database()
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_session() -> Session:
    """
    Get a database session (for non-FastAPI usage).
    
    Returns:
        Database session (remember to close it!)
    """
    if SessionLocal is None:
        init_database()
    
    return SessionLocal()

# Metadata for migrations
metadata = MetaData()

# Health check function
def check_database_health() -> bool:
    """
    Check if database is accessible.
    
    Returns:
        True if database is healthy, False otherwise
    """
    try:
        if engine is None:
            init_database()
        
        with engine.connect() as connection:
            connection.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
