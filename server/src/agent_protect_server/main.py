"""Main server application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from agent_protect_models import HealthResponse
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .endpoints.agents import router as agent_router
from .endpoints.controls import router as control_router
from .endpoints.policies import router as policy_router
from .endpoints.protection import router as protection_router
from .endpoints.rules import router as rule_router
from .logging_utils import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for FastAPI app startup and shutdown."""
    # Startup: Configure logging
    log_level = "DEBUG" if settings.debug else "INFO"
    configure_logging(level=log_level)
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title="Agent Protect Server",
    description="""Server component for Agent Protect - policy-based protection for AI agents.

## Architecture

The system uses a hierarchical model:
- **Agents**: AI systems that need protection
- **Policies**: Collections of controls assigned to agents
- **Controls**: Groups of related rules
- **Rules**: Individual protection configurations

## Hierarchy

```
Agent → Policy → Control(s) → Rule(s)
```

## Quick Start

1. Register your agent with `/api/v1/agents/initAgent`
2. Create rules with `/api/v1/rules` and configure them
3. Create controls and add rules to them
4. Create a policy and add controls to it
5. Assign the policy to your agent
6. Query agent's active rules with `/api/v1/agents/{agent_id}/rules`
    """,
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API v1 prefix for all routes
api_v1_prefix = f"{settings.api_prefix}/{settings.api_version}"

app.include_router(agent_router, prefix=api_v1_prefix)
app.include_router(policy_router, prefix=api_v1_prefix)
app.include_router(control_router, prefix=api_v1_prefix)
app.include_router(rule_router, prefix=api_v1_prefix)
app.include_router(protection_router, prefix=api_v1_prefix)

# Health check at root level (common convention)
@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["system"],
    summary="Health check",
    response_description="Server health status",
)
async def health_check() -> HealthResponse:
    """
    Check if the server is running and responsive.

    This endpoint does not check database connectivity.

    Returns:
        HealthResponse with status and version
    """
    return HealthResponse(status="healthy", version="0.1.0")






def run() -> None:
    """Run the server application."""
    import uvicorn

    from .config import settings

    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level="debug" if settings.debug else "info",
    )


if __name__ == "__main__":
    run()
