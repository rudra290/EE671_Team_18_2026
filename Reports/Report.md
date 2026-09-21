---
title: "Cource Project 1"
subtitle: "Final Capstone Project Report"
institute: "Indian Institute of Technology Bombay"
institution: "Department of Electrical Engineering"
course: "VLSI Design"
course-code: "EE617"
instructor: "Dr. Laxmeesha Somappa"

team-number: "Team 18"
members:
  - name: "Patel Rudra Mayurkumar"
    roll: "26M1227"
  - name: "Harshbhai Maheshbhai Vaghadia"
    roll: "26M1190"
  - name: "Woodrow Gonsalves"
    roll: "26M1158"
  - name: "Giridhara Datta G"
    roll: "26M1201"

# Document Controls
documentclass: report
toc: true
lot: true
lof: true
number-by-section: true
colorlinks: true
---

# Introduction

This project details the design and deployment of a fault-tolerant storage system.

## Performance Metrics

| Node ID | Sync Latency | Heartbeat | Status |
| :---: | :---: | :---: | :---: |
| **Node-01** | 4.2 ms | 1s | Active |
| **Node-02** | 3.8 ms | 1s | Active |
| **Node-03** | 8.1 ms | 2s | Degraded |

: Cluster Node Synchronization {#tbl:nodes}

\begin{equation}\label{eq:consensus}
Q = \left\lfloor \frac{N}{2} \right\rfloor + 1
\end{equation}

DRC Clean Layout's:

<div align="center">
Inverter X1 Layout
</div>

![Inverter X1 Layout](./Layout_Screenshots/Inverter_X1_Layout.png)

<div align="center">
Inverter X2 Layout
</div>

![Inverter X2 Layout](./Layout_Screenshots/Inverter_X2_Layout.png)

<div align="center">
Transmission Gate Layout
</div>

![Transmission Gate Layout](./Layout_Screenshots/Transmission_Gate_Layout.png)

<div align="center">
Masked Latch Layout
</div>

![Masked Latch Layout](./Layout_Screenshots/Latch_Masked_Layout.png)

<div align="center">
Latch Layout
</div>

![Latch Layout](./Layout_Screenshots/Latch_Layout.png)

<div align="center">
Masked Negative Edge triggered D Flip Flop Layout
</div>

![Masked DFF Layout](./Layout_Screenshots/DFF_Masked_Layout.png)

<div align="center">
Negative Edge triggered D Flip Flop Layout
</div>

![DFF Layout](./Layout_Screenshots/DFF_Layout.png)

<div align="center">
Inverter X1_25 Layout
</div>

![Inverter X1_25 Layout](./Layout_Screenshots/Inverter_X1_25_Layout.png)

<div align="center">
NAND MOSFETs' Layout
</div>

![NAND MOSFET Layout](./Layout_Screenshots/NAND3_Layout.png)

<div align="center">
NAND3b Masked Layout
</div>

![NAND3b Masked Layout](./Layout_Screenshots/nand3b_Masked_Layout.png)

<div align="center">
NAND3b Layout
</div>

![NAND3b Layout](./Layout_Screenshots/nand3b_Layout.png)