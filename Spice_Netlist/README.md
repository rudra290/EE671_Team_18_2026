# The Spice models

We need to add spice models for the following:
- Inverter X1
- Dflipflop
- NAND3B

> I have added Two tests for Transmission gate PMOS width calculation. And after the simulations I can say, we should use Wp = 1.02um. Which is giving symmatrical Tphl and Tphl. And I am going for that in Layout.


### Output of CP1_DFF (SPICE): (Using INVX1 as load)
<!-- Has syntax as XDFF D CLK vdd vss Q DFXTN -->

Initial Transient Solution:
Node                                   Voltage
vdd                                        1.8
d                                            0
clk                                        1.8
xdft.clk_b                         1.12952e-07
xdft.d_b                                   1.8
xdft.xdlatch_a.a                           1.8
xdft.q_a                           3.84913e-07
xdft.xdlatch_a.b                           1.8
xdft.xdlatch_b.a                   1.34347e-07
xdft.q_b                                   1.8
xdft.xdlatch_b.b                   1.25335e-07
q                                  3.82287e-07
load_out                                   1.8
vclk#branch                                  0
vd#branch                                    0
vdd#branch                        -1.02226e-09

Measurements for Transient Analysis
trise               =  1.85586e-11 targ=  3.29090e-10 trig=  3.10532e-10  (= 18.55 ps)
tfall               =  1.78465e-11 targ=  1.03336e-08 trig=  1.03158e-08  (= 17.84 ps)

### Output of CP1_NAND3 (SPICE): (Using INVX1 as load)
<!-- Has syntax as XNAND vdd a b c vss out NAND -->

Initial Transient Solution:
Node                                   Voltage
vdd                                        1.8
in                                           0
xnand.abar                                 1.8
out                                 1.6756e-06
xnand.ab                           1.11707e-06
xnand.bc                           5.58533e-07
load_out                                   1.8
v_a#branch                                   0
vdd#branch                        -1.63817e-09

Measurements for Transient Analysis

trise               =  2.20878e-11 targ=  1.07030e-09 trig=  1.04821e-09  (= 22.08 ps)
tfall               =  2.21869e-11 targ=  4.07755e-09 trig=  4.05536e-09  (= 22.18 ps)