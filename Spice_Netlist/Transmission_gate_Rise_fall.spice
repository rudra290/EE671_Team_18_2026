* Sky130 Inverter Rise/Fall Time Optimization Testbench
.title Sky130 Slew Rate Matching Sweep

.lib /foss/pdks/sky130A/libs.tech/ngspice/sky130.lib.spice tt

* --- Top-Level Parameters ---
.param Wp_val = 1.00
.param Wn_val = 0.42
.param L_val  = 0.15

* --- Parameterized Inverter Subcircuit ---
.subckt INVX1 vin vdd vss vout Wp=1.00 Wn=0.42 L=0.15
xp01 vout vin vdd vdd sky130_fd_pr__pfet_01v8
+ w='Wp' l='L' nf=1 mult=1
+ as='Wp * 2 * L' ad='Wp * 2 * L'
+ ps='2 * (Wp + 2 * L)' pd='2 * (Wp + 2 * L)'

xn02 vout vin vss vss sky130_fd_pr__nfet_01v8
+ w='Wn' l='L' nf=1 mult=1
+ as='Wn * 2 * L' ad='Wn * 2 * L'
+ ps='2 * (Wn + 2 * L)' pd='2 * (Wn + 2 * L)'
.ends INVX1

* --- DUT & Realistic Load ---
X1 vin   vdd 0 vout1 INVX1 Wp='Wp_val' Wn='Wn_val' L='L_val'
X2 vout1 vdd 0 vout2 INVX1 Wp='Wp_val' Wn='Wn_val' L='L_val'
Cload vout1 0 5fF

* --- Sources ---
Vdd vdd 0 DC 1.8
* Clean pulse allowing full rail-to-rail transitions
V1  vin 0 PULSE(0 1.8 100ps 20ps 20ps 1.0ns 2.0ns)

* --- Transient Analysis ---
.tran 0.2ps 2.5ns

* --- Slew Rate Sweep Loop ---
.control
  let wp_start = 0.42
  let wp_stop  = 1.80
  let wp_step  = 0.02
  let curr_wp  = wp_start

  let n_steps  = (wp_stop - wp_start) / wp_step + 1
  let vec_wp   = vector(n_steps)
  let vec_tr   = vector(n_steps)
  let vec_tf   = vector(n_steps)
  let vec_diff = vector(n_steps)

  let idx = 0
  while curr_wp <= wp_stop
    alterparam Wp_val = $&curr_wp
    reset
    run

    * 10% to 90% (0.18V to 1.62V) Slew Measurements
    meas tran tr TRIG v(vout1) VAL=0.36 RISE=1 TARG v(vout1) VAL=1.44 RISE=1
    meas tran tf TRIG v(vout1) VAL=1.44 FALL=1 TARG v(vout1) VAL=0.36 FALL=1

    * Save vector metrics
    let vec_wp[idx]   = curr_wp
    let vec_tr[idx]   = tr
    let vec_tf[idx]   = tf
    let vec_diff[idx] = abs(tr - tf)

    let curr_wp = curr_wp + wp_step
    let idx = idx + 1
  end

  * Plot Slew Curves
  plot vec_tr vs vec_wp vec_tf vs vec_wp title "Rise Time (tr) vs Fall Time (tf) [10%-90%]" xlabel "Wp (um)" ylabel "Transition Time (s)"
  plot vec_diff vs vec_wp title "Slew Rate Mismatch |tr - tf|" xlabel "Wp (um)" ylabel "Difference (s)"

  print vec_wp vec_tr vec_tf vec_diff
.endc

.end
