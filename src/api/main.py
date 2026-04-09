"""FastAPI application for MedWriter."""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from loguru import logger

from src.config.settings import Settings
from src.database import DatabaseManager
from src.pdf.store import DocumentStore
from src.redis import RedisManager, JobQueue
from src.api import dependencies


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI app.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting MedWriter API...")
    settings = Settings()

    # Initialize database
    logger.info(f"Connecting to database at {settings.database_url}")
    dependencies.db_manager = DatabaseManager(settings.database_url)
    await dependencies.db_manager.initialize_db()
    logger.info("Database initialized")

    # Initialize Redis
    logger.info(f"Connecting to Redis at {settings.redis_url}")
    dependencies.redis_manager = RedisManager(settings.redis_url)
    await dependencies.redis_manager.connect()
    dependencies.job_queue = JobQueue(dependencies.redis_manager.client)
    logger.info("Redis initialized")

    # Initialize DocumentStore for PDF chunks
    logger.info(f"Connecting to ChromaDB at {settings.chromadb_host}:{settings.chromadb_port}")
    dependencies.document_store = DocumentStore(
        host=settings.chromadb_host, port=settings.chromadb_port
    )
    logger.info("DocumentStore initialized")

    logger.info("MedWriter API started successfully")

    yield

    # Shutdown
    logger.info("Shutting down MedWriter API...")

    dependencies.document_store = None

    if dependencies.db_manager:
        await dependencies.db_manager.close()
        logger.info("Database connection closed")

    if dependencies.redis_manager:
        await dependencies.redis_manager.close()
        logger.info("Redis connection closed")

    logger.info("MedWriter API shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="MedWriter API",
    description="API for medical article writing assistant",
    version="0.2.0",
    lifespan=lifespan,
)

# Configure CORS
# Frontend is served from the same origin (API serves static files),
# so we only need to allow the API's own origin for browser requests.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8003",
        "http://127.0.0.1:8003",
        "http://api:8003",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "MedWriter API",
        "version": "0.2.0",
    }


# Import and include routers
from src.api.routes import conversations, messages

app.include_router(conversations.router, prefix="/api", tags=["conversations"])
app.include_router(messages.router, prefix="/api", tags=["messages"])

# Mount static files
UI_DIR = Path(__file__).parent.parent / "ui"
app.mount("/static", StaticFiles(directory=str(UI_DIR / "static")), name="static")


# Serve HTML pages
@app.get("/")
async def root():
    """Serve welcome page."""
    return FileResponse(str(UI_DIR / "index.html"))


@app.get("/index.html")
async def index():
    """Serve welcome page."""
    return FileResponse(str(UI_DIR / "index.html"))


@app.get("/conversations.html")
async def conversations_page():
    """Serve conversations list page."""
    return FileResponse(str(UI_DIR / "conversations.html"))


@app.get("/chat.html")
async def chat_page():
    """Serve chat interface page."""
    return FileResponse(str(UI_DIR / "chat.html"))
