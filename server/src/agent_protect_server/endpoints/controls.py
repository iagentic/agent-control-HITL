
from agent_protect_models.server import (
    AssocResponse,
    CreateControlRequest,
    CreateControlResponse,
    GetControlRulesResponse,
)
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_async_db
from ..logging_utils import get_logger
from ..models import Control, Rule, control_rules

router = APIRouter(prefix="/controls", tags=["controls"])

_logger = get_logger(__name__)


@router.put(
    "",
    response_model=CreateControlResponse,
    summary="Create a new control",
    response_description="Created control ID",
)
async def create_control(
    request: CreateControlRequest, db: AsyncSession = Depends(get_async_db)
) -> CreateControlResponse:
    """
    Create a new empty control with a unique name.

    Controls group related rules together and can be added to policies.
    A newly created control has no rules until they are explicitly added.

    Args:
        request: Control creation request with unique name
        db: Database session (injected)

    Returns:
        CreateControlResponse with the new control's ID

    Raises:
        HTTPException 409: Control with this name already exists
        HTTPException 500: Database error during creation
    """
    # Uniqueness check
    existing = await db.execute(select(Control.id).where(Control.name == request.name))
    if existing.first() is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Control with name '{request.name}' already exists",
        )

    control = Control(name=request.name)
    db.add(control)
    try:
        await db.commit()
        await db.refresh(control)
    except Exception:
        await db.rollback()
        _logger.error(
            f"Failed to create control '{request.name}'",
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create control '{request.name}': database error",
        )
    return CreateControlResponse(control_id=control.id)


@router.post(
    "/{control_id}/rules/{rule_id}",
    response_model=AssocResponse,
    summary="Add rule to control",
    response_description="Success confirmation",
)
async def add_rule_to_control(
    control_id: int, rule_id: int, db: AsyncSession = Depends(get_async_db)
) -> AssocResponse:
    """
    Associate a rule with a control.

    This operation is idempotent - adding the same rule multiple times has no effect.
    Agents with policies containing this control will immediately see the added rule.

    Args:
        control_id: ID of the control
        rule_id: ID of the rule to add
        db: Database session (injected)

    Returns:
        AssocResponse with success flag

    Raises:
        HTTPException 404: Control or rule not found
        HTTPException 500: Database error
    """
    ctl_res = await db.execute(select(Control).where(Control.id == control_id))
    control = ctl_res.scalars().first()
    if control is None:
        raise HTTPException(
            status_code=404, detail=f"Control with ID '{control_id}' not found"
        )

    rule_res = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = rule_res.scalars().first()
    if rule is None:
        raise HTTPException(
            status_code=404, detail=f"Rule with ID '{rule_id}' not found"
        )

    # Add association using INSERT ... ON CONFLICT DO NOTHING for idempotency
    try:
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        stmt = (
            pg_insert(control_rules)
            .values(control_id=control_id, rule_id=rule_id)
            .on_conflict_do_nothing()
        )
        await db.execute(stmt)
        await db.commit()
    except Exception:
        await db.rollback()
        _logger.error(
            (
                f"Failed to add rule '{rule.name}' ({rule_id}) "
                f"to control '{control.name}' ({control_id})"
            ),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to add rule '{rule.name}' to control '{control.name}': "
                "database error"
            ),
        )

    return AssocResponse(success=True)


@router.delete(
    "/{control_id}/rules/{rule_id}",
    response_model=AssocResponse,
    summary="Remove rule from control",
    response_description="Success confirmation",
)
async def remove_rule_from_control(
    control_id: int, rule_id: int, db: AsyncSession = Depends(get_async_db)
) -> AssocResponse:
    """
    Remove a rule from a control.

    This operation is idempotent - removing a non-associated rule has no effect.
    Agents with policies containing this control will immediately lose the removed rule.

    Args:
        control_id: ID of the control
        rule_id: ID of the rule to remove
        db: Database session (injected)

    Returns:
        AssocResponse with success flag

    Raises:
        HTTPException 404: Control or rule not found
        HTTPException 500: Database error
    """
    ctl_res = await db.execute(select(Control).where(Control.id == control_id))
    control = ctl_res.scalars().first()
    if control is None:
        raise HTTPException(
            status_code=404, detail=f"Control with ID '{control_id}' not found"
        )

    rule_res = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = rule_res.scalars().first()
    if rule is None:
        raise HTTPException(
            status_code=404, detail=f"Rule with ID '{rule_id}' not found"
        )

    # Remove association (idempotent - deleting non-existent is no-op)
    try:
        await db.execute(
            delete(control_rules).where(
                (control_rules.c.control_id == control_id)
                & (control_rules.c.rule_id == rule_id)
            )
        )
        await db.commit()
    except Exception:
        await db.rollback()
        _logger.error(
            (
                f"Failed to remove rule '{rule.name}' ({rule_id}) "
                f"from control '{control.name}' ({control_id})"
            ),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=(
                f"Failed to remove rule '{rule.name}' from control '{control.name}': "
                "database error"
            ),
        )

    return AssocResponse(success=True)


@router.get(
    "/{control_id}/rules",
    response_model=GetControlRulesResponse,
    summary="List control's rules",
    response_description="List of rule IDs",
)
async def list_control_rules(
    control_id: int, db: AsyncSession = Depends(get_async_db)
) -> GetControlRulesResponse:
    """
    List all rules associated with a control.

    Args:
        control_id: ID of the control
        db: Database session (injected)

    Returns:
        GetControlRulesResponse with list of rule IDs

    Raises:
        HTTPException 404: Control not found
    """
    ctl_res = await db.execute(select(Control.id).where(Control.id == control_id))
    if ctl_res.first() is None:
        raise HTTPException(
            status_code=404, detail=f"Control with ID '{control_id}' not found"
        )

    rows = await db.execute(
        select(control_rules.c.rule_id).where(control_rules.c.control_id == control_id)
    )
    rule_ids = [r[0] for r in rows.fetchall()]
    return GetControlRulesResponse(rule_ids=rule_ids)
