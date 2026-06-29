#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

usage() {
  cat <<'EOF'
Usage: ./reproduce.sh [--quick|--full]

Default / quick mode:
  Regenerate active summary JSONs from frozen experiment outputs and verify
  the paper-facing headline numbers.

Full mode:
  Rerun the AOIG/MIG fault campaign, regenerate the AIG-control data,
  recompute target-layer controls, rerun MAJ-n experiments, and verify
  the reported summary numbers. This requires yosys for the AIG
  regeneration step and is sensitive to the yosys/ABC version used to
  regenerate the decomposed AIG controls.
EOF
}

FULL=0
if [[ "${1:-}" == "--quick" ]]; then
  FULL=0
elif [[ "${1:-}" == "--full" ]]; then
  FULL=1
elif [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
elif [[ $# -gt 0 ]]; then
  usage >&2
  exit 2
fi

if [[ "$FULL" == "1" ]]; then
  echo "[1/5] Running AOIG/MIG fault campaign"
  python3 scripts/run_fault_coverage.py

  echo "[2/5] Running AIG granularity-control campaign"
  python3 scripts/granularity_baseline.py

  echo "[3/5] Running target-layer and ARX/substitution controls"
  python3 scripts/invariant_metric.py

  echo "[4/5] Running synthetic MAJ-n study"
  python3 scripts/maj_arity_fault_study.py

  echo "[5/5] Recomputing summaries and verifying numbers"
  python3 scripts/analyze_results.py
  python3 scripts/verify_summary_numbers.py
else
  echo "[1/2] Recomputing summary metrics from frozen JSONs"
  python3 scripts/analyze_results.py

  echo "[2/2] Verifying reported summary numbers"
  python3 scripts/verify_summary_numbers.py
fi

echo "Done."
