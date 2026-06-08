"""
Quantum Visualizer — Step 8 of Vyala Archon
============================================
Fixed: dark-mode-aware colors. The SVG is wrapped in an HTML shell
(see generate_quantum_visualization) that injects CSS variables before
rendering, so Streamlit's isolated iframe resolves them correctly in
both light and dark mode.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from engine.qass import QASSResult

log = logging.getLogger("vyala_archon.visualizer")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class QuantumVisualization:
    algorithm: str
    attack_type: str
    svg: str           # now a full HTML string (shell + SVG + <style>)
    plain_text: str
    caption: str
    gate_legend: list[dict]
    real_scale_note: str


# ---------------------------------------------------------------------------
# HTML wrapper that provides CSS variables for the isolated iframe
# Streamlit's components.v1.html() does NOT inherit the parent page's
# CSS variables, so we must define them ourselves.  We detect dark mode
# via matchMedia and swap to dark values.
# ---------------------------------------------------------------------------

_HTML_SHELL = """\
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  :root {{
    --c-bg:        #FFFFFF;
    --c-bg2:       #F9FAFB;
    --c-border:    #E5E7EB;
    --c-border2:   #D1D5DB;
    --c-text:      #111827;
    --c-text2:     #6B7280;
    --c-blue:      #2563EB;
    --c-blue-bg:   #EFF6FF;
    --c-blue-brd:  #93C5FD;
    --c-green-bg:  #F0FDF4;
    --c-green-brd: #6EE7B7;
    --c-green:     #059669;
    --c-warn:      #D97706;
    --c-warn-bg:   #FFFBEB;
    --c-warn-brd:  #FDE68A;
    --c-danger:    #DC2626;
    font-family: ui-monospace, 'Courier New', monospace;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --c-bg:        #1F2937;
      --c-bg2:       #111827;
      --c-border:    #374151;
      --c-border2:   #4B5563;
      --c-text:      #F9FAFB;
      --c-text2:     #9CA3AF;
      --c-blue:      #60A5FA;
      --c-blue-bg:   #1E3A5F;
      --c-blue-brd:  #3B82F6;
      --c-green-bg:  #052e16;
      --c-green-brd: #16a34a;
      --c-green:     #4ade80;
      --c-warn:      #FBBF24;
      --c-warn-bg:   #422006;
      --c-warn-brd:  #D97706;
      --c-danger:    #F87171;
    }}
  }}
  body {{ margin: 0; padding: 0; background: transparent; }}
  svg {{ width: 100%; height: auto; display: block; }}
</style>
</head>
<body>
{svg_content}
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Gate box helper
# ---------------------------------------------------------------------------

def _gate_box(x: int, y: int, w: int, h: int, label: str, color: str = "blue") -> str:
    if color == "blue":
        bg  = "fill:var(--c-blue-bg)"
        st  = "stroke:var(--c-blue-brd)"
        tc  = "fill:var(--c-blue)"
    elif color == "green":
        bg  = "fill:var(--c-green-bg)"
        st  = "stroke:var(--c-green-brd)"
        tc  = "fill:var(--c-green)"
    elif color == "warn":
        bg  = "fill:var(--c-warn-bg)"
        st  = "stroke:var(--c-warn-brd)"
        tc  = "fill:var(--c-warn)"
    else:
        bg  = "fill:var(--c-bg2)"
        st  = "stroke:var(--c-border)"
        tc  = "fill:var(--c-text)"

    cx = x + w // 2
    cy = y + h // 2
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="3" '
        f'style="{bg};{st};stroke-width:0.8"/>'
        f'<text x="{cx}" y="{cy+4}" '
        f'style="font-family:var(--font,monospace);font-size:11px;font-weight:500;{tc};text-anchor:middle">'
        f'{label}</text>'
    )


# ---------------------------------------------------------------------------
# Shor's circuit SVG
# ---------------------------------------------------------------------------

def _shors_svg(result: QASSResult) -> str:
    n_count = min(result.logical_qubits, 4)
    has_ellipsis = result.logical_qubits > 4

    W = 700
    HEADER_H = 56
    WIRE_SPACING = 44
    WIRE_ROWS = n_count + 1
    FOOTER_H = 60
    H = HEADER_H + WIRE_ROWS * WIRE_SPACING + FOOTER_H + 20

    L = []
    L.append(f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg"'
             f' role="img" aria-label="Shor\'s algorithm circuit for {result.algorithm}">')

    # Title bar
    L.append(f'<rect x="0" y="0" width="{W}" height="{HEADER_H}" style="fill:var(--c-bg2)"/>')
    L.append(f'<text x="16" y="22" style="font-family:sans-serif;font-size:13px;font-weight:500;fill:var(--c-text)">'
             f"Shor's algorithm — {result.algorithm} quantum attack circuit</text>")
    L.append(f'<text x="16" y="40" style="font-family:sans-serif;font-size:11px;fill:var(--c-warn)">'
             f"Pedagogical structure — actual: {result.logical_qubits:,} logical qubits, "
             f"depth {result.gate_depth:,}</text>")

    X_LABEL = 16
    X_INIT  = 100
    X_H     = 160
    X_U2    = 320
    X_BAR1  = 430
    X_QFT   = 490
    X_BAR2  = 560
    X_MEAS  = 590
    WIRE_END = W - 20

    for i in range(n_count):
        y = HEADER_H + 10 + i * WIRE_SPACING + WIRE_SPACING // 2

        L.append(f'<line x1="{X_INIT}" y1="{y}" x2="{WIRE_END}" y2="{y}" '
                 f'style="stroke:var(--c-border2);stroke-width:1.2"/>')
        L.append(f'<text x="{X_LABEL}" y="{y+4}" '
                 f'style="font-size:11px;fill:var(--c-text2)">|0⟩ q{i}</text>')

        L.append(_gate_box(X_H - 12, y - 12, 24, 24, "H", "blue"))

        cx = 250 + i * 25
        L.append(f'<circle cx="{cx}" cy="{y}" r="5" style="fill:var(--c-blue)"/>')
        target_y = HEADER_H + 10 + n_count * WIRE_SPACING + WIRE_SPACING // 2
        L.append(f'<line x1="{cx}" y1="{y}" x2="{cx}" y2="{target_y}" '
                 f'style="stroke:var(--c-text2);stroke-width:1;stroke-dasharray:3 2"/>')

    # QFT† block
    qft_top = HEADER_H + 10 + WIRE_SPACING // 2 - 16
    qft_bot = HEADER_H + 10 + (n_count - 1) * WIRE_SPACING + WIRE_SPACING // 2 + 16
    qft_h   = qft_bot - qft_top
    L.append(f'<rect x="{X_QFT-12}" y="{qft_top}" width="60" height="{qft_h}" rx="4" '
             f'style="fill:var(--c-blue-bg);stroke:var(--c-blue-brd);stroke-width:0.5"/>')
    L.append(f'<text x="{X_QFT+18}" y="{(qft_top+qft_bot)//2+4}" '
             f'style="font-size:11px;font-weight:500;fill:var(--c-blue);text-anchor:middle">QFT†</text>')

    # Measurement boxes
    for i in range(n_count):
        y = HEADER_H + 10 + i * WIRE_SPACING + WIRE_SPACING // 2
        L.append(_gate_box(X_MEAS - 12, y - 12, 28, 24, "M", "green"))
        L.append(f'<line x1="{X_MEAS+18}" y1="{y-2}" x2="{WIRE_END}" y2="{y-2}" '
                 f'style="stroke:var(--c-text2);stroke-width:0.8"/>')
        L.append(f'<line x1="{X_MEAS+18}" y1="{y+2}" x2="{WIRE_END}" y2="{y+2}" '
                 f'style="stroke:var(--c-text2);stroke-width:0.8"/>')

    # Target wire
    target_y = HEADER_H + 10 + n_count * WIRE_SPACING + WIRE_SPACING // 2
    L.append(f'<line x1="{X_INIT}" y1="{target_y}" x2="{WIRE_END}" y2="{target_y}" '
             f'style="stroke:var(--c-border2);stroke-width:1.2"/>')
    L.append(f'<text x="{X_LABEL}" y="{target_y+4}" '
             f'style="font-size:11px;fill:var(--c-text2)">|1⟩ tgt</text>')
    L.append(_gate_box(X_H - 12, target_y - 12, 24, 24, "X", "gray"))

    if has_ellipsis:
        L.append(f'<text x="{X_LABEL}" y="{target_y-8}" style="font-size:14px;fill:var(--c-text2)">⋮</text>')

    for bx in (X_BAR1, X_BAR2):
        L.append(f'<line x1="{bx}" y1="{HEADER_H+10}" x2="{bx}" y2="{target_y+22}" '
                 f'style="stroke:var(--c-border);stroke-width:1;stroke-dasharray:4 3"/>')

    for label, cx in [("H", X_H), ("ctrl-U", X_U2), ("QFT†", X_QFT+18), ("meas", X_MEAS+4)]:
        L.append(f'<text x="{cx}" y="{H-FOOTER_H+14}" '
                 f'style="font-size:10px;fill:var(--c-text2);text-anchor:middle">{label}</text>')

    # Footer
    footer_y = H - 38
    L.append(f'<rect x="0" y="{footer_y-10}" width="{W}" height="48" style="fill:var(--c-bg2)"/>')
    L.append(f'<text x="16" y="{footer_y+8}" '
             f'style="font-family:sans-serif;font-size:11px;fill:var(--c-text)">'
             f"Logical qubits: {result.logical_qubits:,}  │  "
             f"Physical qubits (2030 QLDPC): {result.physical_qubits_2030:,}  │  "
             f"Gate depth: {result.gate_depth:,}  │  "
             f"Time to break: {result.time_to_break_human}</text>")
    L.append(f'<text x="16" y="{footer_y+24}" '
             f'style="font-family:sans-serif;font-size:10px;fill:var(--c-text2)">'
             f"Source: Gidney &amp; Ekerå 2025 · Iceberg Quantum 2026 (arXiv:2602.11457) · Beauregard 2003"
             f"</text>")
    L.append("</svg>")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# Grover's circuit SVG
# ---------------------------------------------------------------------------

def _grovers_svg(result: QASSResult) -> str:
    n_q = min(4, max(2, result.logical_qubits // 32))

    W = 660
    HEADER_H = 56
    WIRE_SPACING = 44
    FOOTER_H = 60
    H = HEADER_H + n_q * WIRE_SPACING + FOOTER_H + 20

    L = []
    L.append(f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg"'
             f' role="img" aria-label="Grover\'s algorithm circuit for {result.algorithm}">')

    L.append(f'<rect x="0" y="0" width="{W}" height="{HEADER_H}" style="fill:var(--c-bg2)"/>')
    L.append(f'<text x="16" y="22" style="font-family:sans-serif;font-size:13px;font-weight:500;fill:var(--c-text)">'
             f"Grover's algorithm — {result.algorithm} key search circuit</text>")
    L.append(f'<text x="16" y="40" style="font-family:sans-serif;font-size:11px;fill:var(--c-warn)">'
             f"{result.grover_iterations:.2e} iterations — AES-128 effective security halved to 64-bit</text>")

    X_LABEL = 16
    X_INIT  = 90
    X_H1    = 140
    X_BAR1  = 190
    X_ORC   = 240
    X_BAR2  = 310
    X_DIFF  = 380
    X_BAR3  = 450
    X_MEAS  = 500
    WIRE_END = W - 20

    for i in range(n_q):
        y = HEADER_H + 10 + i * WIRE_SPACING + WIRE_SPACING // 2

        L.append(f'<line x1="{X_INIT}" y1="{y}" x2="{WIRE_END}" y2="{y}" '
                 f'style="stroke:var(--c-border2);stroke-width:1.2"/>')
        L.append(f'<text x="{X_LABEL}" y="{y+4}" style="font-size:11px;fill:var(--c-text2)">|0⟩ q{i}</text>')
        L.append(_gate_box(X_H1 - 12, y - 12, 24, 24, "H", "blue"))

        if i == n_q - 1:
            L.append(_gate_box(X_ORC - 12, y - 12, 24, 24, "Z", "warn"))
        else:
            L.append(f'<circle cx="{X_ORC}" cy="{y}" r="5" style="fill:var(--c-warn)"/>')
            target_y = HEADER_H + 10 + (n_q - 1) * WIRE_SPACING + WIRE_SPACING // 2
            L.append(f'<line x1="{X_ORC}" y1="{y}" x2="{X_ORC}" y2="{target_y}" '
                     f'style="stroke:var(--c-text2);stroke-width:1;stroke-dasharray:3 2"/>')

        if i == 0:
            diff_top = y - 16
            diff_bot = HEADER_H + 10 + (n_q - 1) * WIRE_SPACING + WIRE_SPACING // 2 + 16
            L.append(f'<rect x="{X_DIFF-16}" y="{diff_top}" width="64" height="{diff_bot-diff_top}" rx="4" '
                     f'style="fill:var(--c-blue-bg);stroke:var(--c-blue-brd);stroke-width:0.5"/>')
            L.append(f'<text x="{X_DIFF+16}" y="{(diff_top+diff_bot)//2+4}" '
                     f'style="font-size:11px;font-weight:500;fill:var(--c-blue);text-anchor:middle">Diffuse</text>')

        L.append(_gate_box(X_MEAS - 12, y - 12, 28, 24, "M", "green"))

    for bx in (X_BAR1, X_BAR2, X_BAR3):
        bot_y = HEADER_H + 10 + n_q * WIRE_SPACING
        L.append(f'<line x1="{bx}" y1="{HEADER_H+10}" x2="{bx}" y2="{bot_y}" '
                 f'style="stroke:var(--c-border);stroke-width:1;stroke-dasharray:4 3"/>')

    for label, cx in [("H", X_H1), ("Oracle", X_ORC), ("Diffuse", X_DIFF+16), ("meas", X_MEAS+4)]:
        L.append(f'<text x="{cx}" y="{H-FOOTER_H+14}" '
                 f'style="font-size:10px;fill:var(--c-text2);text-anchor:middle">{label}</text>')

    footer_y = H - 38
    L.append(f'<rect x="0" y="{footer_y-10}" width="{W}" height="48" style="fill:var(--c-bg2)"/>')
    L.append(f'<text x="16" y="{footer_y+8}" '
             f'style="font-family:sans-serif;font-size:11px;fill:var(--c-text)">'
             f"Logical qubits: {result.logical_qubits:,}  │  "
             f"Grover iterations: {result.grover_iterations:.2e}  │  "
             f"Time: {result.time_to_break_human}</text>")
    L.append(f'<text x="16" y="{footer_y+24}" '
             f'style="font-family:sans-serif;font-size:10px;fill:var(--c-text2)">'
             f"NIST guidance: AES-256 recommended (quantum-resistant). "
             f"Grover's on AES-256 → 2^128 ops, practically infeasible.</text>")
    L.append("</svg>")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# ASCII fallbacks
# ---------------------------------------------------------------------------

def _shors_ascii(result: QASSResult) -> str:
    n = min(result.logical_qubits, 4)
    rows = [
        f"Shor's Algorithm Circuit — {result.algorithm}",
        f"Logical qubits: {result.logical_qubits:,}  |  Gate depth: {result.gate_depth:,}",
        "-" * 60,
    ]
    for i in range(n):
        rows.append(f"|0⟩ q{i}: ──[H]──●──────────────[QFT†]──[M]──")
    rows.append(f"|1⟩ tgt: ──[X]──[a^x mod N]──────────────────────")
    if result.logical_qubits > 4:
        rows.append(f"  ... ({result.logical_qubits - 4:,} more counting qubits)")
    rows += [
        "-" * 60,
        f"Time to break at 2030 error rates: {result.time_to_break_human}",
        f"Physical qubits (QLDPC): {result.physical_qubits_2030:,}",
    ]
    return "\n".join(rows)


def _grovers_ascii(result: QASSResult) -> str:
    n = min(4, max(2, result.logical_qubits // 32))
    rows = [
        f"Grover's Algorithm Circuit — {result.algorithm}",
        f"Iterations: {result.grover_iterations:.2e}",
        "-" * 60,
    ]
    for i in range(n):
        rows.append(f"|0⟩ q{i}: ──[H]──[Oracle]──[Diffuse]──[M]──")
    rows += [
        "-" * 60,
        "Effective key strength after Grover: half the original bits",
        f"Logical qubits required: {result.logical_qubits:,}",
    ]
    return "\n".join(rows)


# ---------------------------------------------------------------------------
# Gate legends
# ---------------------------------------------------------------------------

_GATE_LEGENDS = {
    "shors": [
        {"symbol": "H",     "name": "Hadamard",       "description": "Creates superposition — qubit explores all states simultaneously"},
        {"symbol": "ctrl-U","name": "Controlled-U",   "description": "Modular exponentiation a^x mod N — encodes periodicity into phase"},
        {"symbol": "QFT†",  "name": "Inverse QFT",    "description": "Quantum Fourier Transform† extracts the period r from phase"},
        {"symbol": "M",     "name": "Measurement",    "description": "Collapses quantum state — yields r for classical post-processing"},
        {"symbol": "CNOT",  "name": "Controlled-NOT", "description": "Two-qubit entangling gate — core of modular arithmetic"},
    ],
    "grovers": [
        {"symbol": "H",      "name": "Hadamard",        "description": "Initialises uniform superposition over all 2^n possible keys"},
        {"symbol": "Z",      "name": "Phase Oracle",    "description": "Marks the correct key with a phase flip (−1)"},
        {"symbol": "Diffuse","name": "Grover Diffusion","description": "Amplifies the marked state's probability via reflection about mean"},
        {"symbol": "M",      "name": "Measurement",     "description": "After √(2^n) iterations, correct key has high probability"},
    ],
}


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_quantum_visualization(qass_result: QASSResult) -> QuantumVisualization:
    """
    Step 8 of Vyala Archon — Quantum Visualizer.
    Returns an HTML string (not bare SVG) so CSS variables resolve inside
    Streamlit's iframe sandbox.
    """
    log.info(f"Quantum Visualizer: {qass_result.algorithm} ({qass_result.attack_type})")

    if qass_result.attack_type == "shors":
        raw_svg    = _shors_svg(qass_result)
        plain_text = _shors_ascii(qass_result)
        caption = (
            f"Shor's algorithm applied to {qass_result.algorithm}: "
            f"{qass_result.logical_qubits:,} logical qubits, "
            f"{qass_result.time_to_break_human} to break at 2030 projected hardware."
        )
        real_scale_note = (
            f"This diagram shows the circuit structure at compressed scale. "
            f"The real circuit for {qass_result.algorithm} has "
            f"{qass_result.logical_qubits:,} logical qubits "
            f"({qass_result.physical_qubits_2030:,} physical) "
            f"and gate depth {qass_result.gate_depth:,}. "
            f"Reference: Beauregard 2003, Gidney & Ekerå 2025, Iceberg Quantum 2026 (arXiv:2602.11457)."
        )
        legend = _GATE_LEGENDS["shors"]
    else:
        raw_svg    = _grovers_svg(qass_result)
        plain_text = _grovers_ascii(qass_result)
        caption = (
            f"Grover's algorithm applied to {qass_result.algorithm}: "
            f"{qass_result.grover_iterations:.2e} iterations halve effective key strength. "
            f"Upgrade to AES-256 for quantum resistance."
        )
        real_scale_note = (
            f"Full Grover's on {qass_result.algorithm} requires "
            f"{qass_result.grover_iterations:.2e} oracle calls. "
            f"AES-128 effective security drops to 64-bit. AES-256 → 128-bit: practically infeasible."
        )
        legend = _GATE_LEGENDS["grovers"]

    # Wrap SVG in a full HTML shell so CSS variables resolve in Streamlit iframes
    html_output = _HTML_SHELL.format(svg_content=raw_svg)

    return QuantumVisualization(
        algorithm=qass_result.algorithm,
        attack_type=qass_result.attack_type,
        svg=html_output,
        plain_text=plain_text,
        caption=caption,
        gate_legend=legend,
        real_scale_note=real_scale_note,
    )