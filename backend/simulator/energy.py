"""Power in W, elapsed time in s, energy in Wh; retain evidence before clipping."""

from dataclasses import dataclass
import math

from backend.contracts import ContractModel, NonNegativeFloat


def finite_number(value, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    try:
        result = float(value)
    except (ValueError, OverflowError) as error:
        raise ValueError(f"{name} must be finite") from error
    if not math.isfinite(result) or (result <= 0 if positive else result < 0):
        raise ValueError(f"{name} must be {'positive' if positive else 'nonnegative'} and finite")
    return result


class PowerProfile(ContractModel):
    base_W: NonNegativeFloat = 0.0
    solar_W: NonNegativeFloat = 0.0
    compute_W: NonNegativeFloat = 0.0


@dataclass(frozen=True)
class EnergyLedgerEntry:
    duration_s: float
    energy_before_Wh: float
    solar_input_Wh: float
    background_Wh: float
    compute_Wh: float
    transmit_Wh: float
    energy_unclipped_Wh: float
    energy_after_Wh: float
    lower_violation: bool

    @property
    def consumed_Wh(self) -> float:
        return self.background_Wh + self.compute_Wh + self.transmit_Wh


def advance_energy(energy_Wh: float, capacity_Wh: float, duration_s: float,
                   powers: PowerProfile, tx_W: float = 0.0) -> EnergyLedgerEntry:
    energy = finite_number(energy_Wh, "energy_Wh")
    capacity = finite_number(capacity_Wh, "capacity_Wh", positive=True)
    duration = finite_number(duration_s, "duration_s", positive=True)
    transmit = finite_number(tx_W, "tx_W")
    profile = PowerProfile.model_validate(powers)
    if energy > capacity:
        raise ValueError("Initial energy exceeds capacity")
    solar, base, compute, tx = [power * duration / 3600.0 for power in
                                (profile.solar_W, profile.base_W, profile.compute_W, transmit)]
    raw = energy + solar - base - compute - tx
    if not all(math.isfinite(value) for value in (solar, base, compute, tx, raw)):
        raise ValueError("Energy arithmetic overflow")
    return EnergyLedgerEntry(duration, energy, solar, base, compute, tx, raw,
                             min(capacity, max(0.0, raw)), raw < 0.0)
