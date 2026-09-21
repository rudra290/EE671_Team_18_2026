# Inverter Post Layout Completion Flow

## Baseline

- Branch: `datta/inv-complete`
- Canonical layout: `Layout/invX1.mag`
- Legacy uppercase layouts are retained but are not the source for this flow.
- Technology: SKY130A
- Corner: TT, `27 °C`, `VDD = 1.8 V`
- Cell dimensions: `1.67 µm × 3.20 µm`
- Cell area: `5.344 µm²`
- Pins: `vin`, `vout`, `Vdd`, `Vss`
- PMOS: `W = 1.26 µm`, `L = 0.15 µm`
- NMOS: `W = 0.42 µm`, `L = 0.15 µm`
- Transition thresholds: `0.36 V` and `1.44 V`
- Propagation-delay threshold: `0.9 V`

## Status

- [x] Canonical layout and dimensions identified
- [x] DRC reports zero errors
- [x] LVS matches uniquely
- [x] Capacitance-extracted PEX netlist verified
- [x] Functional FO1 deck retained unchanged
- [x] Automated timing, input-capacitance, and power decks prepared
- [x] Machine-readable CSV and inverter-only DOCX pipeline prepared
- [x] Verilog model and self-checking testbench prepared
- [x] LEF export automation prepared
- [x] CharLib PEX wrapper and configuration prepared
- [ ] Run automated characterization inside IIC-OSIC
- [ ] Export and visually inspect the LEF inside Magic
- [ ] Compile and run the Verilog test inside IIC-OSIC
- [ ] Run CharLib and inspect `Charlib/inv.lib`
- [ ] Add the required screenshots and final measured values to the report

## Flow Order

Use this order for the inverter and the remaining cells:

1. Inspect circuit sizing and layout dimensions.
2. Run DRC.
3. Extract the LVS netlist and run LVS.
4. Extract the PEX netlist.
5. Run the functional test.
6. Run timing, input-capacitance, static-power, and dynamic-power characterization.
7. Export and inspect LEF.
8. Compile and test Verilog.
9. Run CharLib and inspect the Liberty file.
10. Fill the report and collect evidence.

## DRC

Magic Tcl commands:

```tcl
drc check
drc catchup
drc count total
```

Recorded result: `Total DRC errors found: 0`.

Required evidence: a readable layout screenshot with the zero-error Tcl result and the `1.67 µm × 3.20 µm` cell dimensions.

## LVS

Reference netlist: `Spice_Netlist/inv_schematic.spice`

Layout-derived netlist: `Spice_Netlist/inv_layout_lvs.spice`

Run from the repository root:

```bash
netgen -batch lvs \
  "Spice_Netlist/inv_layout_lvs.spice Inverter_X1" \
  "Spice_Netlist/inv_schematic.spice Inverter_X1" \
  "/foss/pdks/sky130A/libs.tech/netgen/sky130A_setup.tcl" \
  "Reports/inv_lvs_report.txt"
```

Recorded result: `Netlists match uniquely` and `Final result: Circuits match uniquely`.

## PEX

PEX netlist: `Spice_Netlist/inv_pex.spice`

The current PEX file contains:

- Four external nodes: `vin`, `vout`, `Vdd`, `Vss`
- One PMOS with `W/L = 1.26/0.15 µm`
- One NMOS with `W/L = 0.42/0.15 µm`
- Six extracted capacitors
- Total listed parasitic capacitance: `1.03982 fF`

The generated PEX remains flat and unedited. The simulation decks provide the required `.subckt` wrapper. Explicit extracted interconnect resistors are not used for this inverter.

## Functional Test

Deck: `Spice_Netlist/inv_pex_functional.spice`

Run:

```bash
ngspice Spice_Netlist/inv_pex_functional.spice
```

The deck drives one PEX inverter with another identical PEX inverter as the load. Verify that `out1 = !in` and `out2 = in`, record `tr`, `tf`, `tphl`, `tplh`, and `tp`, and save the waveform. The previously observed rise and fall transitions were approximately `21 ps`; copy the exact terminal values into the final report.

## Automated Characterization

Run from the repository root:

```bash
bash Spice_Netlist/run_inv_characterization.sh
```

The runner performs:

- `inv_timing_char.spice`: 3×3 rise/fall transition and cell-rise/cell-fall delay characterization
- `inv_input_cap.spice`: `1 µA` current-source rise/fall input-capacitance measurement from 20% to 80% of VDD
- `inv_power_char.spice`: static power for both input states and 3×3 rise/fall dynamic power

The characterization grid is:

| Output load | Input slews |
|---:|---:|
| `0.5 fF` | `10 ps`, `100 ps`, `1000 ps` |
| `10 fF` | `10 ps`, `100 ps`, `1000 ps` |
| `100 fF` | `10 ps`, `100 ps`, `1000 ps` |

Input capacitance is calculated as:

```text
C = 1 µA × (t80 - t20) / 1.08 V
```

The PEX output is left unloaded during this measurement. Dynamic power is the average supply energy over an `8 ns` event period after subtracting the weighted static leakage baseline.

Successful execution produces exactly 59 data rows plus the header in `Reports/inv_characterization.csv` and repopulates `LIB/inv.docx`:

- 36 timing records
- 18 dynamic-power records
- 3 input-capacitance records
- 2 static-power records

The runner fails if an ngspice measurement fails, a value is missing or negative, or the record counts are incorrect.

## LEF

Run:

```bash
bash LEF/run_inv_lef.sh
```

This opens `Layout/invX1.mag` in batch Magic, renames the in-memory top cell to `inv`, and writes `LEF/inv.lef`. Inspect the result in a text editor and layout viewer. Confirm the macro size, boundary, four pins, pin layers, directions, and power rails before marking it complete.

## Verilog

Model: `Verilog/inv.v`

Self-checking testbench: `Verilog/inv_tb.v`

Run:

```bash
bash Verilog/run_inv_test.sh
```

The expected terminal result is `inv functional test passed`.

## CharLib

PEX wrapper: `Spice_Netlist/inv_charlib.spice`

Configuration: `Charlib/inv.yaml`

Run:

```bash
bash Charlib/run_inv_charlib.sh
```

The configuration uses TT at `1.8 V` and `27 °C`, the same 20%/80%/50% thresholds, and the same 3×3 slew/load grid as the manual characterization. The script requires `Charlib/inv.lib` to contain the inverter cell, Boolean function, and both 3×3 indexes.

CharLib uses charge integration for its Liberty input capacitance. The manual course-table capacitance remains the separate constant-current result. Compare their scale and document any difference rather than replacing one with the other.

## Final Evidence

The final report still needs:

- Circuit diagram and MOSFET W/L table
- Layout screenshot and `1.67 µm × 3.20 µm` area annotation
- PEX netlist screenshot
- Zero-DRC screenshot
- Clean-LVS screenshot
- Functional and timing waveforms with readable axes and units
- Fully populated inverter characterization document
- LEF inspection evidence
- Verilog compile/test output
- CharLib command output and Liberty excerpts
- Team contribution table

Do not commit `.ext`, raw waveform, swap, temporary renderer, or failed intermediate files.
