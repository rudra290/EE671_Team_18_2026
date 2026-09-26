* SPICE model mimicking physical stick diagram with shared diffusion and taps
* Function: out = !(~A . B . C)

.lib /foss/pdks/sky130A/libs.tech/ngspice/sky130.lib.spice tt

.subckt Inverter_X1 in vdd vss out
XM1 out in vdd vdd sky130_fd_pr__pfet_01v8 l=0.15 w=1.26 as='w*2*l' ad='w*2*l' ps='2*(w+(2*l))' pd='2*(w+(2*l))'
XM2 out in vss vss sky130_fd_pr__nfet_01v8 l=0.15 w=0.42 as='w*2*l' ad='w*2*l' ps='2*(w+(2*l))' pd='2*(w+(2*l))'
.ends Inverter_X1

.subckt Inverter_X1_25 in vdd vss out
XM1 out in vdd vdd sky130_fd_pr__pfet_01v8 l=0.15 w=1.57 as='w*2*l' ad='w*2*l' ps='2*(w+(2*l))' pd='2*(w+(2*l))'
XM2 out in vss vss sky130_fd_pr__nfet_01v8 l=0.15 w=0.51 as='w*2*l' ad='w*2*l' ps='2*(w+(2*l))' pd='2*(w+(2*l))'
.ends Inverter_X1_25

.subckt NAND vdd a b c vss out

* --- P-PULL-UP NETWORK (Continuous P-diffusion strip, Bulk = vdd) ---
XM_Ap_bar out  a vdd vdd sky130_fd_pr__pfet_01v8 l=0.15 w=1.26 as='w*2*l' ps='2*(w+(2*l))' ad='w*l' pd='w'
XM_Bp     out  b    vdd vdd sky130_fd_pr__pfet_01v8 l=0.15 w=1.26 as='w*l' ps='w' ad='w*l' pd='w'
XM_Cp     out  c    vdd vdd sky130_fd_pr__pfet_01v8 l=0.15 w=1.26 as='w*l' ps='w' ad='w*2*l' pd='2*(w+(2*l))'

* --- N-PULL-DOWN NETWORK (Continuous N-diffusion strip, Bulk = vss) ---
XM_An_bar out  a ab  vss sky130_fd_pr__nfet_01v8 l=0.15 w=1.26 ad='w*2*l' pd='2*(w+(2*l))' as='w*l' ps='w'
XM_Bn     ab   b    bc  vss sky130_fd_pr__nfet_01v8 l=0.15 w=1.26 ad='w*l' pd='w' as='w*l' ps='w'
XM_Cn     bc   c    vss vss sky130_fd_pr__nfet_01v8 l=0.15 w=1.26 ad='w*l' pd='w' as='w*2*l' ps='2*(w+(2*l))'

.ends NAND

.subckt nand3b vdd a b c vss out
XINVA a vdd vss abar Inverter_X1
XNAND vdd abar b c vss N1_out NAND
Xb1 N1_out vdd vss B1_out Inverter_X1
Xb2 B1_out vdd vss out Inverter_X1_25
.ends nand3b

* --- TESTBENCH ---
VDD vdd 0 DC 1.8
V_A in  0 PULSE(0 1.8 1n 10p 10p 3n 6n)

* Test setup: pin ordering is (vdd a b c vss out)
* Setting b=vdd, c=vdd means out tracks input 'a' directly (out = A)
XNAND3B vdd 0 vdd in 0 out nand3b
XLOAD out vdd 0 LOAD_OUT Inverter_X1

.tran 1p 8n
.measure tran tr TRIG v(out) VAL=0.36 RISE=1 TARG v(out) VAL=1.44 RISE=1
.measure tran tf TRIG v(out) VAL=1.44 FALL=1 TARG v(out) VAL=0.36 FALL=1

.control
run
set color0=white
set color1=black
* plot v(in) v(B2_out)
meas tran x_intersect1 when v(out)=0.36 RISE=1
let y_marker1 = 0.36 + 0 * time 
let x_marker1 = 1.8 * (time >= x_intersect1) 
meas tran x_intersect2 when v(out)=1.44 RISE=1
let y_marker2 = 1.44 + 0 * time 
let x_marker2 = 1.8 * (time >= x_intersect2)
plot v(in) v(out) y_marker1 y_marker2 x_marker1 x_marker2
.endc

.end
