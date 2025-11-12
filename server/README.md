# Agent Protect Server

Server component for Agent Protect - provides agent protection services via REST API.

## Features

- FastAPI-based REST API
- Health check endpoint
- Content protection analysis endpoint
- Configurable via environment variables
- Async/await support

## Installation

### For Development (within monorepo)

```bash
# From the root directory
uv sync

# Run the server
cd server
uv run python -m agent_protect_server.main
```

### For Production Deployment

```bash
# Build the package
cd server
uv build

# Install the built package
uv pip install dist/agent_protect_server-0.1.0-py3-none-any.whl

# Run the server
agent-protect-server
```

## Configuration

Create a `.env` file in the server directory:

```env
HOST=0.0.0.0
PORT=8000
DEBUG=false
API_VERSION=v1
API_PREFIX=/api
```

## API Endpoints

### Health Check

```bash
GET /health
```

Response:
```json
{
  "status": "healthy",
  "version": "0.1.0"
}
```

### Protection Check

```bash
POST /protect
Content-Type: application/json

{
  "content": "Text to analyze",
  "context": {
    "source": "user_input"
  }
}
```

Response:
```json
{
  "is_safe": true,
  "confidence": 0.95,
  "reason": "Content appears safe"
}
```

## Development

### Running Tests

```bash
cd server
uv run pytest
```

### Type Checking

```bash
cd server
uv run mypy src/
```

### Linting

```bash
cd server
uv run ruff check src/
```

## Deployment

See [DEPLOYMENT.md](../DEPLOYMENT.md) for detailed deployment instructions.

