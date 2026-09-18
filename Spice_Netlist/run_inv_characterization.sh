#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$repo_root"

results=Reports/inv_characterization.csv
printf '%s\n' 'metric,slew_ps,load_fF,condition,value,unit' > "$results"

ngspice -b Spice_Netlist/inv_timing_char.spice > Reports/inv_timing_char.log 2>&1
ngspice -b Spice_Netlist/inv_input_cap.spice > Reports/inv_input_cap.log 2>&1
ngspice -b Spice_Netlist/inv_power_char.spice > Reports/inv_power_char.log 2>&1

logs=(Reports/inv_timing_char.log Reports/inv_input_cap.log Reports/inv_power_char.log)
if grep -Eiq 'measure .*failed|Error:' "${logs[@]}"; then
    grep -Ein 'measure .*failed|Error:' "${logs[@]}"
    exit 1
fi

awk -F, '
NR == 1 {
    if ($0 != "metric,slew_ps,load_fF,condition,value,unit") exit 1
    next
}
NF != 6 || $1 == "" || $4 == "" || $5 == "" || $6 == "" { exit 1 }
$5 !~ /^[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?$/ { exit 1 }
$5 + 0 < 0 { exit 1 }
{ count[$1]++ }
END {
    if (NR != 60) exit 1
    if (count["rise_transition"] != 9) exit 1
    if (count["fall_transition"] != 9) exit 1
    if (count["cell_rise_delay"] != 9) exit 1
    if (count["cell_fall_delay"] != 9) exit 1
    if (count["rise_dynamic_power"] != 9) exit 1
    if (count["fall_dynamic_power"] != 9) exit 1
    if (count["input_cap"] != 3) exit 1
    if (count["static_power"] != 2) exit 1
}
' "$results"

python3 LIB/populate_inv_docx.py "$results" LIB/inv.docx
printf 'Validated 59 characterization records in %s\n' "$results"
