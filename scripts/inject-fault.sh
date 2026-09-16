#!/usr/bin/env bash
# Usage: ./scripts/inject-fault.sh "Northgate Assembly/Motor-1" overheating
set -euo pipefail
cd "$(dirname "$0")/.."
python scripts/fault_ctl.py inject "$1" "$2"
