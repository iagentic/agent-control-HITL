from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agent_control_models.observability import ControlExecutionEvent, EventQueryRequest
from agent_control_server.observability.store.postgres import PostgresEventStore
from .conftest import async_engine, engine


@pytest.fixture(autouse=True)
def clear_event_table() -> None:
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM control_execution_events"))
    yield


def _event(
    *,
    agent_uuid,
    control_id: int,
    action: str,
    matched: bool,
    timestamp: datetime,
    trace_id: str,
) -> ControlExecutionEvent:
    return ControlExecutionEvent(
        trace_id=trace_id,
        span_id="b" * 16,
        agent_uuid=agent_uuid,
        agent_name="agent",
        control_id=control_id,
        control_name=f"control-{control_id}",
        check_stage="pre",
        applies_to="llm_call",
        action=action,
        matched=matched,
        confidence=0.8,
        timestamp=timestamp,
    )


@pytest.mark.asyncio
async def test_postgres_event_store_query_events_and_stats() -> None:
    # Given: a Postgres-backed store and a set of events
    session_maker = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    store = PostgresEventStore(session_maker)

    agent_uuid = uuid4()
    now = datetime.now(UTC)

    events = [
        _event(
            agent_uuid=agent_uuid,
            control_id=1,
            action="allow",
            matched=True,
            timestamp=now - timedelta(seconds=10),
            trace_id="a" * 32,
        ),
        _event(
            agent_uuid=agent_uuid,
            control_id=2,
            action="deny",
            matched=False,
            timestamp=now - timedelta(seconds=5),
            trace_id="b" * 32,
        ),
        _event(
            agent_uuid=agent_uuid,
            control_id=1,
            action="allow",
            matched=True,
            timestamp=now,
            trace_id="a" * 32,
        ),
    ]

    # When: storing events
    await store.store(events)

    # When: querying events filtered by control_id
    query = EventQueryRequest(agent_uuid=agent_uuid, control_ids=[1], limit=10, offset=0)
    resp = await store.query_events(query)
    # Then: only matching events are returned
    assert resp.total == 2
    assert all(e.control_id == 1 for e in resp.events)

    # When: querying events filtered by trace_id
    query = EventQueryRequest(trace_id="a" * 32, limit=10, offset=0)
    resp = await store.query_events(query)
    # Then: only matching events are returned
    assert resp.total == 2
    assert all(e.trace_id == "a" * 32 for e in resp.events)

    # When: querying stats
    stats = await store.query_stats(agent_uuid, timedelta(hours=1))
    # Then: totals and action counts are aggregated correctly
    assert stats.total_executions == 3
    assert stats.total_matches == 2
    assert stats.total_non_matches == 1
    assert stats.total_errors == 0
    assert stats.action_counts == {"allow": 2}
