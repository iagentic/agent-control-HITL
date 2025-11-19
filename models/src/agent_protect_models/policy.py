from .base import BaseModel


class Rule(BaseModel):
    id: int
    name: str
    rule: dict

class Control(BaseModel):
    id: int
    name: str
    rules: list[Rule]

class Policy(BaseModel):
    id: int
    name: str
    controls: list[Control]
