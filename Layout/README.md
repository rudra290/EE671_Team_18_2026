## Layouts

- [ ] Inverter
- [x] Transmission gate
- [ ] Dflipflop
- [ ] Nand3b

### Constrains

- Standard cell height should be 2.72um. Which is meassured between middle of Metal layer of Vdd and Vss.
- I have made Transmission Gate. Observed that I could minimize height of metal layer to 0.24um. So all cells should follow that.

|Cell|Label structure|
|----|------|
|Tranmission Gate| Vdd enb en in out Vss|
|Inverter_X1| Vdd vin vout Vss|
