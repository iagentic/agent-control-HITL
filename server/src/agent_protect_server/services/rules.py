from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from agent_protect_models.policy import Rule as APIRule
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Agent, Control, Policy, Rule, control_rules, policy_controls


async def list_rules_for_agent(agent_id: UUID, db: AsyncSession) -> list[APIRule]:
    """Return API Rule models for all rules associated with the agent's policy.

    Traversal: Agent -> Policy -> Controls -> Rules.
    Uses explicit joins over association tables to avoid async relationship loading.
    """
    stmt = (
        select(Rule)
        .join(control_rules, Rule.id == control_rules.c.rule_id)
        .join(Control, control_rules.c.control_id == Control.id)
        .join(policy_controls, Control.id == policy_controls.c.control_id)
        .join(Policy, policy_controls.c.policy_id == Policy.id)
        .join(Agent, Policy.id == Agent.policy_id)
        .where(Agent.agent_uuid == agent_id)
    )

    result = await db.execute(stmt)
    db_rules: Sequence[Rule] = result.scalars().unique().all()

    # Map DB Rule to API Rule with id, name, and data
    return [APIRule(id=r.id, name=r.name, rule=r.data) for r in db_rules]
