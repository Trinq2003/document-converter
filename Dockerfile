# Multi-stage Dockerfile for Document Converter API
# Stage 1: Build stage
FROM python:3.11-slim as builder

# Build arguments
ARG BUILD_DATE
ARG GIT_COMMIT

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_CACHE_DIR=/opt/uv-cache \
    BUILD_DATE=${BUILD_DATE} \
    GIT_COMMIT=${GIT_COMMIT}

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Pandoc
RUN curl -L https://github.com/jgm/pandoc/releases/download/3.1.9/pandoc-3.1.9-1-amd64.deb -o pandoc.deb \
    && dpkg -i pandoc.deb \
    && rm pandoc.deb

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Create virtual environment and install dependencies
COPY pyproject.toml ./
# Copy LICENSE file for build
COPY LICENSE ./
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
# Copy lock file if it exists, otherwise generate it
COPY uv.lock* ./
# Install dependencies (including uvicorn for running the app)
RUN if [ -f uv.lock ]; then uv sync --frozen --no-dev; else uv sync --no-dev; fi

# Stage 2: Production stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    APP_NAME="Document Converter API" \
    APP_VERSION="1.0.0" \
    DEBUG=false \
    HOST=0.0.0.0 \
    PORT=8000 \
    BASE_DIR=/app/data \
    LOG_LEVEL=INFO \
    MAX_FILE_SIZE=52428800 \
    CLEANUP_TEMP_FILES=true \
    PRESERVE_IMAGES=true \
    PANDOC_TIMEOUT=300 \
    PANDOC_MATH_ENGINE=mathml \
    PANDOC_TOC_DEPTH=4

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Pandoc
RUN curl -L https://github.com/jgm/pandoc/releases/download/3.1.9/pandoc-3.1.9-1-amd64.deb -o pandoc.deb \
    && dpkg -i pandoc.deb \
    && rm pandoc.deb

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Add labels for metadata
LABEL org.opencontainers.image.title="Document Converter API"
LABEL org.opencontainers.image.description="Professional document conversion service that converts DOCX to Markdown"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.created="${BUILD_DATE}"
LABEL org.opencontainers.image.revision="${GIT_COMMIT}"
LABEL org.opencontainers.image.source="https://github.com/your-org/document-converter-api"
LABEL org.opencontainers.image.licenses="MIT"

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Create application directory
WORKDIR /app

# Copy application code
COPY app/ ./app/
COPY *.py ./

# Create data directories and set permissions
RUN mkdir -p /app/data/{docx,html,md,temp,logs} \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Default command
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
