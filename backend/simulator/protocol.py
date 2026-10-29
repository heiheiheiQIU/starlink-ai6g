"""Private deterministic stop-and-wait protocol; never a policy input."""
from dataclasses import dataclass, field

from pydantic import model_validator
from backend.contracts import ContractModel, NonNegativeFloat, PositiveFloat


def split_payload(payload_bytes: int) -> tuple[int, ...]:
    if isinstance(payload_bytes, bool) or not isinstance(payload_bytes, int) or payload_bytes <= 0:
        raise ValueError('payload_bytes must be a positive integer')
    full, tail = divmod(payload_bytes, 1024)
    return (1024,) * full + ((tail,) if tail else ())


class ProtocolConfig(ContractModel):
    data_propagation_s: NonNegativeFloat
    ack_propagation_s: NonNegativeFloat
    control_bps: PositiveFloat
    ack_rx_W: NonNegativeFloat


@dataclass
class Pending:
    time_s: float
    kind: str
    task_id: str
    block_id: int
    payload_bytes: int
    attempt: int
    ack_start_s: float = 0.0
    ack_end_s: float = 0.0
    ack_visible_end_s: float = 0.0
    valid_ack: bool = False
    rx_start_s: float = 0.0
    rx_visible_end_s: float = 0.0


@dataclass
class ProtocolState:
    pending: list[Pending] = field(default_factory=list)
    gateway: set[tuple[str, int]] = field(default_factory=set)
    confirmed: set[tuple[str, int]] = field(default_factory=set)
    attempts: dict[tuple[str, int], int] = field(default_factory=dict)
