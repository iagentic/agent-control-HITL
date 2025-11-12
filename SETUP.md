# Setup Instructions

This document walks you through setting up the Agent Protect project for the first time.

## Step 1: Install UV

UV is a fast Python package manager. Install it with:

### macOS/Linux

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Windows

```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Alternative: Using pip

```bash
pip install uv
```

### Verify Installation

```bash
uv --version
```

You should see something like: `uv 0.x.x`

## Step 2: Install Project Dependencies

From the project root directory:

```bash
cd /path/to/agent-protect
uv sync
```

This command will:
1. Create a virtual environment
2. Install all workspace packages (`models`, `server`, `sdk`)
3. Install all dependencies
4. Link the packages together

You should see output like:

```
Resolved 25 packages in 1.2s
Downloaded 25 packages in 2.3s
Installed 25 packages in 0.5s
 + agent-protect-models==0.1.0 (from workspace)
 + agent-protect-sdk==0.1.0 (from workspace)
 + agent-protect-server==0.1.0 (from workspace)
 + fastapi==0.109.0
 + httpx==0.26.0
 + pydantic==2.5.0
 + ...
```

## Step 3: Verify Installation

Test that everything is installed correctly:

```bash
# Check if the server command is available
uv run agent-protect-server --help

# Try importing the SDK
uv run python -c "from agent_protect_sdk import AgentProtectClient; print('✓ SDK imported successfully')"

# Try importing the models
uv run python -c "from agent_protect_models import ProtectionRequest; print('✓ Models imported successfully')"
```

## Step 4: Run the Server

Start the server:

```bash
uv run agent-protect-server
```

Or for development with auto-reload:

```bash
cd server
uv run uvicorn agent_protect_server.main:app --reload
```

You should see:

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

## Step 5: Test the API

In a new terminal, test the API:

```bash
# Health check
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","version":"0.1.0"}

# Protection check
curl -X POST http://localhost:8000/protect \
  -H "Content-Type: application/json" \
  -d '{"content":"Hello, world!"}'

# Expected response:
# {"is_safe":true,"confidence":0.95,"reason":"Content appears safe"}
```

## Step 6: Test the SDK

Create a test file:

```python
# test_sdk.py
import asyncio
from agent_protect_sdk import AgentProtectClient

async def main():
    async with AgentProtectClient(base_url="http://localhost:8000") as client:
        # Health check
        health = await client.health_check()
        print(f"✓ Server health: {health}")
        
        # Protection check
        result = await client.check_protection("Hello, world!")
        print(f"✓ Protection result: {result}")
        
        # Use boolean check
        if result:
            print("✓ Content is safe")
        
        # Check confidence
        if result.is_confident(threshold=0.9):
            print(f"✓ High confidence: {result.confidence}")

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:

```bash
uv run python test_sdk.py
```

Expected output:

```
✓ Server health: {'status': 'healthy', 'version': '0.1.0'}
✓ Protection result: [SAFE] Confidence: 95% - Content appears safe
✓ Content is safe
✓ High confidence: 0.95
```

## Step 7: Run the Examples

Try the included examples:

```bash
# Basic usage example
uv run python examples/basic_usage.py

# Batch processing example
uv run python examples/batch_processing.py

# Models usage example
uv run python examples/models_usage.py
```

## Project Structure Overview

After setup, your project structure should look like this:

```
agent-protect/
├── pyproject.toml          # Root workspace config
├── .gitignore
├── README.md               # Main documentation
├── QUICKSTART.md           # Quick start guide
├── SETUP.md                # This file
├── DEPLOYMENT.md           # Deployment guide
│
├── models/                 # Shared Pydantic models
│   ├── pyproject.toml
│   ├── README.md
│   └── src/
│       └── agent_protect_models/
│           ├── __init__.py
│           ├── base.py
│           ├── health.py
│           └── protection.py
│
├── server/                 # FastAPI server
│   ├── pyproject.toml
│   ├── README.md
│   └── src/
│       └── agent_protect_server/
│           ├── __init__.py
│           ├── main.py
│           └── config.py
│
├── sdk/                    # Python SDK
│   ├── pyproject.toml
│   ├── README.md
│   └── src/
│       └── agent_protect_sdk/
│           ├── __init__.py
│           └── client.py
│
└── examples/               # Usage examples
    ├── basic_usage.py
    ├── batch_processing.py
    └── models_usage.py
```

## Understanding the Architecture

### Three-Package Monorepo

This project uses a **monorepo** structure with three packages:

1. **models** (`agent-protect-models`):
   - Foundation package
   - Contains all Pydantic data models
   - Used by both server and SDK
   - Ensures type safety and consistency

2. **server** (`agent-protect-server`):
   - FastAPI application
   - Depends on `models`
   - Provides REST API endpoints
   - Can be deployed independently

3. **sdk** (`agent-protect-sdk`):
   - Python client library
   - Depends on `models`
   - Provides async Python API
   - Can be published to PyPI

### Dependency Flow

```
models (foundation)
  ↓
  ├─→ server (uses models for API)
  └─→ sdk (uses models for client)
```

### Workspace Dependencies

The `pyproject.toml` in the root defines the workspace:

```toml
[tool.uv.workspace]
members = ["models", "server", "sdk"]
```

Each package's `pyproject.toml` references the models package:

```toml
[tool.uv.sources]
agent-protect-models = { workspace = true }
```

This tells `uv` to use the local workspace version during development, but can be replaced with a PyPI version for deployment.

## Common Issues and Solutions

### Issue: `command not found: uv`

**Solution**: Install UV following Step 1 above, then restart your terminal.

### Issue: `ModuleNotFoundError: No module named 'agent_protect_models'`

**Solution**: Run `uv sync` from the project root to install all workspace packages.

### Issue: Server won't start

**Solution**: 
1. Check if port 8000 is already in use: `lsof -i :8000`
2. Kill the process: `kill -9 <PID>`
3. Or use a different port: `uv run uvicorn agent_protect_server.main:app --port 8001`

### Issue: SDK can't connect to server

**Solution**:
1. Make sure the server is running: `curl http://localhost:8000/health`
2. Check the base URL in your client code
3. Check firewall settings

### Issue: Import errors after changes

**Solution**: After modifying models, reinstall the workspace:

```bash
uv sync --force
```

## Development Workflow

### Making Changes

1. **Edit files** in the appropriate package
2. **Test locally**:
   ```bash
   uv run pytest
   ```
3. **Lint and format**:
   ```bash
   uv run ruff check .
   uv run ruff format .
   ```
4. **Type check**:
   ```bash
   uv run mypy models/src server/src sdk/src
   ```

### Adding a New Dependency

For a specific package:

```bash
# Add to server
cd server
uv add fastapi-users

# Add to SDK
cd sdk
uv add aiofiles

# Add to models
cd models
uv add pydantic-extra-types
```

For dev dependencies (testing, linting):

```bash
# From root
uv add --dev pytest-cov
```

### Running Tests

```bash
# All tests
uv run pytest

# With coverage
uv run pytest --cov=models --cov=server --cov=sdk

# Specific package
cd server && uv run pytest
```

## Next Steps

Now that you have everything set up:

1. ✅ Read [QUICKSTART.md](QUICKSTART.md) for quick usage examples
2. ✅ Explore [README.md](README.md) for comprehensive documentation
3. ✅ Check [DEPLOYMENT.md](DEPLOYMENT.md) for deployment options
4. ✅ Review package-specific READMEs:
   - [models/README.md](models/README.md)
   - [server/README.md](server/README.md)
   - [sdk/README.md](sdk/README.md)

## Getting Help

- 📖 Read the documentation in each package
- 🐛 Check GitHub Issues
- 💬 Join GitHub Discussions
- 📧 Contact the team

## Additional Resources

- **UV Documentation**: https://github.com/astral-sh/uv
- **FastAPI Documentation**: https://fastapi.tiangolo.com
- **Pydantic Documentation**: https://docs.pydantic.dev
- **HTTPX Documentation**: https://www.python-httpx.org

Happy coding! 🚀

