"""Versioned synthetic axes compiler used exclusively by the interactive API."""
from typing import Literal

from pydantic import field_validator, model_validator

from backend.cli import RunConfig
from backend.contracts import ContractModel, NonNegativeFloat, NonNegativeInt


class SandboxAxes(ContractModel):
    task_count: Literal[2, 6, 10]
    deadline_s: Literal[8, 12, 18, 24]
    weights: Literal['equal', 'tiered', 'urgent']
    initial_energy_Wh: Literal[0.8, 1.2, 10.0]
    health: Literal['healthy', 'degraded', 'critical']
    reserve_Wh: NonNegativeFloat
    disturbance: Literal['none', 'mild', 'strong']
    rate: Literal['robust', 'fast']

    @field_validator('task_count', 'deadline_s', 'initial_energy_Wh', mode='before')
    @classmethod
    def numeric_choices(cls, value):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError('Expected a numeric axis choice')
        return value

    @model_validator(mode='after')
    def reserve_within_capacity(self):
        if self.reserve_Wh > 20:
            raise ValueError('reserve_Wh must be at most capacity 20 Wh')
        return self


class SandboxRequest(ContractModel):
    kind: Literal['sandbox_axes']
    compiler_version: Literal['sandbox-axis-v1']
    axes: SandboxAxes


GOLDEN_AXES = {
    'S1': dict(task_count=2, deadline_s=24, weights='equal', initial_energy_Wh=10.0,
               health='healthy', reserve_Wh=0.5, disturbance='none', rate='fast'),
    'S2': dict(task_count=6, deadline_s=8, weights='tiered', initial_energy_Wh=0.8,
               health='critical', reserve_Wh=0.5, disturbance='none', rate='robust'),
    'S3': dict(task_count=2, deadline_s=24, weights='tiered', initial_energy_Wh=10.0,
               health='healthy', reserve_Wh=0.5, disturbance='strong', rate='robust'),
}


def compile_sandbox_axes(axes, seed) -> dict:
    """Return a complete validated RunConfig, with no browser-built scenario."""
    from pydantic import TypeAdapter
    seed = TypeAdapter(NonNegativeInt).validate_python(seed, strict=True)
    axis = SandboxAxes.model_validate(axes)
    weights = {'equal': (1, 1, 1), 'tiered': (1, 3, 6), 'urgent': (6, 1, 1)}[axis.weights]
    tasks = []
    for index in range(axis.task_count):
        arrival = float(index % 3)
        payload = 3072 if index == 0 else 1024
        tasks.append(dict(task_id=f'T{index+1}', arrival_s=arrival,
                          deadline_s=arrival+axis.deadline_s, payload_bytes=payload,
                          remaining_bytes=payload, priority_weight=float(weights[index % 3]),
                          business_class='synthetic', data_location='satellite_1'))
    capacity_fraction, lower_fraction = {
        'healthy': (1.0, 0.98), 'degraded': (0.85, 0.8), 'critical': (0.7, 0.65),
    }[axis.health]
    lower_energy = axis.initial_energy_Wh * lower_fraction
    lower_capacity = 20.0 * capacity_fraction
    health = dict(soc_est=axis.initial_energy_Wh/20.0,
                  soc_lower=lower_energy/lower_capacity, capacity_Wh_est=20.0,
                  capacity_lower_Wh=lower_capacity, energy_lower_Wh=lower_energy,
                  rul_est=None, rul_unit=None, uncertainty_method='synthetic_fixed_bounds',
                  model_version='sandbox-axis-v1', observed_at_s=0.0, available_at_s=0.0,
                  reason_codes=['RUL_UNAVAILABLE'])
    rate = 16384.0 if axis.rate == 'robust' else 32768.0
    data_loss, ack_loss = {'none': (0.0, 0.0), 'mild': (0.05, 0.15),
                           'strong': (0.1, 0.65)}[axis.disturbance]
    window = dict(window_id='W1', start_s=0.0, end_s=32.0,
                  rate_profile=[dict(time_s=0.0, robust_bps=rate, fast_bps=rate*2)],
                  loss_profile=[dict(time_s=0.0, robust_loss_prob=data_loss, fast_loss_prob=data_loss)],
                  source='synthetic', forecast_version='sandbox-axis-v1')
    scenario = dict(schema_version='1.0', scenario_id='sandbox-axis-v1', source='synthetic',
                    capacity_Wh=20.0, initial_energy_Wh=axis.initial_energy_Wh,
                    reserve_Wh=axis.reserve_Wh, max_power_W=150.0,
                    powers=dict(base_W=36.0, solar_W=0.0, compute_W=0.0),
                    tx_power_W=dict(robust=36.0, fast=72.0), slot_s=1.0,
                    forecast_version='sandbox-axis-v1', tasks=tasks, true_windows=[window],
                    forecast_windows=[window], health_observations=[health],
                    protocol=dict(data_propagation_s=0.0, ack_propagation_s=0.0,
                                  control_bps=1024.0, ack_rx_W=8.0),
                    channel=dict(seed=seed, ack_loss_prob=ack_loss))
    return RunConfig.model_validate(dict(schema_version='1.0', kind='rule_validation',
        scenario=scenario, evaluation_end_s=32.0, actions=[], seed=seed)).model_dump(mode='json')
