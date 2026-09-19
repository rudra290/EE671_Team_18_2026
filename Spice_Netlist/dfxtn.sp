
.lib /foss/pdks/sky130A/libs.tech/ngspice/sky130.lib.spice tt

.subckt Inverter_X1 in vdd vss out
XM1 out in vdd vdd sky130_fd_pr__pfet_01v8 l=0.15 w=1.26 as='w*2*l' ad='w*2*l' ps='2*(w+(2*l))' pd='2*(w+(2*l))'
XM2 out in vss vss sky130_fd_pr__nfet_01v8 l=0.15 w=0.42 as='w*2*l' ad='w*2*l' ps='2*(w+(2*l))' pd='2*(w+(2*l))'
.ends Inverter_X1

.subckt Inverter_X2 in vdd vss out
XM1 out in vdd vdd sky130_fd_pr__pfet_01v8 l=0.15 w=2.52 as='w*2*l' ad='w*2*l' ps='2*(w+(2*l))' pd='2*(w+(2*l))'
XM2 out in vss vss sky130_fd_pr__nfet_01v8 l=0.15 w=0.78 as='w*2*l' ad='w*2*l' ps='2*(w+(2*l))' pd='2*(w+(2*l))'
.ends Inverter_X2

.subckt Transmission_gate in n_in out p_in vdd vss
XM1 in n_in out vss sky130_fd_pr__nfet_01v8 l=0.15 w=0.42 as='w*2*l' ad='w*2*l' ps='2*(w+(2*l))' pd='2*(w+(2*l))'
XM2 out p_in in vdd sky130_fd_pr__pfet_01v8 l=0.15 w=0.98 as='w*2*l' ad='w*2*l' ps='2*(w+(2*l))' pd='2*(w+(2*l))'
.ends Transmission_gate

.subckt latch D CLK CLK_B vdd vss Q
XTG_IN D CLK A CLK_B vdd vss Transmission_gate
XINV1 A vdd vss Q Inverter_X2
XINV2 Q vdd vss B Inverter_X1
XTG_FB B CLK_B A CLK vdd vss Transmission_gate
.ends latch

.subckt dfxtn D CLK vdd vss Q
XINV_CLK CLK vdd vss CLK_B Inverter_X1
XINV_D D vdd vss D_B Inverter_X1
XDLATCH_A D_B CLK CLK_B vdd vss Q_A latch
XDLATCH_B Q_A CLK_B CLK vdd vss Q_B latch
XINV_O Q_B vdd vss Q Inverter_X2
.ends dfxtn


* TOP-LEVEL TESTBENCH

VDD vdd 0 DC 1.8
VD D 0 PULSE(0 1.8 0 10p 10p 10n 20n)
VCLK CLK 0 PULSE(1.8 0 200p 10p 10p 5n 10n)
XDFT D CLK vdd 0 Q dfxtn
XLOAD Q vdd 0 LOAD_OUT Inverter_X1

* Optional capacitive load
* CLOAD Q 0 0.5f

.tran 10p 30n

.measure tran trise TRIG v(Q) VAL=0.36 RISE=1 TARG v(Q) VAL=1.44 RISE=1
.measure tran tfall TRIG v(Q) VAL=1.44 FALL=1 TARG v(Q) VAL=0.36 FALL=1

.control
run
plot v(D) v(CLK) v(Q)
.endc

.end
