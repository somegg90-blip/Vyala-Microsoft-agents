"""
Vyala Archon — Entry point
==========================
Run modes:
  python -m vyala_archon scan <repo_url> [--branch <branch>] [--out report.json]
  python -m vyala_archon serve                 # FastAPI dashboard server

Install:
  pip install azure-ai-projects azure-identity qiskit qiskit-aer \
              tree-sitter fastapi uvicorn

Environment variables (required):
  FOUNDRY_PROJECT_ENDPOINT    — Foundry project endpoint URL
  AZURE_SEARCH_ENDPOINT       — Azure AI Search endpoint
  KB_NAME                     — Knowledge base name (default: pqc-kb)
  KB_CONNECTION_NAME          — Foundry project connection name for Foundry IQ
  GITHUB_CONNECTION_NAME      — Foundry project connection name for GitHub MCP
"""

import sys
import json
import argparse
import logging
import os
from dataclasses import asdict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("vyala_archon")


def _dataclass_serializer(obj):
    """Custom JSON serializer for dataclasses and enums."""
    if hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)
    if hasattr(obj, "value"):
        return obj.value
    return str(obj)


def cmd_scan(args):
    from agent.archon_agent_v2 import VyalaArchonAgentV2

    agent = VyalaArchonAgentV2(branch=args.branch)
    try:
        agent.setup()
        report = agent.run_full_scan_v2(args.repo_url, branch=args.branch)
    finally:
        agent.teardown()

    # Print summary
    summary = report.summary()
    print("\n" + "=" * 60)
    print(f"Vyala Archon — Scan Complete")
    print(f"Repo:    {report.repo_url}")
    print(f"Host:    {report.repo_host}  |  Branch: {report.branch or 'default'}")
    print(f"Files:   {report.total_files_scanned} scanned, "
          f"{report.files_skipped_no_crypto_imports} skipped (no crypto imports)")
    print(f"Findings: {len(report.findings)}")
    print("-" * 60)
    for sev, count in summary.items():
        if count > 0:
            print(f"  {sev:12s}: {count}")
    print("=" * 60)

    if report.quantum_visualization:
        print(f"\nQuantum Circuit: {report.quantum_visualization.caption}")
        print(report.quantum_visualization.plain_text)
        print()

    # Top 3 critical items
    critical = [r for r in report.remediation_plan if r.finding.severity.value == "CRITICAL"]
    if critical:
        print(f"\nTop {min(3, len(critical))} CRITICAL findings:")
        for r in critical[:3]:
            conf_str = f"conf={r.iq_confidence:.2f}" if r.iq_confidence else ""
            print(
                f"  {r.finding.file}:{r.finding.line}  "
                f"{r.finding.algorithm} → {r.pqc_replacement} ({r.fips_standard})  "
                f"[{conf_str}]  [{r.status}]"
            )

    # Save report
    if args.out:
        # Remove non-serializable Qiskit circuit objects before saving
        report_dict = {
            "repo_url": report.repo_url,
            "scanned_at": report.scanned_at,
            "total_files_scanned": report.total_files_scanned,
            "files_skipped": report.files_skipped_no_crypto_imports,
            "repo_host": report.repo_host,
            "branch": report.branch,
            "summary": summary,
            "findings_count": len(report.findings),
            "remediation_plan": [
                {
                    "file": r.finding.file,
                    "line": r.finding.line,
                    "algorithm": r.finding.algorithm,
                    "severity": r.finding.severity.value,
                    "quantum_risk_score": r.finding.quantum_risk_score,
                    "use_case": r.finding.use_case,
                    "critical_path": r.finding.critical_path,
                    "pqc_replacement": r.pqc_replacement,
                    "fips_standard": r.fips_standard,
                    "iq_confidence": r.iq_confidence,
                    "citations": r.iq_citations,
                    "effort_hours": r.migration_effort_hours,
                    "hybrid_transition": r.hybrid_transition,
                    "code_guidance": r.code_guidance,
                    "status": r.status,
                    "review_reason": r.review_reason,
                }
                for r in report.remediation_plan
            ],
            "qass_summary": {
                algo: {
                    "attack_type": q.attack_type,
                    "logical_qubits": q.logical_qubits,
                    "physical_qubits_2030": q.physical_qubits_2030,
                    "time_to_break": q.time_to_break_human,
                    "breakable_by_2030": q.breakable_by_2030,
                    "urgency_multiplier": q.urgency_multiplier,
                    "threat_summary": q.threat_summary,
                }
                for algo, q in report.qass_results.items()
            },
            "quantum_visualization": {
                "caption": report.quantum_visualization.caption,
                "real_scale_note": report.quantum_visualization.real_scale_note,
                "gate_legend": report.quantum_visualization.gate_legend,
                "plain_text": report.quantum_visualization.plain_text,
                # SVG is large; save to separate file
            } if report.quantum_visualization else None,
            "audit_log": report.audit_log,
        }

        with open(args.out, "w") as f:
            json.dump(report_dict, f, indent=2)
        log.info(f"Report saved to {args.out}")

        # Save SVG separately if visualization exists
        if report.quantum_visualization:
            svg_path = args.out.replace(".json", "_circuit.svg")
            with open(svg_path, "w") as f:
                f.write(report.quantum_visualization.svg)
            log.info(f"Circuit SVG saved to {svg_path}")


def cmd_serve(args):
    """Start FastAPI server for the dashboard."""
    try:
        from fastapi import FastAPI
        import uvicorn
    except ImportError:
        print("Install fastapi and uvicorn: pip install fastapi uvicorn")
        sys.exit(1)

    from agent.archon_agent_v2 import VyalaArchonAgentV2

    app = FastAPI(title="Vyala Archon", description="PQC Threat Intelligence Dashboard")

    @app.post("/scan")
    async def scan(repo_url: str, branch: str = None):
        agent = VyalaArchonAgentV2(branch=branch)
        try:
            agent.setup()
            report = agent.run_full_scan_v2(repo_url, branch=branch)
        finally:
            agent.teardown()

        return {
            "repo_url": repo_url,
            "summary": report.summary(),
            "findings_count": len(report.findings),
            "remediation_plan": [
                {
                    "file": r.finding.file,
                    "line": r.finding.line,
                    "algorithm": r.finding.algorithm,
                    "severity": r.finding.severity.value,
                    "quantum_risk_score": r.finding.quantum_risk_score,
                    "pqc_replacement": r.pqc_replacement,
                    "fips_standard": r.fips_standard,
                    "iq_confidence": r.iq_confidence,
                    "status": r.status,
                    "effort_hours": r.migration_effort_hours,
                    "hybrid_transition": r.hybrid_transition,
                }
                for r in report.remediation_plan
            ],
            "qass_summary": {
                algo: {
                    "logical_qubits": q.logical_qubits,
                    "physical_qubits_2030": q.physical_qubits_2030,
                    "time_to_break": q.time_to_break_human,
                    "breakable_by_2030": q.breakable_by_2030,
                    "urgency_multiplier": q.urgency_multiplier,
                }
                for algo, q in report.qass_results.items()
            },
            "quantum_circuit_svg": (
                report.quantum_visualization.svg
                if report.quantum_visualization else None
            ),
            "quantum_circuit_caption": (
                report.quantum_visualization.caption
                if report.quantum_visualization else None
            ),
            "audit_log": report.audit_log,
        }

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": "2.0"}

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))


def main():
    parser = argparse.ArgumentParser(
        description="Vyala Archon — PQC Threat Intelligence Agent"
    )
    subparsers = parser.add_subparsers(dest="command")

    # scan command
    scan_parser = subparsers.add_parser("scan", help="Scan a repository")
    scan_parser.add_argument("repo_url", help="GitHub URL, GitLab URL, or local path")
    scan_parser.add_argument("--branch", default=None, help="Branch to scan")
    scan_parser.add_argument("--out", default="report.json", help="Output JSON path")

    # serve command
    serve_parser = subparsers.add_parser("serve", help="Start dashboard API server")
    serve_parser.add_argument("--port", default=8000, type=int)

    args = parser.parse_args()

    if args.command == "scan":
        cmd_scan(args)
    elif args.command == "serve":
        cmd_serve(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()