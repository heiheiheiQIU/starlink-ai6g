"""Synthetic external randomness indexed by physical time, never by packet count."""
import hashlib
import math
from fractions import Fraction
from typing import Literal

from backend.contracts import ContractModel,NonNegativeInt,PositiveFloat,Probability


class ChannelConfig(ContractModel):
    version: Literal['time-indexed-sha256-v1']='time-indexed-sha256-v1'
    seed: NonNegativeInt
    step_s: PositiveFloat=.25
    ack_loss_prob: Probability=0.0


def uniform_at(config:ChannelConfig,time_s:float,stream:Literal['data','ack']) -> float:
    if not math.isfinite(time_s) or time_s<0 or stream not in ('data','ack'):
        raise ValueError('Invalid channel time or stream')
    position=time_s/config.step_s
    if not math.isfinite(position):raise ValueError('Channel time index overflow')
    # Decimal input semantics avoid .3/.1 becoming 2.9999999999999996.
    index=Fraction(str(time_s))//Fraction(str(config.step_s))
    key=f'{config.version}|{config.seed}|{stream}|{index}'.encode('ascii')
    bits=int.from_bytes(hashlib.sha256(key).digest()[:8],'big')>>11
    return bits/(2**53)


def loss_at(windows,time_s,mode):
    for window in windows:
        if window.start_s<=time_s<window.end_s:
            point=max((p for p in window.loss_profile if p.time_s<=time_s),key=lambda p:p.time_s)
            return getattr(point,mode+'_loss_prob')
    raise ValueError('Loss sample outside visible window')
