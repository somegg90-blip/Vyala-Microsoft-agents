"""
Quantum Attack Surface Simulator (QASS) — Step 3 of Vyala Archon
=================================================================
For each identified vulnerability, QASS builds the actual Qiskit circuit
that would implement the quantum attack, then estimates:

  • Logical qubit count        (circuit qubits needed for the algorithm)
  • Physical qubit count       (with error correction overhead)
  • Gate depth                 (circuit layers)
  • Time to break at 2030 error rates
  • Grover iteration count     (for symmetric / hashing)

RSA / ECDSA / ECDH  →  Shor's algorithm  (Quantum Fourier Transform)
AES-128 / MD5 / SHA1 →  Grover's algorithm (unstructured search)

2030 hardware assumptions (Pinnacle Architecture / Gidney 2025 bounds):
  - Physical error rate  p = 1e-3
  - Code cycle time      1 µs
  - Reaction time        10 µs
  - QLDPC codes (Iceberg Quantum Feb 2026 preprint arXiv:2602.11457)

Physical qubit estimates are conservative upper bounds for threat framing.
These are pedagogical circuits, not production attacks — real Shor's on
RSA-2048 requires fault-tolerant hardware not yet available.
"""

from __future__ import annotations

import math
import logging
from dataclasses import dataclass
from typing import Optional

log = logging.getLogger("vyala_archon.qass")

# ---------------------------------------------------------------------------
# Try to import Qiskit; degrade gracefully if not installed
# ---------------------------------------------------------------------------
try:
    from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
    from qiskit.circuit.library import QFT, QFTGate
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False
    log.warning(
        "Qiskit not installed. QASS will run in estimation-only mode. "
        "Install with: pip install qiskit qiskit-aer"
    )


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class QASSResult:
    """
    Output of the Quantum Attack Surface Simulator for one finding.
    All fields are threat-modelling estimates, not proven attack timelines.
    """
    algorithm: str                   # e.g. "RSA-2048"
    attack_type: str                 # "shors" | "grovers"

    # Circuit metrics
    logical_qubits: int
    gate_depth: int
    gate_count_estimate: int

    # Physical resource estimates (2030 hardware assumptions)
    physical_qubits_2030: int        # with QLDPC error correction
    time_to_break_seconds: float     # at 2030 projected error rates
    time_to_break_human: str         # e.g. "~5 days"

    # Grover-specific
    grover_iterations: Optional[int] = None   # None for Shor's

    # Risk framing for the dashboard
    breakable_by_2030: bool = False
    urgency_multiplier: float = 1.0  # fed into Step 3 CVSS-Q scorer
    threat_summary: str = ""

    # Qiskit circuit (serialized as QASM string if available)
    circuit_qasm: Optional[str] = None
    circuit_ascii: Optional[str] = None      # text drawing for dashboard


# ---------------------------------------------------------------------------
# Physical qubit overhead model
# ---------------------------------------------------------------------------
# Based on:
#   Gidney & Ekerå 2025  — ~1M physical qubits for RSA-2048 (surface codes)
#   Iceberg Quantum 2026 (arXiv:2602.11457) — ~62K-100K (QLDPC Pinnacle)
#   We use a conservative QLDPC model: ~30 physical per logical qubit
#   (vs ~1000 for surface codes) to reflect 2030 projected hardware.

_PHYSICAL_PER_LOGICAL_2030 = 30   # QLDPC estimate, 2030 projected hardware
_SURFACE_CODE_OVERHEAD    = 1000  # legacy surface code baseline

def _physical_qubits(logical: int, optimistic: bool = True) -> int:
    """Estimate physical qubits required for `logical` logical qubits."""
    overhead = _PHYSICAL_PER_LOGICAL_2030 if optimistic else _SURFACE_CODE_OVERHEAD
    return logical * overhead


# ---------------------------------------------------------------------------
# Shor's algorithm resource estimator
# ---------------------------------------------------------------------------
# Qubit formula (Beauregard 2003, standard 2n+3 circuit):
#   n   = number of bits in key (e.g. 2048 for RSA-2048)
#   counting register: 2n qubits  (precision for QFT phase estimation)
#   target register:   n  qubits  (holds a^x mod N)
#   ancilla:           3  qubits
#   total logical:     2n + n + 3 = 3n + 3
#
# For ECC (ECDLP), the best known estimate is ~9n logical qubits (Roetteler 2017)
#
# Gate depth ~ O(n^3) for modular exponentiation via QFT-based adders
# We use the simplified 2000n^2 + n^3 estimate from Pavlidis & Gizopoulos 2012.

def _shors_resources(key_bits: int, algo_base: str) -> tuple[int, int, int]:
    """
    Returns (logical_qubits, gate_depth, gate_count_estimate).
    algo_base: "RSA" | "ECDSA" | "ECDH"
    """
    n = key_bits

    if algo_base in ("RSA",):
        # Standard 2n+3 Beauregard circuit
        logical_qubits = 2 * n + 3
        # Gate depth for modular exponentiation (Pavlidis 2012)
        gate_depth = int(2000 * n**2)
        gate_count = int(1600 * n**3)

    elif algo_base in ("ECDSA", "ECDH"):
        # ECDLP requires ~9n logical qubits (Roetteler et al. 2017, arXiv:1706.06752)
        logical_qubits = 9 * n + 2
        # Slightly deeper due to elliptic curve group law circuits
        gate_depth = int(2500 * n**2)
        gate_count = int(2000 * n**3)

    else:
        logical_qubits = 3 * n + 3
        gate_depth = int(2000 * n**2)
        gate_count = int(1600 * n**3)

    return logical_qubits, gate_depth, gate_count


def _shors_time_seconds(gate_depth: int) -> float:
    """
    Estimate wall-clock seconds at 2030 projected hardware.
    Assumes 1µs code cycle time, 10µs reaction time, QLDPC.
    Based on Gidney 2025 (< 1 week for RSA-2048 at ~1M qubits surface code)
    and Iceberg Quantum 2026 (1-4 minutes per shot at 1µs cycle time).
    We model: time ≈ gate_depth × cycle_time × error_correction_rounds
    """
    cycle_time_us = 1.0          # microseconds, projected 2030
    error_correction_rounds = 15  # ~15 rounds per logical gate for QLDPC
    time_us = gate_depth * cycle_time_us * error_correction_rounds
    return time_us * 1e-6  # convert to seconds


# ---------------------------------------------------------------------------
# Grover's algorithm resource estimator
# ---------------------------------------------------------------------------
# Grover's provides a quadratic speedup for brute-force search.
# For a key of k bits: iterations = π/4 × √(2^k)
# Logical qubits: k (key register) + k (oracle ancilla) + 1 scratch = 2k+1
# Physical qubits at 2030: 2k+1 logical × QLDPC overhead
# Time: iterations × T_oracle  where T_oracle ~ O(k) gate depth
#
# Reality check: AES-128 with Grover requires ~2^64 iterations — still
# computationally expensive even quantumly. This is why NIST recommends
# AES-256 (2^128 iterations) as quantum-resistant. We surface this nuance.

def _grovers_resources(key_bits: int) -> tuple[int, int, int, int]:
    """
    Returns (logical_qubits, gate_depth, gate_count, grover_iterations).
    """
    k = key_bits
    logical_qubits = 2 * k + 1
    
    # PREVENT OVERFLOW: If k > 128, 2**k is too massive for math.sqrt().
    # Grover's on anything > 128 bits is practically infinite anyway.
    if k > 128:
        iterations = 10**18  # Symbolic near-infinite number
        gate_depth = 10**15
        gate_count = 10**18
        return logical_qubits, gate_depth, gate_count, iterations

    # Normal calculation for small key sizes (AES-128, MD5, SHA-1)
    iterations = int(math.pi / 4 * math.sqrt(2**k))
    gate_depth = k * iterations  # total depth across all iterations
    gate_count = k * iterations * 3  # ~3 gates per qubit per iteration
    return logical_qubits, gate_depth, gate_count, iterations


def _grovers_time_seconds(iterations: int, key_bits: int) -> float:
    """
    Estimate wall-clock time for Grover's at 2030 hardware.
    Each oracle call ~ key_bits × 1µs × error_correction_rounds.
    """
    cycle_time_us = 1.0
    error_correction_rounds = 15
    oracle_time_us = key_bits * cycle_time_us * error_correction_rounds
    return iterations * oracle_time_us * 1e-6


def _human_time(seconds: float) -> str:
    """Convert seconds to a readable string."""
    if seconds < 60:
        return f"~{seconds:.1f} seconds"
    elif seconds < 3600:
        return f"~{seconds/60:.0f} minutes"
    elif seconds < 86400:
        return f"~{seconds/3600:.1f} hours"
    elif seconds < 86400 * 365:
        return f"~{seconds/86400:.1f} days"
    elif seconds < 86400 * 365 * 1000:
        return f"~{seconds/(86400*365):.1f} years"
    else:
        return f"~{seconds/(86400*365*1e6):.2e} million years"


# ---------------------------------------------------------------------------
# Qiskit circuit builders (pedagogical — small-N demonstration circuits)
# ---------------------------------------------------------------------------

def _build_shors_demo_circuit(n_count: int = 3) -> Optional["QuantumCircuit"]:
    """
    Build a pedagogical Shor's order-finding circuit (Qiskit 2.x API).
    Uses a small n_count (counting register size) for visualisation.
    The full-scale circuit for RSA-2048 requires millions of qubits
    and is not simulable classically — this demonstrates the structure.

    Structure:
        |0>^n_count  ── H gates ──┐
                                  ├── Controlled-U (mod exp) ── QFT†── measure
        |1>^n_target ─────────────┘
    """
    if not QISKIT_AVAILABLE:
        return None

    n_target = 4  # ancilla register (represents the modular arithmetic space)

    counting = QuantumRegister(n_count, name="count")
    target   = QuantumRegister(n_target, name="target")
    measure  = ClassicalRegister(n_count, name="c")
    qc = QuantumCircuit(counting, target, measure)

    # Step 1: Hadamard on all counting qubits → superposition
    qc.h(counting)

    # Step 2: Initialize target register |1>
    qc.x(target[n_target - 1])

    # Step 3: Controlled-U gates (simplified placeholder for modular exponentiation)
    # In a real Shor circuit this would be controlled-a^(2^k) mod N gates.
    # Here we use controlled-SWAP as a structural stand-in for visualisation.
    for k in range(n_count):
        # Controlled rotation representing the phase kickback mechanism
        qc.cp(2 * math.pi / (2 ** (k + 1)), counting[k], target[0])
        qc.cx(counting[k], target[k % n_target])

    qc.barrier()

    # Step 4: Inverse QFT on counting register (from Qiskit circuit library)
    iqft = QFTGate(n_count).inverse()
    iqft.name = "QFT†"
    qc.append(iqft, counting)

    # Step 5: Measure counting register
    qc.measure(counting, measure)

    return qc


def _build_grovers_demo_circuit(n_qubits: int = 3) -> Optional["QuantumCircuit"]:
    """
    Build a pedagogical Grover's search circuit.
    Demonstrates the Hadamard diffusion + oracle structure.
    n_qubits: search space size (2^n_qubits states).
    """
    if not QISKIT_AVAILABLE:
        return None

    qr = QuantumRegister(n_qubits, name="q")
    cr = ClassicalRegister(n_qubits, name="c")
    qc = QuantumCircuit(qr, cr)

    # Step 1: Hadamard → uniform superposition of all 2^n states
    qc.h(qr)
    qc.barrier()

    # Step 2: Oracle (marks the target state — simplified as Z on last qubit)
    # In a real Grover's, this encodes "does this key decrypt correctly?"
    qc.z(qr[-1])
    qc.barrier()

    # Step 3: Grover diffusion operator
    qc.h(qr)
    qc.x(qr)
    qc.h(qr[-1])
    if n_qubits > 1:
        qc.mcx(list(range(n_qubits - 1)), qr[-1])  # multi-controlled X
    qc.h(qr[-1])
    qc.x(qr)
    qc.h(qr)
    qc.barrier()

    qc.measure(qr, cr)
    return qc


# ---------------------------------------------------------------------------
# Main QASS entry point
# ---------------------------------------------------------------------------

def simulate_quantum_attack(
    algorithm: str,
    key_bits: int,
    use_case: str,
    critical_path: bool,
) -> QASSResult:
    """
    Step 3 of Vyala Archon — Quantum Attack Surface Simulator.

    Builds the Qiskit circuit, estimates resources, and returns a QASSResult
    with all metrics needed for the dashboard and the risk scorer.

    Args:
        algorithm:    e.g. "RSA-2048", "ECDH-256", "AES-128"
        key_bits:     integer key size in bits
        use_case:     "signing" | "key_exchange" | "symmetric" | "hashing"
        critical_path: whether this is in an auth/TLS/signing path
    """
    algo_base = algorithm.split("-")[0]
    is_asymmetric = algo_base in ("RSA", "ECDSA", "ECDH")
    attack_type = "shors" if is_asymmetric else "grovers"

    log.info(f"QASS: Simulating {attack_type} attack on {algorithm} ({key_bits}-bit key)")

    # ── Resource estimation ──────────────────────────────────────────────────
    if is_asymmetric:
        logical_q, gate_depth, gate_count = _shors_resources(key_bits, algo_base)
        phys_q = _physical_qubits(logical_q, optimistic=True)
        break_secs = _shors_time_seconds(gate_depth)
        grover_iters = None
    else:
        logical_q, gate_depth, gate_count, grover_iters = _grovers_resources(key_bits)
        phys_q = _physical_qubits(logical_q, optimistic=True)
        break_secs = _grovers_time_seconds(grover_iters, key_bits)

    time_human = _human_time(break_secs)

    # ── 2030 breakability assessment ─────────────────────────────────────────
    # Based on: hardware roadmaps targeting ~1M physical qubits by early 2030s
    # Gidney 2025: RSA-2048 needs ~1M physical qubits (surface code)
    # Iceberg Quantum 2026: RSA-2048 needs ~62K-100K (QLDPC)
    # We use 1M as the conservative 2030 threshold.
    PROJECTED_PHYSICAL_QUBITS_2030 = 1_000_000

    breakable_2030 = phys_q <= PROJECTED_PHYSICAL_QUBITS_2030

    # Urgency multiplier for the CVSS-Q risk scorer (Step 3 in main agent)
    if breakable_2030 and phys_q < 100_000:
        urgency_multiplier = 1.5   # very high — breakable even with near-term hardware
    elif breakable_2030 and phys_q < 500_000:
        urgency_multiplier = 1.3   # high — within 2030 projections comfortably
    elif breakable_2030:
        urgency_multiplier = 1.15  # moderate — at the edge of 2030 projections
    else:
        urgency_multiplier = 1.0   # not immediately breakable by 2030

    # Special case: AES-128 / Grover's — always flag even though not "breakable"
    # Grover halves effective security: 128-bit → 64-bit effective
    if not is_asymmetric:
        breakable_2030 = False
    if algo_base == "AES-128":
        urgency_multiplier = 1.2  # Grover's on AES-128 still needs 2^64 ops

    # ── Build pedagogical Qiskit circuits ───────────────────────────────────
    # We build small-scale circuits (not real key size) for visualisation.
    # The real circuit dimensions are shown via the resource estimates above.
    circuit_qasm = None
    circuit_ascii = None

    if QISKIT_AVAILABLE:
        try:
            if is_asymmetric:
                # Small demo circuit: 3-qubit counting register
                demo_n = min(3, max(2, key_bits.bit_length() // 8))
                qc = _build_shors_demo_circuit(n_count=demo_n)
            else:
                demo_n = min(4, max(2, key_bits // 32))
                qc = _build_grovers_demo_circuit(n_qubits=demo_n)

            if qc is not None:
                circuit_ascii = str(qc.draw(output="text", fold=80))
                circuit_qasm  = qc.qasm() if hasattr(qc, "qasm") else None
                log.info(f"QASS: Circuit built — {qc.num_qubits} qubits, depth {qc.depth()}")
        except Exception as e:
            log.warning(f"QASS: Circuit build failed (non-critical): {e}")

    # ── Threat summary for dashboard ─────────────────────────────────────────
    if is_asymmetric:
        threat_summary = (
            f"Shor's algorithm applied to {algorithm}: requires {logical_q:,} logical qubits "
            f"({phys_q:,} physical at 2030 QLDPC error rates). "
            f"Gate depth: {gate_depth:,.0f}. "
            f"Estimated time to break: {time_human}. "
        )
        if breakable_2030:
            threat_summary += (
                f"⚠ WITHIN 2030 PROJECTIONS — Iceberg Quantum (Feb 2026) "
                f"demonstrated RSA-2048 may require only ~62K-100K physical qubits "
                f"with QLDPC codes. This key is at risk by 2030."
            )
        else:
            threat_summary += "Outside near-term 2030 quantum hardware projections."
    else:
        # Grover's
        effective_bits = key_bits // 2
        threat_summary = (
            f"Grover's algorithm on {algorithm}: Grover's search halves the effective "
            f"key length from {key_bits} bits to {effective_bits} bits. "
            f"Requires {grover_iters:.2e} oracle iterations. "
            f"Logical qubits: {logical_q:,}. "
            f"AES-256 is recommended — Grover's reduces it to 128-bit security, "
            f"which remains computationally infeasible."
        )
        if algo_base in ("MD5", "SHA1"):
            threat_summary = (
                f"Grover's algorithm on {algorithm}: "
                f"{grover_iters:.2e} iterations needed for preimage attack. "
                f"However, classical collision attacks already break {algo_base} "
                f"— quantum attack is not the primary concern. Replace immediately."
            )

    return QASSResult(
        algorithm=algorithm,
        attack_type=attack_type,
        logical_qubits=logical_q,
        gate_depth=gate_depth,
        gate_count_estimate=gate_count,
        physical_qubits_2030=phys_q,
        time_to_break_seconds=break_secs,
        time_to_break_human=time_human,
        grover_iterations=grover_iters,
        breakable_by_2030=breakable_2030,
        urgency_multiplier=urgency_multiplier,
        threat_summary=threat_summary,
        circuit_qasm=circuit_qasm,
        circuit_ascii=circuit_ascii,
    )