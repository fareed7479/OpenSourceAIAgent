import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.init_db import init_db
from app.api import auth, repositories, issues, assignments, prs, settings as settings_api, runs, webhooks, intelligence

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize database tables on startup
try:
    init_db()
except Exception as e:
    logger.critical(f"Failed to initialize database: {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS middleware
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include API Routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(repositories.router, prefix=f"{settings.API_V1_STR}/repositories", tags=["repositories"])
app.include_router(issues.router, prefix=f"{settings.API_V1_STR}/issues", tags=["issues"])
app.include_router(assignments.router, prefix=f"{settings.API_V1_STR}/assignments", tags=["assignments"])
app.include_router(prs.router, prefix=f"{settings.API_V1_STR}/prs", tags=["prs"])
app.include_router(settings_api.router, prefix=f"{settings.API_V1_STR}/settings", tags=["settings"])
app.include_router(runs.router, prefix=f"{settings.API_V1_STR}/runs", tags=["runs"])
app.include_router(webhooks.router, prefix=f"{settings.API_V1_STR}/webhooks/github", tags=["webhooks"])
app.include_router(intelligence.router, prefix=f"{settings.API_V1_STR}/intelligence", tags=["intelligence"])

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "version": "1.0.0"
    }

# Reload trigger comment to force uvicorn reload on windows

