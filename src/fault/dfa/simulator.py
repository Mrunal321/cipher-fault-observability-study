"""
Combinational circuit simulator for BLIF netlists.

Simulates a Circuit (from blif_parser) given primary input assignments,
returning values for all signals including primary outputs.

Supports fault injection via an optional override dict that forces
specific signals to fixed values before propagation.
"""

from __future__ import annotations
from typing import Dict, List, Optional
from .blif_parser import Circuit


def simulate(
    circuit: Circuit,
    inputs: Dict[str, int],
    overrides: Optional[Dict[str, int]] = None,
) -> Dict[str, int]:
    """
    Evaluate all signals in the circuit.

    Parameters
    ----------
    circuit:
        Parsed Circuit object with build_index() already called.
    inputs:
        Primary input signal → value (0 or 1) mapping.
        Missing inputs default to 0.
    overrides:
        Signal → forced-value mapping applied AFTER the gate that drives
        a signal fires. Models stuck-at faults or bit-flip injection at
        any internal wire.

    Returns
    -------
    Full signal value dict (inputs + all gate outputs).
    """
    vals: Dict[str, int] = dict(inputs)

    if overrides:
        # Apply overrides on primary inputs before propagation
        for sig, v in overrides.items():
            if sig in circuit.inputs:
                vals[sig] = v

    for gate in circuit.topo_order():
        v = gate.evaluate(vals)
        # Apply override after gate fires (models fault at gate output wire)
        if overrides and gate.output in overrides:
            v = overrides[gate.output]
        vals[gate.output] = v

    return vals


def simulate_outputs(
    circuit: Circuit,
    inputs: Dict[str, int],
    overrides: Optional[Dict[str, int]] = None,
) -> Dict[str, int]:
    """Return only the primary output signal values."""
    vals = simulate(circuit, inputs, overrides)
    return {sig: vals.get(sig, 0) for sig in circuit.outputs}


def outputs_to_int(
    circuit: Circuit,
    output_vals: Dict[str, int],
) -> int:
    """Pack output bits into an integer, MSB = outputs[0]."""
    result = 0
    for sig in circuit.outputs:
        result = (result << 1) | output_vals.get(sig, 0)
    return result


def inputs_from_int(
    circuit: Circuit,
    value: int,
) -> Dict[str, int]:
    """Unpack an integer into primary input dict, MSB = inputs[0]."""
    n = len(circuit.inputs)
    result = {}
    for i, sig in enumerate(circuit.inputs):
        result[sig] = (value >> (n - 1 - i)) & 1
    return result


def batch_simulate(
    circuit: Circuit,
    input_vectors: List[Dict[str, int]],
    overrides: Optional[Dict[str, int]] = None,
) -> List[Dict[str, int]]:
    """Simulate a list of input vectors; return list of output dicts."""
    return [simulate_outputs(circuit, iv, overrides) for iv in input_vectors]
