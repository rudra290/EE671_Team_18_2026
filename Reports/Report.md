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
