# Document Converter API

A professional document conversion service that converts DOCX files to Markdown with support for tables, math equations, and images. Built with FastAPI and containerized with Docker.

## Features

- **DOCX to Markdown Conversion**: High-quality conversion preserving document structure
- **Table Preservation**: Maintains table formatting in HTML format within markdown
- **Math Equation Support**: Preserves mathematical expressions using MathML
- **Image Handling**: Extracts and properly references images with correct paths
- **Batch Processing**: Convert multiple documents simultaneously
- **RESTful API**: Clean, documented API endpoints
- **Docker Support**: Easy deployment with Docker and Docker Compose
- **Production Ready**: Includes logging, health checks, and error handling

## Quick Start

### Using Docker (Recommended)

1. **Clone and build:**
   ```bash
   git clone <repository-url>
   cd document-converter-api
   docker-compose up --build
   ```

2. **Access the API:**
   - API: http://localhost:8000
   - Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/api/v1/health

### Local Development

1. **Install uv (if not already installed):**
   ```bash
   # macOS and Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Windows
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   
   # Or via pip
   pip install uv
   ```

2. **Setup the project:**
   ```bash
   # Quick setup (generates lock file and installs dependencies)
   ./setup.sh        # Linux/macOS
   setup.bat         # Windows
   
   # Or manually:
   uv lock           # Generate lock file
   uv sync --no-install-project  # Install all dependencies (including dev)
   ```

3. **Alternative manual setup:**
   ```bash
   # Install all dependencies (including dev)
   uv sync --no-install-project
   
   # Or install only production dependencies
   uv sync --no-dev --no-install-project
   ```

4. **Install Pandoc:**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install pandoc
   
   # macOS
   brew install pandoc
   
   # Windows
   # Download from https://pandoc.org/installing.html
   ```

5. **Run the application:**
   ```bash
   # Using uv
   uv run uvicorn app.main:app --reload
   
   # Or using make
   make dev
   ```

## API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/health` | Health check |
| `GET` | `/api/v1/documents` | List available documents |
| `POST` | `/api/v1/upload` | Upload DOCX file |
| `POST` | `/api/v1/convert` | Convert single document |
| `POST` | `/api/v1/convert/batch` | Convert multiple documents |
| `GET` | `/api/v1/tasks/{task_id}` | Get async task status |
| `GET` | `/api/v1/download/{filename}` | Download converted file |
| `DELETE` | `/api/v1/documents/{filename}` | Delete document |

### Example Usage

#### Upload and Convert a Document

```bash
# Upload a document
curl -X POST "http://localhost:8000/api/v1/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.docx" 

# Convert the document
curl -X POST "http://localhost:8000/api/v1/convert" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "document.docx",
    "preserve_images": true,
    "include_toc": true,
    "math_engine": "mathml"
  }'
```

#### Batch Conversion

```bash
curl -X POST "http://localhost:8000/api/v1/convert/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "filenames": ["doc1.docx", "doc2.docx"],
    "preserve_images": true,
    "include_toc": true
  }'
```

## Configuration

The application can be configured using environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `false` | Enable debug mode |
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |
| `BASE_DIR` | `/app/data` | Base directory for files |
| `MAX_FILE_SIZE` | `52428800` | Maximum file size (50MB) |
| `LOG_LEVEL` | `INFO` | Logging level |
| `PANDOC_TIMEOUT` | `300` | Pandoc timeout in seconds |
| `CLEANUP_TEMP_FILES` | `true` | Clean up temporary files |

See `env.example` for all available configuration options.

## Project Structure

```
document-converter-api/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── config.py              # Configuration management
│   ├── models.py              # Pydantic models
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py          # API endpoints
│   │   └── dependencies.py    # FastAPI dependencies
│   └── core/
│       ├── __init__.py
│       ├── logger.py          # Logging configuration
│       ├── document_converter.py  # Main converter logic
│       ├── pandoc_converter.py    # Pandoc integration
│       └── html_processor.py      # HTML processing
├── data/                      # File storage (created automatically)
├── pyproject.toml            # Project configuration and dependencies
├── uv.lock                   # Locked dependency versions
├── Dockerfile                # Docker configuration
├── docker-compose.yml        # Docker Compose setup
├── nginx.conf                # Nginx configuration
├── Makefile                  # Development commands
└── README.md                 # This file
```

## Development

### Setup Development Environment

```bash
# Install development dependencies
uv sync --no-install-project

# Install pre-commit hooks
uv run pre-commit install

# Run tests
uv run pytest
# Or use make
make test

# Format code
make format

# Run linting
make lint

# Update lock file
uv lock
```

### Available Make Commands

```bash
make help          # Show all available commands
make dev           # Run development server
make test          # Run tests
make lint          # Run linting
make format        # Format code
make install       # Install production dependencies
make install-dev   # Install development dependencies
make sync          # Sync dependencies from lock file
make lock          # Update lock file
make docker-build  # Build Docker image with tags
make docker-run    # Run Docker container
make docker-images # List built Docker images
make docker-compose-up     # Start services with Docker Compose
make docker-compose-down   # Stop and remove services
make docker-compose-logs   # View logs from all services
make docker-dev           # Run development environment
make docker-prod          # Run production environment
make docker-clean         # Clean up Docker resources
make clean         # Clean up temporary files
```

## Development with Live Reloading

The development environment is configured with live code reloading, so any changes you make to the source code will automatically be applied to the running container without needing to rebuild.

### Development Setup

```bash
# Start development environment with live reloading
make docker-dev

# Or run in detached mode
make docker-dev-detached

# View logs
make docker-compose-logs

# Stop development environment
make docker-compose-down
```

### How Live Reloading Works

- The development container mounts your local `./app` directory into the container
- Uvicorn runs with the `--reload` flag, watching for file changes
- Any changes to Python files in the `app/` directory will trigger an automatic restart
- The container uses the `development` profile with `DEBUG=true` and `LOG_LEVEL=DEBUG`

### Testing Live Reloading

1. Start the development environment: `make docker-dev`
2. Make a change to any file in the `app/` directory
3. Watch the logs to see the automatic reload: `make docker-compose-logs`
4. Test the API: `python test_reload.py`

## Production Deployment

### Using Docker Compose

```bash
# Development environment
make docker-dev           # Start development environment with live reload
make docker-compose-logs  # View logs
make docker-compose-down  # Stop services

# Production environment
make docker-prod          # Start production with Nginx and Redis
make docker-prod-down     # Stop production environment

# General Docker Compose commands
make docker-compose-up     # Start services
make docker-compose-down   # Stop and remove services
make docker-compose-logs   # View logs from all services
make docker-compose-restart # Restart all services
make docker-compose-ps     # List running services
```

### Docker Image Tagging

The Docker build process automatically creates multiple tags:

- `document-converter-api:latest` - Latest version
- `document-converter-api:1.0.0` - Version tag
- `document-converter-api:<git-commit>` - Git commit hash tag

```bash
# Build with all tags
make docker-build

# List all built images
make docker-images

# Run specific version
docker run document-converter-api:1.0.0
```

### Using Kubernetes

The application is containerized and can be deployed to Kubernetes. Example manifests are available in the `k8s/` directory.

### Environment Variables for Production

```bash
DEBUG=false
LOG_LEVEL=INFO
BASE_DIR=/app/data
MAX_FILE_SIZE=52428800
PANDOC_TIMEOUT=300
CLEANUP_TEMP_FILES=true
```

## Monitoring and Logging

- **Health Checks**: Built-in health check endpoint
- **Structured Logging**: JSON-formatted logs with request tracking
- **Error Handling**: Comprehensive error handling with proper HTTP status codes
- **Metrics**: Request timing and conversion statistics

## Security Considerations

- File upload validation
- Size limits on uploads
- Non-root container execution
- Input sanitization
- Rate limiting (with Nginx)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run linting and tests
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
- Create an issue in the repository
- Check the API documentation at `/docs`
- Review the logs for debugging information

## Changelog

### v1.0.0
- Initial release
- DOCX to Markdown conversion
- Table and math equation preservation
- Image handling
- RESTful API
- Docker support
- Production-ready configuration
