### The final report must have the following (Cell-1, Cell-2 followed by Cell-3):
1. Circuit Diagram of the Cell with a table of MOSFET width and length
2. Screenshot of the cell layout (with area mentioned as WIDTH X HEIGHT)
3. Screenshot of the PEX netlist
4. DRC and LVS clean screenshots
5. Waveforms from one simulation (input, outputs and clocks clearly shown) – i.e., one waveform each for propagation delay, rise or fall transition time, set-up time, hold-time
6. A completely filled Timing and Power tables (similar to the .doc files in the LIB folder).
7. Table of contribution of each member of the team.

### Command to make Report 
```bash
pandoc temp.md --template=template.tex -o output.pdf --pdf-engine=lualatex --filter pandoc-crossref --lua-filter=inline.lua 
```

### Note for understanding the files in Layout_Screenshots
Files ending in layout are annotated, DRC Clean Screenshots.

Screenshots with 'Masked' written on them do not show the entire layout of the cell, it shows on the instantiation and the connection of different cells to complete the entire layout. 

You can see Schematic of the invx1, dfxtn, nand3b in the svg form at the same level as Layout_Screenshots in the [Schematic](./Schematic) folder.
