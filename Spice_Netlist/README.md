Output of CP1_DFF: (Using INVX1 as load)
Initial Transient Solution:
Node                                   Voltage
vdd                                        1.8
in                                           0
clk                                        1.8
clk_bar                            1.12952e-07
a_out                                      1.8
b_out                                      1.8
c_out                              1.18756e-07
d_out                                      1.8
f_out                              1.34673e-07
g_out                                      1.8
h_out                              1.25498e-07
q                                  1.12952e-07
load_out                                   1.8

Measurements for Transient Analysis:
tr                  =  2.60042e-11 targ=  3.38792e-10 trig=  3.12787e-10
tf                  =  2.50759e-11 targ=  1.03486e-08 trig=  1.03236e-08

Using C=0.5fF as load we get:
tr                  =  1.91878e-11 targ=  3.25996e-10 trig=  3.06808e-10
tf                  =  1.64744e-11 targ=  1.03361e-08 trig=  1.03196e-08

After making Inverter G as X2 (using INVX1 load):
tr                  =  23.7 ps
tf                  =  23.3 ps