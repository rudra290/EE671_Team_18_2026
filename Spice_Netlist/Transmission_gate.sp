* Sky130 Inverter PMOS Width Sweep (Fixed numparam scoping)
.title Sky130 Wp Sizing Sweep

.lib /foss/pdks/sky130A/libs.tech/ngspice/sky130.lib.spice tt

* --- Top-Level Default Parameters ---
.param Wp_val = 1.00
.param Wn_val = 0.42
.param L_val  = 0.15

* --- Correctly Parameterized Subcircuit ---
* Default parameters MUST be declared on the .subckt line
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

* --- DUT & Load Instances ---
* Parameters are explicitly passed into the instance
X1 vin   vdd 0 vout1 INVX1 Wp='Wp_val' Wn='Wn_val' L='L_val'
X2 vout1 vdd 0 vout2 INVX1 Wp='Wp_val' Wn='Wn_val' L='L_val'
Cload vout1 0 5fF

* --- Supplies & Input Signal ---
Vdd vdd 0 DC 1.8
V1  vin 0 PULSE(0 1.8 50ps 20ps 20ps 0.4ns 0.8ns)

* --- Transient Analysis ---
.tran 0.2ps 1.6ns

* --- Control Block with Parameter Sweep ---
.control
  let wp_start = 0.42
  let wp_stop  = 1.60
  let wp_step  = 0.01
  let curr_wp  = wp_start

  let n_steps  = (wp_stop - wp_start) / wp_step + 1
  let vec_wp   = vector(n_steps)
  let vec_tplh = vector(n_steps)
  let vec_tphl = vector(n_steps)
  let vec_diff = vector(n_steps)

  let idx = 0
  while curr_wp <= wp_stop
    * Update top-level parameter
    alterparam Wp_val = $&curr_wp
    reset
    run

    * Measure 50% propagation delays
    meas tran tplh TRIG v(vin) VAL=0.9 FALL=1 TARG v(vout1) VAL=0.9 RISE=1
    meas tran tphl TRIG v(vin) VAL=0.9 RISE=1 TARG v(vout1) VAL=0.9 FALL=1

    * Store data points
    let vec_wp[idx]   = curr_wp
    let vec_tplh[idx] = tplh
    let vec_tphl[idx] = tphl
    let vec_diff[idx] = abs(tplh - tphl)

    let curr_wp = curr_wp + wp_step
    let idx = idx + 1
  end

  * Display Results
  plot vec_tplh vs vec_wp vec_tphl vs vec_wp title "Delay (tplh vs tphl) vs PMOS Width" xlabel "Wp (um)" ylabel "Delay (s)"
  plot vec_diff vs vec_wp title "Absolute Delay Difference |tplh - tphl|" xlabel "Wp (um)" ylabel "Skew (s)"

  print vec_wp vec_tplh vec_tphl vec_diff
.endc

.end
