# Base image with Python
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster dependency management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv pip install --system -e . --no-build-isolation || uv pip install --system \
    llama-index \
    llama-index-llms-openai \
    llama-index-llms-anthropic \
    fastmcp \
    httpx \
    pydantic \
    pydantic-settings \
    python-dotenv \
    loguru \
    typer \
    rich \
    nest-asyncio \
    "sqlalchemy[asyncio]" \
    asyncpg \
    alembic \
    "redis[hiredis]" \
    fastapi \
    "uvicorn[standard]" \
    python-multipart \
    pymupdf \
    chromadb \
    llama-index-vector-stores-chroma \
    llama-index-embeddings-openai \
    llama-index-retrievers-bm25

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p logs

# Default command (override in docker-compose)
CMD ["python3", "-m", "src.worker"]
