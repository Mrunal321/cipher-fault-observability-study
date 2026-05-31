"""
BLIF netlist parser.

Parses a flat (no subcircuits) or pre-flattened BLIF file into a Circuit
object suitable for simulation and fault injection.

Supports:
  .model, .inputs, .outputs, .names (truth-table logic gates), .end
  Multi-model files: returns the last (top-level) model, or the one
  whose name matches a requested top name.

Does NOT support: .latch, .subckt (use a flattened netlist).
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class Gate:
    """A single .names gate: computes output from inputs via truth table."""
    output: str
    inputs: List[str]
    # Each row is a pair (input_cube: str, output_val: int)
    # input_cube uses '0','1','-' per input position
    cover: List[Tuple[str, int]] = field(default_factory=list)

    def evaluate(self, vals: Dict[str, int]) -> int:
        """
        Evaluate this gate given a signal-value mapping.
        Returns 0 or 1.
        """
        if not self.inputs:
            # Constant: single cover row with no input pattern
            if self.cover:
                return self.cover[0][1]
            return 0

        for cube, out_val in self.cover:
            match = True
            for i, ch in enumerate(cube):
                if ch == '-':
                    continue
                sig = self.inputs[i]
                v = vals.get(sig, 0)
                if ch == '0' and v != 0:
                    match = False
                    break
                if ch == '1' and v != 1:
                    match = False
                    break
            if match:
                return out_val
        return 0  # default output is 0


@dataclass
class Circuit:
    name: str
    inputs: List[str]
    outputs: List[str]
    gates: List[Gate] = field(default_factory=list)
    # signal name → Gate that drives it
    _drivers: Dict[str, Gate] = field(default_factory=dict, repr=False)

    def build_index(self) -> None:
        self._drivers = {g.output: g for g in self.gates}

    def topo_order(self) -> List[Gate]:
        """Return gates in topological order (inputs first)."""
        visited: Set[str] = set(self.inputs)
        order: List[Gate] = []
        self._topo_visit(visited, order)
        return order

    def _topo_visit(
        self,
        visited: Set[str],
        order: List[Gate],
    ) -> None:
        def visit(sig: str) -> None:
            if sig in visited:
                return
            gate = self._drivers.get(sig)
            if gate is None:
                visited.add(sig)
                return
            for inp in gate.inputs:
                visit(inp)
            visited.add(sig)
            order.append(gate)

        for g in self.gates:
            visit(g.output)

    def all_internal_signals(self) -> List[str]:
        """All signal names that are driven by a gate (not primary inputs)."""
        return [g.output for g in self.gates]


def _tokenize_names_header(line: str) -> Tuple[List[str], str]:
    """Split '.names i0 i1 ... o' into ([i0, i1, ...], o)."""
    parts = line.split()
    if len(parts) < 2:
        return [], parts[1] if len(parts) == 2 else parts[0]
    signals = parts[1:]
    return signals[:-1], signals[-1]


def parse_blif(text: str, top_model: Optional[str] = None) -> Circuit:
    """
    Parse BLIF text and return a Circuit.

    If the file contains multiple models (e.g. with subcircuit definitions
    that were manually inlined), returns the model named top_model, or the
    last model if top_model is None.
    """
    models: List[Circuit] = []
    current: Optional[Circuit] = None
    current_gate: Optional[Gate] = None

    for raw_line in text.splitlines():
        # Strip comments and trailing whitespace
        line = raw_line.split('#')[0].rstrip()
        if not line:
            if current_gate is not None:
                # blank line ends a .names block (some tools emit this)
                pass
            continue

        if line.startswith('.model'):
            if current_gate is not None and current is not None:
                current.gates.append(current_gate)
                current_gate = None
            if current is not None:
                models.append(current)
            model_name = line.split(maxsplit=1)[1].strip() if len(line.split()) > 1 else ""
            current = Circuit(name=model_name, inputs=[], outputs=[])

        elif line.startswith('.inputs'):
            if current is not None:
                current.inputs.extend(line.split()[1:])

        elif line.startswith('.outputs'):
            if current is not None:
                current.outputs.extend(line.split()[1:])

        elif line.startswith('.names'):
            if current_gate is not None and current is not None:
                current.gates.append(current_gate)
            ins, out = _tokenize_names_header(line)
            current_gate = Gate(output=out, inputs=ins)

        elif line.startswith('.end'):
            if current_gate is not None and current is not None:
                current.gates.append(current_gate)
                current_gate = None
            if current is not None:
                models.append(current)
                current = None

        elif line.startswith('.'):
            # Unsupported directive — skip (latch, subckt, etc.)
            if current_gate is not None and current is not None:
                current.gates.append(current_gate)
                current_gate = None

        else:
            # Truth-table row
            if current_gate is not None:
                parts = line.split()
                if len(parts) == 1:
                    # Constant gate (no inputs): '1' or '0'
                    current_gate.cover.append(("", int(parts[0])))
                elif len(parts) == 2:
                    current_gate.cover.append((parts[0], int(parts[1])))

    # Handle file that ends without .end
    if current_gate is not None and current is not None:
        current.gates.append(current_gate)
    if current is not None:
        models.append(current)

    if not models:
        raise ValueError("No .model found in BLIF text")

    if top_model is not None:
        for m in models:
            if m.name == top_model:
                m.build_index()
                return m
        raise KeyError(f"Model '{top_model}' not found in BLIF file")

    result = models[-1]
    result.build_index()
    return result


def parse_blif_file(path: str, top_model: Optional[str] = None) -> Circuit:
    with open(path) as f:
        return parse_blif(f.read(), top_model)
