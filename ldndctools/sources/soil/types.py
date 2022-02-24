from dataclasses import dataclass

__all__ = ["BaseAttribute", "FullAttribute"]


@dataclass
class BaseAttribute:
    name: str
    unit: str


@dataclass
class FullAttribute(BaseAttribute):
    long_name: str
    msd: int
