from dataclasses import dataclass
from enum import Enum


class PrincipalType(str, Enum):
    HUMAN = "human"
    MACHINE = "machine"


@dataclass(slots=True)
class Principal:
    principal_type: PrincipalType
    subject: str
    scopes: set[str]
    role: str | None = None
    actor_id: str | None = None

    def require_scopes(self, required: set[str]) -> None:
        missing = required - self.scopes
        if missing:
            raise PermissionError(f"missing required scopes: {sorted(missing)}")


def parse_scope_header(scope_header: str | None) -> set[str]:
    if not scope_header:
        return set()
    return {chunk.strip() for chunk in scope_header.split(",") if chunk.strip()}
