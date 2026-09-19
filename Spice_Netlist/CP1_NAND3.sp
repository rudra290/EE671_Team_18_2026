* SPICE model mimicking physical stick diagram with shared diffusion and taps
* Function: out = !(~A . B . C)

.lib /foss/pdks/sky130A/libs.tech/ngspice/sky130.lib.spice tt

.subckt INVX1 in vdd vss out
XM1 out in vdd vdd sky130_fd_pr__pfet_01v8 l=0.15 w=1.26 as='w*2*l' ad='w*2*l' ps='2*(w+(2*l))' pd='2*(w+(2*l))'
XM2 out in vss vss sky130_fd_pr__nfet_01v8 l=0.15 w=0.42 as='w*2*l' ad='w*2*l' ps='2*(w+(2*l))' pd='2*(w+(2*l))'
.ends INVX1

.subckt INVX2 in vdd vss out
XM1 out in vdd vdd sky130_fd_pr__pfet_01v8 l=0.15 w=1.57 as='w*2*l' ad='w*2*l' ps='2*(w+(2*l))' pd='2*(w+(2*l))'
XM2 out in vss vss sky130_fd_pr__nfet_01v8 l=0.15 w=0.51 as='w*2*l' ad='w*2*l' ps='2*(w+(2*l))' pd='2*(w+(2*l))'
.ends INVX2

.subckt NAND vdd a b c vss out
* Input Inverter for A
XINVA a vdd vss abar INVX1

* --- P-PULL-UP NETWORK (Continuous P-diffusion strip, Bulk = vdd) ---
* M_Ap shares drain (out) with M_Bp. M_Bp shares source (vdd) with M_Cp.
XM_Ap_bar out  abar vdd vdd sky130_fd_pr__pfet_01v8 l=0.15 w=1.26
+ as='w*2*l'       ps='2*(w+(2*l))'
+ ad='w*l'         pd='w'

XM_Bp     out  b    vdd vdd sky130_fd_pr__pfet_01v8 l=0.15 w=1.26
+ as='w*l'         ps='w'
+ ad='w*l'         pd='w'

XM_Cp     out  c    vdd vdd sky130_fd_pr__pfet_01v8 l=0.15 w=1.26
+ as='w*l'         ps='w'
+ ad='w*2*l'       pd='2*(w+(2*l))'

* --- N-PULL-DOWN NETWORK (Continuous N-diffusion strip, Bulk = vss) ---
* Nodes 'ab' and 'bc' are uncontacted internal shared diffusions (half area per side).
XM_An_bar out  abar ab  vss sky130_fd_pr__nfet_01v8 l=0.15 w=1.26
+ ad='w*2*l'       pd='2*(w+(2*l))'
+ as='w*l'         ps='w'

XM_Bn     ab   b    bc  vss sky130_fd_pr__nfet_01v8 l=0.15 w=1.26
+ ad='w*l'         pd='w'
+ as='w*l'         ps='w'

XM_Cn     bc   c    vss vss sky130_fd_pr__nfet_01v8 l=0.15 w=1.26
+ ad='w*l'         pd='w'
+ as='w*2*l'       ps='2*(w+(2*l))'
.ends NAND

* --- TESTBENCH ---
VDD vdd 0 DC 1.8
V_A in  0 PULSE(0 1.8 1n 10p 10p 3n 6n)

* Test setup: pin ordering is (vdd a b c vss out)
* Setting b=vdd, c=vdd means out tracks input 'a' directly (out = A)
XNAND vdd in vdd vdd 0 out NAND
 Xb1 out vdd 0 B1_out INVX1
 Xb2 B1_out vdd 0 B2_out INVX2
 XLOAD B2_out vdd 0 LOAD_OUT INVX1
*XLOAD out vdd 0 LOAD_OUT INVX1

.tran 1p 8n
.measure tran tr TRIG v(B2_out) VAL=0.36 RISE=1 TARG v(B2_out) VAL=1.44 RISE=1
.measure tran tf TRIG v(B2_out) VAL=1.44 FALL=1 TARG v(B2_out) VAL=0.36 FALL=1
*.measure tran tr TRIG v(out) VAL=0.36 RISE=1 TARG v(out) VAL=1.44 RISE=1
*.measure tran tf TRIG v(out) VAL=1.44 FALL=1 TARG v(out) VAL=0.36 FALL=1

.control
run
plot v(in) v(B2_out)
*plot v(in) v(out)
.endc

.end
