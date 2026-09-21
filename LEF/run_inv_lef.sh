#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_root"

pdk_path="${PDKPATH:-/foss/pdks/sky130A}"
magic -dnull -noconsole -rcfile "$pdk_path/libs.tech/magic/sky130A.magicrc" Layout/invX1.mag < LEF/export_inv_lef.tcl > Reports/inv_lef.log 2>&1

grep -q 'MACRO inv' LEF/inv.lef
grep -q 'PIN vin' LEF/inv.lef
grep -q 'PIN vout' LEF/inv.lef
grep -q 'PIN Vdd' LEF/inv.lef
grep -q 'PIN Vss' LEF/inv.lef

printf 'Generated LEF/inv.lef\n'
