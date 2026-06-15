import logging
from app.core.database import engine, Base
# Import all models to ensure they are registered with Base.metadata
from app.models import User, Repository, Issue, Assignment, AgentRun, AgentLog, PullRequest, Setting, ProviderConfig

logger = logging.getLogger(__name__)

def init_db() -> None:
    """Initialize database tables."""
    try:
        logger.info("Initializing database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise e

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
