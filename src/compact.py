"""Compact encoding + QAOA for Instant Insanity.

A cube in a tower puts one opposite-face pair on the front/back axis and a
different pair on left/right, so it has 3 * 2 = 6 legal choices. Six choices fit
in 3 qubits (8 states), so we map all 8 states onto the 6 and two states end up
as duplicates. Every bitstring then decodes to a legal cube, which means no
penalty terms and a plain X mixer.

Qubit 3*c + j is bit j of cube c. Qiskit counts keys put qubit 0 on the right.
"""

import itertools

import numpy as np

CHOICES = list(itertools.permutations(range(3), 2))   # (front/back pair, left/right pair)

# The 8 states -> 6 choices map. Which two states are duplicates is a free
# choice, and it changes how many Z strings the Hamiltonian needs. ALIAS below
# is the cheapest of the 720 * 36 maps we tried: 460 CX per cost layer instead
# of 1216 for the obvious one. See cheapest_alias().
ALIAS = [(0, 2), (1, 2), (0, 1), (2, 1), (2, 0), (1, 0), (2, 1), (2, 1)]
NAIVE_ALIAS = CHOICES + [CHOICES[0], CHOICES[1]]


def decode(bits, n_cubes, alias=ALIAS):
    """Bitstring integer -> one (front/back pair, left/right pair) per cube."""
    return [alias[(bits >> (3 * c)) & 7] for c in range(n_cubes)]


def _counts(cubes, alias):
    """T[side][colour][cube][state] = how many faces of that colour the cube shows."""
    letters = sorted({ch for cube in cubes for pair in cube for ch in pair})
    T = np.zeros((2, len(letters), len(cubes), 8), dtype=np.int64)
    for c, cube in enumerate(cubes):
        for i in range(8):
            for side in (0, 1):
                for k, colour in enumerate(letters):
                    T[side, k, c, i] = cube[alias[i][side]].count(colour)
    return T


def all_costs(cubes, alias=ALIAS):
    """cost = sum over axes, colours of (d_k - 2)^2, for every bitstring at once."""
    n = len(cubes)
    T = _counts(cubes, alias)
    idx = np.arange(8 ** n, dtype=np.int64)
    cost = np.zeros(8 ** n, dtype=np.int32)
    for side in (0, 1):
        for k in range(T.shape[1]):
            d = np.zeros(8 ** n, dtype=np.int32)
            for c in range(n):
                d += T[side, k, c][(idx >> (3 * c)) & 7].astype(np.int32)
            cost += (d - 2) ** 2
    return cost


def cost_of(cubes, bits, alias=ALIAS):
    """The same cost for one bitstring, written straight from the definition.

    Deliberately slow and obvious: this is what all_costs is checked against.
    """
    letters = sorted({ch for cube in cubes for pair in cube for ch in pair})
    choice = decode(bits, len(cubes), alias)
    total = 0
    for side in (0, 1):
        for colour in letters:
            d = sum(cubes[c][choice[c][side]].count(colour) for c in range(len(cubes)))
            total += (d - 2) ** 2
    return total


def hamiltonian(cubes, alias=ALIAS):
    """The cost as {Z-mask: coefficient}; bit q of the mask means a Z on qubit q.

    Each cube's colour count is a function of its own 3 qubits, so a
    Walsh-Hadamard transform writes it as a polynomial in those 3 Z operators.
    Squaring (d_k - 2) multiplies those polynomials, and a product of Z strings
    is the Z string on the XOR of their masks.
    """
    T = _counts(cubes, alias)
    H = {}
    for side in (0, 1):
        for k in range(T.shape[1]):
            poly = {0: -2.0}                      # the "- 2" in (d_k - 2)
            for c in range(len(cubes)):
                f = T[side, k, c]
                for m in range(8):
                    w = sum(f[i] * (-1) ** bin(i & m).count("1") for i in range(8)) / 8
                    if abs(w) > 1e-12:
                        g = m << (3 * c)
                        poly[g] = poly.get(g, 0.0) + w
            for a, wa in poly.items():            # square it
                for b, wb in poly.items():
                    H[a ^ b] = H.get(a ^ b, 0.0) + wa * wb
    return {m: w for m, w in H.items() if abs(w) > 1e-9}


def diagonal(terms, n_qubits):
    """Evaluate the Z-string Hamiltonian on every bitstring."""
    idx = np.arange(2 ** n_qubits, dtype=np.int64)
    out = np.zeros(2 ** n_qubits)
    for mask, w in terms.items():
        v, parity = idx & mask, np.zeros(len(idx), dtype=np.int64)
        while v.any():
            parity ^= v & 1
            v >>= 1
        out += w * (1 - 2 * parity)
    return out


def cx_count(terms):
    """CX gates one cost layer needs: a weight-w Z string costs 2(w-1)."""
    return sum(2 * (bin(m).count("1") - 1) for m in terms if bin(m).count("1") >= 2)


def cheapest_alias(cubes):
    """Try every ordering of the 6 choices and every filling of the 2 spares."""
    best = None
    for perm in itertools.permutations(range(6)):
        base = [CHOICES[i] for i in perm]
        for dup in itertools.product(range(6), repeat=2):
            alias = base + [CHOICES[perm[dup[0]]], CHOICES[perm[dup[1]]]]
            t = hamiltonian(cubes, alias)
            score = (cx_count(t), len(t))
            if best is None or score < best[0]:
                best = (score, alias, t)
    return best[1], best[2]


# ----------------------------------------------------------------- simulation

def qaoa_probs(diag, n_qubits, gammas, betas):
    """Exact QAOA output probabilities. Hand-written because the angle search
    calls this thousands of times; checked against Qiskit in the notebook."""
    state = np.full(2 ** n_qubits, 2 ** (-n_qubits / 2), dtype=np.complex128)
    for g, b in zip(gammas, betas):
        state *= np.exp(-1j * g * diag)                     # cost layer
        c, s = np.cos(b), -1j * np.sin(b)                   # X mixer
        for j in range(n_qubits):
            v = state.reshape(-1, 2, 2 ** j)
            a0, a1 = v[:, 0, :].copy(), v[:, 1, :]
            v[:, 0, :] = c * a0 + s * a1
            v[:, 1, :] = s * a0 + c * a1
    return np.abs(state) ** 2


def qaoa_circuit(terms, n_qubits, gammas, betas):
    """|+>^n, then per layer exp(-i gamma H) and exp(-i beta sum X)."""
    from qiskit import QuantumCircuit

    qc = QuantumCircuit(n_qubits)
    qc.h(range(n_qubits))
    order = sorted((m for m in terms if m), key=lambda m: -bin(m).count("1"))
    for g, b in zip(gammas, betas):
        for mask in order:
            qs = [q for q in range(n_qubits) if (mask >> q) & 1]
            angle = 2 * g * terms[mask]
            if len(qs) == 1:
                qc.rz(angle, qs[0])
            else:
                for x, y in zip(qs[:-1], qs[1:]):
                    qc.cx(x, y)
                qc.rz(angle, qs[-1])
                for x, y in reversed(list(zip(qs[:-1], qs[1:]))):
                    qc.cx(x, y)
        qc.rx(2 * b, range(n_qubits))
    return qc


# ----------------------------------------------------------------- optimiser

def _cvar(probs, cost, alpha):
    """Mean cost of the best alpha-fraction of the distribution.

    Minimising the plain average chases the bulk of bad bitstrings. CVaR looks
    only at the good tail, which is where the answers are.
    """
    order = np.argsort(cost)
    p, c = probs[order], cost[order]
    cum = np.cumsum(p)
    k = min(int(np.searchsorted(cum, alpha) + 1), len(p))
    w = p[:k].copy()
    over = w.sum() - alpha
    if over > 0:
        w[k - 1] -= over
    return float(w @ c[:k] / max(w.sum(), 1e-15))


def grow_angles(diag, cost, n_qubits, p_max, alpha=0.3, seed=7,
                restarts=8, maxiter=600, verbose=True):
    """Solve p=1, stretch those angles into p=2, re-optimise, and so on.

    Optimising all 2p angles from a random start stalls; every layer here starts
    from the previous layer's answer.
    """
    from scipy.optimize import minimize

    rng = np.random.default_rng(seed)
    wins = np.flatnonzero(cost == 0)
    baseline = len(wins) / len(cost)

    def objective(angles):
        p = len(angles) // 2
        probs = qaoa_probs(diag, n_qubits, angles[:p], angles[p:])
        return _cvar(probs, cost, alpha) if alpha < 1 else float(probs @ cost)

    best, best_val = None, None
    for _ in range(restarts):
        x0 = np.concatenate([rng.uniform(0, 0.8, 1), rng.uniform(0, np.pi / 2, 1)])
        res = minimize(objective, x0, method="COBYLA", options={"maxiter": maxiter})
        if best_val is None or res.fun < best_val:
            best, best_val = res.x.copy(), res.fun

    trace, x = [], best
    for p in range(1, p_max + 1):
        if p > 1:
            g, b = x[:p - 1], x[p - 1:]
            x0 = np.concatenate([np.interp(np.linspace(0, 1, p), np.linspace(0, 1, p - 1), g),
                                 np.interp(np.linspace(0, 1, p), np.linspace(0, 1, p - 1), b)])
            res = minimize(objective, x0, method="COBYLA", options={"maxiter": maxiter})
            if res.fun > objective(x0):          # retry from a nudged start
                res2 = minimize(objective, x0 + rng.normal(0, 0.05, len(x0)),
                                method="COBYLA", options={"maxiter": maxiter})
                res = res2 if res2.fun < res.fun else res
            x = res.x
        probs = qaoa_probs(diag, n_qubits, x[:p], x[p:])
        entry = {"p": p, "p_solved": float(probs[wins].sum()),
                 "baseline": baseline, "angles": x.tolist()}
        trace.append(entry)
        if verbose:
            print(f"  p={p:>2}  P(solved) {entry['p_solved']:7.3%}   "
                  f"x{entry['p_solved'] / baseline:6.0f} over random")
    return trace


# ---------------------------------------------------------------- submitting
# Adapted from resources/helpers.py in the challenge repo (Apache-2.0), inlined
# here so this notebook needs only src/.

def prepare(circuit):
    """Add a marker qubit fixed at 1, measure everything, transpile to basic gates.

    Providers do not all order bits the same way. The marker is the last qubit,
    so where it lands in a result key tells us which end holds the last qubit.
    """
    from qiskit import QuantumCircuit, transpile

    n = circuit.num_qubits
    qc = QuantumCircuit(n + 1)
    qc.compose(circuit, range(n), inplace=True)
    qc.x(n)
    qc.measure_all()
    return transpile(qc, basis_gates=["rz", "sx", "x", "cx"], optimization_level=1)


def strip_marker(raw):
    """Drop the marker bit and return counts in Qiskit order (qubit 0 on the right)."""
    if all(key[0] == "1" for key in raw):
        return {key[1:]: n for key, n in raw.items()}
    if all(key[-1] == "1" for key in raw):
        return {key[:-1][::-1]: n for key, n in raw.items()}
    raise ValueError("marker bit not found; was the circuit built with prepare()?")
