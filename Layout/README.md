## Layouts

- [x] Inverter
- [x] Transmission gate
- [x] Dflipflop
- [ ] Nand3b

### Constrains

- Standard cell height should be 2.72um. Which is meassured between middle of Metal layer of Vdd and Vss.
- I have made Transmission Gate. Observed that I could minimize height of metal layer to 0.48um. So all cells should follow that.

|Cell|Label structure|Width|
|----|------|------|
|Tranmission Gate|in n_in out p_in vdd vss|Wp=0.98um, Wn=0.42um|
|Inverter_X1|in vdd vss out|Wp=1.26um, Wn=0.42um|
|invx1|in vdd vss out|Wp=1.26um, Wn=0.42um|
|Inverter_X2|in vdd vss out|Wp=2.52um, Wn=0.78um|
|latch|D CLK CLK_B vdd vss Q||
|dfxtn|D CLK vdd vss Q||