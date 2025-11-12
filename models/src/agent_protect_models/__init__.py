"""Agent Protect Models - Shared data models for server and SDK."""

__version__ = "0.1.0"

from .health import HealthResponse
from .protection import ProtectionRequest, ProtectionResponse, ProtectionResult

__all__ = [
    "HealthResponse",
    "ProtectionRequest",
    "ProtectionResponse",
    "ProtectionResult",
]

