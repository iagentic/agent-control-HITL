from .base import BaseModel
from .controls import ControlDefinition


class Control(BaseModel):
    """A control with identity and configuration.

    Note: Only fully-configured controls (with valid ControlDefinition)
    are returned from API endpoints. Unconfigured controls are filtered out.
    """

    id: int
    name: str
    control: ControlDefinition


class Policy(BaseModel):
    """A policy with its associated controls.

    Policies define a collection of controls that can be assigned to agents.
    Controls are directly associated with policies (no intermediate layer).
    """

    id: int
    name: str
    controls: list[Control]
