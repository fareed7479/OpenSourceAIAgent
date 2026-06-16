import logging
from sqlalchemy import inspect, text
from app.core.database import engine, Base
# Import all models to ensure they are registered with Base.metadata
from app.models import User, Repository, Issue, Assignment, AgentRun, AgentLog, PullRequest, Setting, ProviderConfig

logger = logging.getLogger(__name__)

def run_migrations() -> None:
    """Run lightweight migrations to ensure all columns exist on the issues and assignments tables."""
    try:
        inspector = inspect(engine)
        
        # 1. Migrate issues table if it exists
        if inspector.has_table("issues"):
            columns = [col["name"] for col in inspector.get_columns("issues")]
            with engine.connect() as conn:
                if "author_username" not in columns:
                    logger.info("Migration: Adding column author_username to issues table...")
                    conn.execute(text("ALTER TABLE issues ADD COLUMN author_username VARCHAR;"))
                    conn.commit()
                if "github_created_at" not in columns:
                    logger.info("Migration: Adding column github_created_at to issues table...")
                    conn.execute(text("ALTER TABLE issues ADD COLUMN github_created_at DATETIME;"))
                    conn.commit()
                if "github_updated_at" not in columns:
                    logger.info("Migration: Adding column github_updated_at to issues table...")
                    conn.execute(text("ALTER TABLE issues ADD COLUMN github_updated_at DATETIME;"))
                    conn.commit()
                if "comments_count" not in columns:
                    logger.info("Migration: Adding column comments_count to issues table...")
                    conn.execute(text("ALTER TABLE issues ADD COLUMN comments_count INTEGER DEFAULT 0;"))
                    conn.commit()
                if "meta_info" not in columns:
                    logger.info("Migration: Adding column meta_info to issues table...")
                    conn.execute(text("ALTER TABLE issues ADD COLUMN meta_info JSON;"))
                    conn.commit()
                if "source_owner" not in columns:
                    logger.info("Migration: Adding column source_owner to issues table...")
                    conn.execute(text("ALTER TABLE issues ADD COLUMN source_owner VARCHAR;"))
                    conn.commit()
                if "source_repo" not in columns:
                    logger.info("Migration: Adding column source_repo to issues table...")
                    conn.execute(text("ALTER TABLE issues ADD COLUMN source_repo VARCHAR;"))
                    conn.commit()
        else:
            logger.info("Issues table does not exist yet. Skipping issues migrations.")

        # 2. Migrate assignments table if it exists
        if inspector.has_table("assignments"):
            columns = [col["name"] for col in inspector.get_columns("assignments")]
            with engine.connect() as conn:
                if "comment_url" not in columns:
                    logger.info("Migration: Adding column comment_url to assignments table...")
                    conn.execute(text("ALTER TABLE assignments ADD COLUMN comment_url VARCHAR;"))
                    conn.commit()
                if "issue_url" not in columns:
                    logger.info("Migration: Adding column issue_url to assignments table...")
                    conn.execute(text("ALTER TABLE assignments ADD COLUMN issue_url VARCHAR;"))
                    conn.commit()
                if "repository_url" not in columns:
                    logger.info("Migration: Adding column repository_url to assignments table...")
                    conn.execute(text("ALTER TABLE assignments ADD COLUMN repository_url VARCHAR;"))
                    conn.commit()
        else:
            logger.info("Assignments table does not exist yet. Skipping assignments migrations.")

        # 3. Migrate agent_runs table if it exists
        if inspector.has_table("agent_runs"):
            columns = [col["name"] for col in inspector.get_columns("agent_runs")]
            with engine.connect() as conn:
                if "actual_provider" not in columns:
                    logger.info("Migration: Adding column actual_provider to agent_runs table...")
                    conn.execute(text("ALTER TABLE agent_runs ADD COLUMN actual_provider VARCHAR;"))
                    conn.commit()
                if "fallback_provider" not in columns:
                    logger.info("Migration: Adding column fallback_provider to agent_runs table...")
                    conn.execute(text("ALTER TABLE agent_runs ADD COLUMN fallback_provider VARCHAR;"))
                    conn.commit()
                if "fallback_reason" not in columns:
                    logger.info("Migration: Adding column fallback_reason to agent_runs table...")
                    conn.execute(text("ALTER TABLE agent_runs ADD COLUMN fallback_reason VARCHAR;"))
                    conn.commit()
        else:
            logger.info("Agent runs table does not exist yet. Skipping agent_runs migrations.")

        logger.info("Database migrations check complete.")
    except Exception as e:
        logger.error(f"Error running database migrations: {e}")

def init_db() -> None:
    """Initialize database tables."""
    try:
        logger.info("Initializing database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully. Running migrations...")
        run_migrations()
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise e

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
