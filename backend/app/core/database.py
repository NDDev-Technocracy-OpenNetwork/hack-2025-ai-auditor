import logging
from collections.abc import AsyncGenerator, Generator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, SQLModel, create_engine, select

from app.core.config import settings

logger = logging.getLogger(__name__)

# Create synchronous engine for migrations and setup
sync_engine = create_engine(
    settings.database_url,
    echo=settings.is_development,  # Log SQL queries in development
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=300,  # Recycle connections every 5 minutes
)

# Create async engine for application use
async_database_url = settings.database_url.replace("postgresql+psycopg://", "postgresql+asyncpg://")
async_engine = create_async_engine(
    async_database_url,
    echo=settings.is_development,
    pool_pre_ping=True,
    pool_recycle=300,
)

# Create session factories
SessionLocal = sessionmaker(
    bind=sync_engine,
    class_=Session,
    expire_on_commit=False,
)

AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


def create_tables():
    """Create all database tables."""
    try:
        SQLModel.metadata.create_all(sync_engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


def get_session() -> Generator[Session, None, None]:
    """Dependency to get database session."""
    with SessionLocal() as session:
        try:
            yield session
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Async database session error: {e}")
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database with initial data if needed."""
    try:
        # Import models to register them
        from app.models.prompts import (  # noqa: F401 - model registration
            AnalysisResult,
            Prompt,
            PromptRelation,
        )

        # Create tables
        create_tables()

        # Add any initial data here if needed
        logger.info("Database initialized successfully")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


async def check_db_connection() -> bool:
    """Check if database connection is working."""
    try:
        async with AsyncSessionLocal() as session:
            # Simple query to test connection
            result = await session.execute(select(1))
            return result.scalar() == 1
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


# Database utilities
class DatabaseManager:
    """Database management utilities."""

    @staticmethod
    async def get_session_count() -> int:
        """Get current number of database sessions."""
        try:
            return async_engine.pool.size()
        except Exception:
            return 0

    @staticmethod
    async def health_check() -> dict:
        """Comprehensive database health check."""
        health_data = {
            "connected": False,
            "pool_size": 0,
            "pool_checked_in": 0,
            "pool_checked_out": 0,
            "pool_overflow": 0,
        }

        try:
            # Test connection
            health_data["connected"] = await check_db_connection()

            # Pool statistics
            pool = async_engine.pool
            health_data["pool_size"] = pool.size()
            health_data["pool_checked_in"] = pool.checkedin()
            health_data["pool_checked_out"] = pool.checkedout()
            health_data["pool_overflow"] = pool.overflow()

        except Exception as e:
            logger.error(f"Database health check failed: {e}")

        return health_data


# Global database manager instance
db_manager = DatabaseManager()
