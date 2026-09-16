#!/usr/bin/env bash
# Usage: ./scripts/remove-fault.sh "Northgate Assembly/Motor-1" overheating
set -euo pipefail
cd "$(dirname "$0")/.."
python scripts/fault_ctl.py remove "$1" "$2"
