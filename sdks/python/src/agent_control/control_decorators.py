"""
Control decorator for server-side protection of agent functions.

This module provides a decorator that applies server-defined policies to agent functions.
Policies contain multiple controls (regex, list, Luna2, etc.) that are managed server-side.

Architecture:
    SERVER defines: Policies -> Controls (stage, selector, evaluator, action)
    SDK decorator: just marks WHERE the policy applies

Usage:
    import agent_control

    agent_control.init(agent_name="my-agent", agent_id="agent-123")

    # Apply the agent's assigned policy
    @agent_control.control()
    async def chat(message: str) -> str:
        return await assistant.respond(message)

    # The server's policy contains controls that define:
    # - stage: "pre" or "post"
    # - selector.path: "input" or "output"
    # - evaluator: regex, list, Luna2 plugin, etc.
    # - action: deny, warn, or log
"""

import asyncio
import functools
import inspect
import logging
import os
from collections.abc import Callable
from typing import Any, TypeVar

from agent_control import AgentControlClient

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class ControlViolationError(Exception):
    """Raised when a control is triggered with 'deny' action."""

    def __init__(
        self,
        control_id: int | str | None = None,
        control_name: str | None = None,
        message: str = "Control violation",
        metadata: dict[str, Any] | None = None
    ):
        self.control_id = control_id
        self.control_name = control_name or (str(control_id) if control_id else "unknown")
        self.message = message
        self.metadata = metadata or {}
        super().__init__(f"Control violation [{self.control_name}]: {message}")


def _get_current_agent() -> Any | None:
    """Get the current agent from agent_control module."""
    try:
        import agent_control
        return agent_control.current_agent()
    except Exception:
        return None


def _get_server_url() -> str:
    """Get the server URL from environment or default."""
    return os.getenv("AGENT_CONTROL_URL", "http://localhost:8000")


async def _evaluate_async(
    agent_uuid: str,
    step: dict[str, Any],
    stage: str,
    server_url: str
) -> dict[str, Any]:
    """Call server evaluation endpoint asynchronously."""

    async with AgentControlClient(base_url=server_url) as client:
        response = await client.http_client.post(
            "/api/v1/evaluation",
            json={
                "agent_uuid": str(agent_uuid),
                "step": step,
                "stage": stage
            }
        )
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result


def _evaluate_sync(
    agent_uuid: str,
    step: dict[str, Any],
    stage: str,
    server_url: str
) -> dict[str, Any]:
    """Call server evaluation endpoint synchronously."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(
        _evaluate_async(agent_uuid, step, stage, server_url)
    )
    loop.close()
    return result


def _extract_input_from_args(func: Callable, args: tuple, kwargs: dict) -> str:
    """
    Extract input data from function arguments.

    Tries common parameter names, then falls back to first string argument.
    """
    sig = inspect.signature(func)
    bound = sig.bind(*args, **kwargs)
    bound.apply_defaults()

    # Common input parameter names (in order of preference)
    input_names = ["input", "message", "query", "text", "prompt", "content", "user_input"]

    for name in input_names:
        if name in bound.arguments:
            value = bound.arguments[name]
            if value is not None:
                return str(value)

    # Fall back to first string argument
    for param_name, value in bound.arguments.items():
        if isinstance(value, str):
            return value

    # Last resort: stringify all arguments
    return str(bound.arguments)


def _create_evaluation_payload(
    func: Callable,
    args: tuple,
    kwargs: dict,
    output: Any = None
) -> dict[str, Any]:
    """
    Create evaluation payload for server, detecting if it's a tool step or LLM step.

    Returns a Step payload structure.
    """
    sig = inspect.signature(func)
    bound = sig.bind(*args, **kwargs)
    bound.apply_defaults()

    # Check if this function is a tool (has tool_name attribute from @tool decorator)
    tool_name = getattr(func, "name", None) or getattr(func, "tool_name", None)

    if tool_name:
        # This is a tool step
        return {
            "type": "tool",
            "name": tool_name,
            "input": dict(bound.arguments),
            "output": output if isinstance(output, (str, int, float, bool, dict, list)) else (
                None if output is None else str(output)
            ),
        }

    # This is an LLM inference step
    input_data = _extract_input_from_args(func, args, kwargs)
    return {
        "type": "llm_inference",
        "name": func.__name__,
        "input": input_data,
        "output": output if isinstance(output, (str, int, float, bool, dict, list)) else (
            None if output is None else str(output)
        ),
    }


def _handle_evaluation_result(result: dict[str, Any]) -> None:
    """Handle evaluation result from server - raise on deny."""
    if not result:
        logger.warning("Received empty evaluation result from server")
        return

    is_safe = result.get("is_safe", True)
    matches = result.get("matches") or []  # Handle None case
    errors = result.get("errors") or []  # Handle server-side evaluation errors

    # CRITICAL: Check errors array FIRST - server-side failures must block execution
    if errors:
        error_messages = []
        for error in errors:
            if isinstance(error, dict):
                control_name = error.get("control_name", "unknown")
                error_msg = error.get("result", {}).get("message", "Unknown error")
                error_messages.append(f"[{control_name}] {error_msg}")

        raise RuntimeError(
            f"Control evaluation failed on server. Execution blocked for safety.\n"
            f"Errors: {'; '.join(error_messages)}"
        )

    if not is_safe:
        for match in matches:
            if not isinstance(match, dict):
                logger.warning(f"Invalid match format: {match}")
                continue

            action = match.get("action", "deny")
            control_id = match.get("control_id")
            matched_control = match.get("control_name", "unknown")

            # Safely extract result message and metadata
            result_data = match.get("result") or {}
            if isinstance(result_data, dict):
                message = result_data.get("message", "Control triggered")
                metadata = result_data.get("metadata", {})
            else:
                message = "Control triggered"
                metadata = {}

            if action == "deny":
                raise ControlViolationError(
                    control_id=control_id,
                    control_name=matched_control,
                    message=message,
                    metadata=metadata
                )
            elif action == "warn":
                logger.warning(f"⚠️ Control [{matched_control}]: {message}")
            elif action == "log":
                logger.info(f"ℹ️ Control [{matched_control}]: {message}")


def control(policy: str | None = None) -> Callable[[F], F]:
    """
    Decorator to apply server-defined policy at this code location.

    The policy's controls (stage, selector, evaluator, action) are defined
    on the SERVER. This decorator just marks WHERE to apply the policy.

    Args:
        policy: Optional policy name for documentation. The agent's assigned
                policy is automatically used. This parameter is for clarity
                in code when multiple policies exist.

    Returns:
        Decorated function

    Raises:
        ControlViolationError: If any control triggers with "deny" action

    How it works:
        1. Before function execution: Calls server with stage="pre"
           - Server evaluates all "pre" controls in the agent's policy
        2. Function executes
        3. After function execution: Calls server with stage="post"
           - Server evaluates all "post" controls in the agent's policy

    Example:
        import agent_control

        # Initialize agent (connects to server, loads policy)
        agent_control.init(agent_name="my-bot", agent_id="bot-123")

        # Apply the agent's policy (all controls)
        @agent_control.apply_control()
        async def chat(message: str) -> str:
            return await assistant.respond(message)

        # Document which policy this uses (optional, for clarity)
        @agent_control.apply_control(policy="safety-policy")
        async def process(input: str) -> str:
            return await pipeline.run(input)

    Server Setup (separate from agent code):
        1. Create controls via API:
           PUT /api/v1/controls {"name": "block-toxic-inputs"}
           PUT /api/v1/controls/{id}/data {"data": {...}}

        2. Create policy and add controls:
           PUT /api/v1/policies {"name": "safety-policy"}
           POST /api/v1/policies/{policy_id}/controls/{control_id}

        3. Assign policy to agent:
           POST /api/v1/agents/{agent_id}/policy/{policy_id}
    """
    # The policy parameter is for documentation only - the server uses
    # the agent's assigned policy automatically
    _ = policy

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            agent = _get_current_agent()
            if agent is None:
                logger.warning(
                    "No agent initialized. Call agent_control.init() first. "
                    "Running without protection."
                )
                return await func(*args, **kwargs)

            server_url = _get_server_url()
            agent_uuid = str(agent.agent_id)

            # PRE-EXECUTION: Check controls with stage="pre"
            try:
                step = _create_evaluation_payload(func, args, kwargs, output=None)
                result = await _evaluate_async(agent_uuid, step, "pre", server_url)
                _handle_evaluation_result(result)
            except ControlViolationError:
                raise
            except Exception as e:
                # FAIL-SAFE: If control check fails, DO NOT execute the function
                logger.error(f"Pre-execution control check failed: {e}")
                raise RuntimeError(
                    f"Control check failed unexpectedly. Execution blocked for safety. Error: {e}"
                ) from e

            # Execute the function
            output = await func(*args, **kwargs)

            # POST-EXECUTION: Check controls with stage="post"
            try:
                step = _create_evaluation_payload(func, args, kwargs, output=output)
                result = await _evaluate_async(agent_uuid, step, "post", server_url)
                _handle_evaluation_result(result)
            except ControlViolationError:
                raise
            except Exception as e:
                logger.error(f"Post-execution control check failed: {e}")

            return output

        # Copy over ALL attributes from the original function (important for LangChain tools)
        for attr in dir(func):
            if not attr.startswith('_') and attr not in ('__call__', '__wrapped__'):
                try:
                    setattr(async_wrapper, attr, getattr(func, attr))
                except (AttributeError, TypeError):
                    pass

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            agent = _get_current_agent()
            if agent is None:
                logger.warning(
                    "No agent initialized. Call agent_control.init() first. "
                    "Running without protection."
                )
                return func(*args, **kwargs)

            server_url = _get_server_url()
            agent_uuid = str(agent.agent_id)

            # PRE-EXECUTION
            try:
                step = _create_evaluation_payload(func, args, kwargs, output=None)
                result = _evaluate_sync(agent_uuid, step, "pre", server_url)
                _handle_evaluation_result(result)
            except ControlViolationError:
                raise
            except Exception as e:
                # FAIL-SAFE: If control check fails, DO NOT execute the function
                logger.error(f"Pre-execution control check failed: {e}")
                raise RuntimeError(
                    f"Control check failed unexpectedly. Execution blocked for safety. Error: {e}"
                ) from e

            # Execute
            output = func(*args, **kwargs)

            # POST-EXECUTION
            try:
                step = _create_evaluation_payload(func, args, kwargs, output=output)
                result = _evaluate_sync(agent_uuid, step, "post", server_url)
                _handle_evaluation_result(result)
            except ControlViolationError:
                raise
            except Exception as e:
                logger.error(f"Post-execution control check failed: {e}")

            return output

        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "control",
    "ControlViolationError",
]
