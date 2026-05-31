"""
Fault injection models for DFA on BLIF circuits.

Supported fault models:
  - STUCK_AT_0 / STUCK_AT_1 : permanent stuck-at fault on a wire
  - BIT_FLIP                 : transient single-bit flip (value ^ 1)
  - RANDOM_BYTE              : random value on an 8-bit bus segment

Each FaultSpec describes one fault site. The injector resolves it to
a signal override dict consumed by simulator.simulate().
"""

from __future__ import annotations
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional
from .blif_parser import Circuit


class FaultModel(Enum):
    STUCK_AT_0  = auto()
    STUCK_AT_1  = auto()
    BIT_FLIP    = auto()
    RANDOM_BYTE = auto()


@dataclass
class FaultSpec:
    """Describes a single fault injection site."""
    signal: str           # wire name in the circuit
    model: FaultModel
    # For BIT_FLIP the injector needs the correct value to flip.
    # For RANDOM_BYTE the signal must be the MSB of an 8-bit bus.
    bus_signals: Optional[List[str]] = None  # used by RANDOM_BYTE


def resolve_fault(
    spec: FaultSpec,
    correct_vals: Dict[str, int],
    rng: Optional[random.Random] = None,
) -> Dict[str, int]:
    """
    Return a signal override dict for this fault spec.

    correct_vals: result of a fault-free simulation (needed for BIT_FLIP
                  to know the correct value to flip).
    rng: optional seeded RNG for reproducibility.
    """
    if rng is None:
        rng = random.Random()

    if spec.model == FaultModel.STUCK_AT_0:
        return {spec.signal: 0}

    if spec.model == FaultModel.STUCK_AT_1:
        return {spec.signal: 1}

    if spec.model == FaultModel.BIT_FLIP:
        v = correct_vals.get(spec.signal, 0)
        return {spec.signal: v ^ 1}

    if spec.model == FaultModel.RANDOM_BYTE:
        sigs = spec.bus_signals or [spec.signal]
        val = rng.randint(0, (1 << len(sigs)) - 1)
        return {s: (val >> (len(sigs) - 1 - i)) & 1
                for i, s in enumerate(sigs)}

    raise ValueError(f"Unknown fault model: {spec.model}")


def enumerate_single_bit_faults(
    circuit: Circuit,
    model: FaultModel = FaultModel.BIT_FLIP,
    include_inputs: bool = False,
) -> List[FaultSpec]:
    """
    Return one FaultSpec per injectable wire in the circuit.

    By default covers all gate outputs (internal signals + primary outputs).
    Set include_inputs=True to also inject on primary inputs.
    """
    faults: List[FaultSpec] = []
    if include_inputs:
        for sig in circuit.inputs:
            faults.append(FaultSpec(signal=sig, model=model))
    for gate in circuit.gates:
        faults.append(FaultSpec(signal=gate.output, model=model))
    return faults


def enumerate_sbox_output_faults(
    circuit: Circuit,
    sbox_output_prefix: str,
    model: FaultModel = FaultModel.BIT_FLIP,
) -> List[FaultSpec]:
    """
    Return faults restricted to signals whose names start with
    sbox_output_prefix (e.g. 'sb0_o', 'sb1_o', ...).

    Useful for targeting the S-box output layer specifically.
    """
    faults = []
    for gate in circuit.gates:
        if gate.output.startswith(sbox_output_prefix):
            faults.append(FaultSpec(signal=gate.output, model=model))
    return faults


def build_byte_fault_specs(
    circuit: Circuit,
    bus_prefix: str,
    bus_width: int = 8,
    model: FaultModel = FaultModel.RANDOM_BYTE,
) -> List[FaultSpec]:
    """
    Group signals by bus_prefix+N (e.g. 'state_out') into byte-wide
    FaultSpecs for RANDOM_BYTE injection.

    Signals must be named <bus_prefix><index>.
    """
    sigs = sorted(
        [s for s in [g.output for g in circuit.gates]
         if s.startswith(bus_prefix)],
        key=lambda s: int(s[len(bus_prefix):]) if s[len(bus_prefix):].isdigit() else -1,
    )
    specs = []
    for start in range(0, len(sigs) - bus_width + 1, bus_width):
        group = sigs[start:start + bus_width]
        specs.append(FaultSpec(
            signal=group[0],
            model=model,
            bus_signals=group,
        ))
    return specs
