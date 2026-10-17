# Instant Insanity on 12 qubits

**Qiskit Fall Fest Connecticut 2026 · qBraid challenge · UConn Quantum Computing**

**Team:** Daksh Goswami, Rueben, Ishal
**Level reached:** Core + Bonus

## What we did

Four cubes, four colours; stack them so each side of the tower shows all four
colours once. 331,776 stackings, one works.

In a tower a cube puts one opposite-face pair on the front/back axis and a
*different* pair on left/right, so it has only **6 legal choices**. Six fit in
**3 qubits** (8 states), so we map all 8 states onto the 6 and two are
duplicates. Every bitstring then decodes to a legal cube, which means **no
penalty terms and a plain X mixer** — the starter's one-hot layout needs both.
That halves the register: **12 qubits instead of 24**, 3N instead of 6N.

The cost is `sum over both axes, over colours, of (d_k - 2)^2`, where `d_k`
counts how many chosen pairs show colour k. It is a sum of squares, so it is
zero exactly when every colour has degree 2 — exactly a solved tower.

Two things we found: **which** two states are the duplicates is free to choose,
and searching all 720 x 36 labellings cut the cost layer from **1216 to 460 CX**;
and **growing the angles layer by layer** (solve p=1, warm-start p=2, ...) took
us from ~4% to 44.6%, where optimising all 2p angles from a
random start stalls.

## Results

| Puzzle (N cubes) | Encoding | Device | Qubits | Two-qubit gates | Depth | Shots | P(correct tower) | Random-guess baseline | qBraid job ID |
|---|---|---|---|---|---|---|---|---|---|
| 4 | compact 3N, p=12 | aws:aws:sim:sv1 | 12 | 4704 | 4361 | 2000 | **44.20%** measured | 0.1465% | `aws:aws:sim:sv1-0f30-qjob-6ad3893538127b44c71b9b8b` |
| 5 | compact 3N, p=10 | local Aer | 15 | 7620 | 6538 | 2000 | 13.37% exact | 0.0366% | n/a (local) |
| 6 | compact 3N, p=10 | local Aer | 18 | 10780 | 7803 | 2000 | 8.43% exact | 0.0069% | n/a (local) |
| 7 | compact 3N, p=8 | local Aer | 21 | 11440 | 9366 | 2000 | 1.04% exact | 0.0002% | n/a (local) |

Gates and depth after `transpile(qc, basis_gates=["rz","sx","x","cx"], optimization_level=1)`.
P(correct tower) is the fraction of shots decoding to a tower the starter's own
`solves()` accepts. On SV1 we measured **884/2000 = 44.20%** against a
0.146% baseline, a **302x** lift; the exact
simulation predicted 44.62%, which is within sampling error.

**Cost:** one SV1 job, **0.375 qBraid credits**. We tuned the angles and debugged
on the local Aer simulator and submitted to SV1 once, so that single job is the
whole hardware spend. The N=5..7 rows ran locally and cost nothing.

**Versus brute force:** enumerating all 331,776 stackings and checking each takes
well under a second in the notebook, so classical search wins outright at this
size. Versus random guessing inside our encoding, the circuit is ~302x better.

Bonus puzzles use the starter's `make_puzzle(n, seed)` with seeds
N=5:16, N=6:86, N=7:68. The lift over random
grows with N (5457x at N=7) but the absolute success rate falls — we
report both.

**We are not claiming a quantum speedup.** The general N-cube problem is
NP-complete (Robertson & Munro, 1978) and nothing here changes that.

## How we know it is right

`solution.ipynb` checks, before any quantum run: the Hamiltonian equals the
classical cost on **every** bitstring (difference exactly 0.0e+00); two
independent cost implementations agree; the decoder is correct in **both**
directions against the starter's `solves()`; and the fast simulator we optimise
with matches Qiskit's `Statevector` to 1e-15. Every reported tower was rebuilt
and passed to the classical checker — a low energy was never treated as proof.

## How to run it

In qBraid Lab, open `solution.ipynb` and run all cells. The first cell installs
anything missing, credentials load automatically, and no API key goes in the
notebook. Without credentials the SV1 cell falls back to local Aer and says so.
Seeds fixed at `SEED = 7`. No packages beyond the challenge's own
`requirements.txt` are needed.

## AI use

We used **Claude (Claude Code)** as a coding agent, per `AGENTS.md`. Two things
to be straight about. First, the compact 3-qubits-per-cube encoding is listed in
`AGENTS.md` under "Useful directions" — we did not invent the idea, we built it,
searched the state labelling, and measured what it cost. Second, `AGENTS.md` says
an agent should help the team write `submit_job` rather than paste a finished
version; ours wrote it, and we read it against `resources/02_qbraid_sdk.ipynb`
before running it. The agent derived the cost as Z operators and wrote the
labelling search, the angle growth, the checks and the scaling study. We kept it honest by
verifying every encoding change against brute force **before** any quantum run,
testing the decoder in both directions, and checking its fast simulator against
Qiskit. We caught it twice: once reporting a stale baseline number from an older
version of the code, and once crediting a CVaR objective for the improvement —
an A/B with one parameter changed showed the plain average cost is slightly
better (50.85% vs 44.62% at p=12) and that layer-by-layer
growth was the real win. We report the CVaR configuration because that is what
we actually ran on SV1.

The puzzle and `make_puzzle`, `count_answers`, `orientations`, `solves` in
`src/puzzle.py` are from the challenge repo, used unchanged as our independent
checker; `prepare` and `strip_marker` in `src/compact.py` are adapted from its
`resources/helpers.py`. Apache-2.0.
