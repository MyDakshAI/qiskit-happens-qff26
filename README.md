# Instant Insanity Using QAOA

**Qiskit Fall Fest Connecticut 2026 — UConn**  
**Team:** Qiskit Happens · **Members:** Eshal, Reuben, Daksh  

## Our project

Our challenge was to stack four colored cubes so that every side of the tower shows each color exactly once. We wanted to try solving it with **QAOA (Quantum Approximate Optimization Algorithm)**. Since this was our first quantum optimization project, we started with a classical solution to check our results.

## What we did

We first checked all **331,776** possible tower orientations and found **8** that work. Next, we represented each cube using **3 qubits** for its choices of opposite face pairs. This made the full puzzle use **12 logical qubits**, compared with 24 in the starter's one-hot encoding.

We made a **cost function** that gives correct arrangements a score of zero, then turned it into a **Hamiltonian** for QAOA. The quantum circuit alternates cost and mixer operations, and a classical optimizer adjusts the angles. We used **CVaR** to focus on low-cost answers and tested up to 12 QAOA layers.

To check our work, we compared the Hamiltonian with the classical cost for all **4,096** bitstrings, verified the solutions with `solves()`, and compared our custom simulator with Qiskit's `Statevector`.

## Results

| Puzzle (N cubes) | Encoding | Device | Qubits | Two-qubit gates (after transpiling) | Depth | Shots | P(correct tower) | Random-guess baseline | qBraid job ID |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| 4 | Compact QAOA, p=12 | Local Aer | 13* | 4,704 | 4,362 | 2,000 | **45.30% measured** | 0.1465% | N/A |
| 5 | Compact QAOA, p=10 | Exact local simulation | 15 | Not reported | Not reported | 0 (exact) | **13.37% predicted** | 0.0366% | N/A |
| 6 | Compact QAOA, p=10 | Exact local simulation | 18 | Not reported | Not reported | 0 (exact) | **8.43% predicted** | 0.00687% | N/A |
| 7 | Compact QAOA, p=8 | Exact local simulation | 21 | Not reported | Not reported | 0 (exact) | **1.04% predicted** | 0.000191% | N/A |

*The four-cube circuit uses 12 logical qubits, plus 1 marker qubit for measurement. Its transpiled depth without the marker is 4,361; the exact predicted success rate is 44.62%.*

**AWS status:** Our full-puzzle SV1 attempt returned `ResourceNotFoundError`; the 45.30% measurement is from **local Aer**, not AWS. We previously ran a **separate front/back-only warm-up** on SV1: `aws:aws:sim:sv1-8517-qjob-6ad3987338127b44c71b9e52` (not a full-tower result).

**Bonus seeds:** N=5: `16`; N=6: `86`; N=7: `68`. Bonus probabilities are exact statevector predictions, not shot measurements. Their notebook CX counts are **per cost layer**, not full transpiled counts.

## What we learned

Our compact approach used fewer qubits and made correct answers much more likely than random sampling. **We are not claiming a quantum speedup**, since classical brute force solves this small puzzle quickly. Next, we would try reducing circuit depth and getting a successful full-puzzle SV1 run.

## AI use

We used **ChatGPT and Claude** to understand QAOA, review/debug code, and help write this README. We checked its suggestions using classical brute force, `solves()`, and Qiskit's statevector simulator.
