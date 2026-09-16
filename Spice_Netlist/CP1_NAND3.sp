.lib /foss/pdks/sky130A/libs.tech/ngspice/sky130.lib.spice tt

.subckt INVX1 in vdd vss out
XM1 out in vdd vdd sky130_fd_pr__pfet_01v8 l=0.15 w=1.26 as='w*2*l' ad='w*2*l' ps='2*(w+(2*l))' pd='2*(w+(2*l))'
XM2 out in vss vss sky130_fd_pr__nfet_01v8 l=0.15 w=0.42 as='w*2*l' ad='w*2*l' ps='2*(w+(2*l))' pd='2*(w+(2*l))'
.ends INVX1

.subckt INVX2 in vdd vss out
XM1 out in vdd vdd sky130_fd_pr__pfet_01v8 l=0.15 w=2.52 as='w*2*l' ad='w*2*l' ps='2*(w+(2*l))' pd='2*(w+(2*l))'
XM2 out in vss vss sky130_fd_pr__nfet_01v8 l=0.15 w=0.84 as='w*2*l' ad='w*2*l' ps='2*(w+(2*l))' pd='2*(w+(2*l))'
.ends INVX2

* drain gate source body

.subckt NAND vdd a b c vss out
XINVA a vdd vss abar INVX2
XM_Ap_bar   out abar vdd vdd sky130_fd_pr__pfet_01v8 l=0.15 w=3 as='w*2*l' ad='w*2*l' ps='2*(w+(2*l))' pd='2*(w+(2*l))'
XM_Bp       out b vdd vdd sky130_fd_pr__pfet_01v8 l=0.15 w=2.4 as='w*2*l' ad='w*2*l' ps='2*(w+(2*l))' pd='2*(w+(2*l))'
XM_Cp       out c vdd vdd sky130_fd_pr__pfet_01v8 l=0.15 w=2.4 as='w*2*l' ad='w*2*l' ps='2*(w+(2*l))' pd='2*(w+(2*l))'
XM_An_bar   out abar ab ab sky130_fd_pr__nfet_01v8 l=0.15 w=1.0 as='w*2*l' ad='w*2*l' ps='2*(w+(2*l))' pd='2*(w+(2*l))'
XM_Bn       ab b bc bc sky130_fd_pr__nfet_01v8 l=0.15 w=1.26 as='w*2*l' ad='w*2*l' ps='2*(w+(2*l))' pd='2*(w+(2*l))'
XM_Cn       bc c vss vss sky130_fd_pr__nfet_01v8 l=0.15 w=1.26 as='w*2*l' ad='w*2*l' ps='2*(w+(2*l))' pd='2*(w+(2*l))'
.ends NAND

* TOP-LEVEL TESTBENCH

VDD vdd 0 DC 1.8
V_A in 0 PULSE(0 1.8 1n 10p 10p 3n 6n)
* B=C=vdd NAND out = A
XNAND vdd in vdd vdd 0 out NAND
XLOAD out vdd 0 LOAD_OUT INVX1

* Optional capacitive load
* CLOAD Q 0 0.5f

.tran 1p 12n
.measure tran tr TRIG v(out) VAL=0.36 RISE=1 TARG v(out) VAL=1.44 RISE=1
.measure tran tf TRIG v(out) VAL=1.44 FALL=1 TARG v(out) VAL=0.36 FALL=1

.control
run
plot v(in) v(out)
.endc

.end