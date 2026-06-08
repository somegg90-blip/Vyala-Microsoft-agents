"""
QuantumShield Learning Platform — Orchestrator Agent
=====================================================
Top-level agent that receives user requests, identifies intent,
sequences sub-agent calls, and assembles the final response.

Intent routing:
  "assess"   → AssessmentAgent (Vyala Archon 8-step pipeline)
  "study"    → LearningPathCurator + StudyPlanGenerator
  "insights" → ManagerInsightsAgent
  "full"     → all agents in sequence (the full loop)

This is what makes QuantumShield a true multi-agent system,
satisfying the challenge's multi-agent architecture requirement.
"""

from __future__ import annotations

import os
import json
import logging
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timezone

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.ai.agents.models import MessageRole, ListSortOrder

log = logging.getLogger("quantumshield.orchestrator")

PROJECT_ENDPOINT = os.environ["FOUNDRY_PROJECT_ENDPOINT"]
MODEL = os.environ.get("FOUNDRY_MODEL", "gpt-4.1")

# ---------------------------------------------------------------------------
# Intent classification prompt
# ---------------------------------------------------------------------------

ORCHESTRATOR_INSTRUCTIONS = """
You are the QuantumShield orchestrator. Your ONLY job is to classify
the user's intent and return a JSON object. Nothing else.

Intents:
  "assess"   — user wants to scan a repo for PQC vulnerabilities
  "study"    — user wants a study/learning plan for their team
  "insights" — user wants manager-level team readiness dashboard
  "full"     — user wants the complete flow: assess + study + insights
  "reassess" — user has fixed something and wants a re-scan

Always return ONLY valid JSON, no explanation:
{
  "intent": "<intent>",
  "repo_url": "<url or null>",
  "team_id": "<team_id or null>",
  "engineer_id": "<engineer_id or null>",
  "branch": "<branch or null>"
}
""".strip()


@dataclass
class OrchestrationResult:
    intent: str
    repo_url: Optional[str]
    team_id: Optional[str]
    engineer_id: Optional[str]
    branch: Optional[str]
    assessment: Optional[dict] = None
    learning_path: Optional[dict] = None
    study_plan: Optional[dict] = None
    manager_insights: Optional[dict] = None
    orchestrated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    errors: list[str] = field(default_factory=list)


class OrchestratorAgent:
    """
    Routes requests to the correct sub-agent(s) and assembles
    the final response for the dashboard.
    """

    def __init__(self):
        self.credential = DefaultAzureCredential()
        self.client = AIProjectClient(
            endpoint=PROJECT_ENDPOINT,
            credential=self.credential,
        )
        self._agent = None
        self._thread = None

    def setup(self):
        self._agent = self.client.agents.create_version(
            agent_name="quantumshield-orchestrator",
            definition=PromptAgentDefinition(
                model=MODEL,
                instructions=ORCHESTRATOR_INSTRUCTIONS,
            ),
        )
        log.info(f"Orchestrator agent created: {self._agent.id}")

    def _classify_intent(self, user_message: str) -> dict:
        """Send message to orchestrator agent, get intent JSON back."""
        if self._thread is None:
            self._thread = self.client.agents.threads.create()

        self.client.agents.messages.create(
            thread_id=self._thread.id,
            role=MessageRole.USER,
            content=user_message,
        )
        run = self.client.agents.runs.create(
            thread_id=self._thread.id,
            agent_id=self._agent.id,
        )

        import time
        deadline = time.time() + 60
        while time.time() < deadline:
            r = self.client.agents.runs.get(
                thread_id=self._thread.id, run_id=run.id
            )
            if r.status == "completed":
                msgs = self.client.agents.messages.list(
                    thread_id=self._thread.id,
                    order=ListSortOrder.DESCENDING,
                )
                for msg in msgs:
                    if msg.role == MessageRole.ASSISTANT:
                        raw = msg.content[0].text.value if msg.content else "{}"
                        # Strip markdown fences if present
                        raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
                        try:
                            return json.loads(raw)
                        except json.JSONDecodeError:
                            log.warning(f"Could not parse intent JSON: {raw}")
                            return {"intent": "full", "repo_url": None,
                                    "team_id": None, "engineer_id": None, "branch": None}
                break
            elif r.status in ("failed", "cancelled", "expired"):
                break
            time.sleep(1)

        return {"intent": "full", "repo_url": None,
                "team_id": None, "engineer_id": None, "branch": None}

    def run(
        self,
        user_message: str,
        # Allow callers to pre-supply sub-agent instances
        assessment_agent=None,
        curator_agent=None,
        study_plan_agent=None,
        insights_agent=None,
    ) -> OrchestrationResult:
        """
        Full orchestration loop:
        1. Classify intent
        2. Call relevant sub-agents in sequence
        3. Return assembled OrchestrationResult
        """
        log.info(f"Orchestrator: classifying intent for: {user_message[:80]}")
        parsed = self._classify_intent(user_message)

        result = OrchestrationResult(
            intent=parsed.get("intent", "full"),
            repo_url=parsed.get("repo_url"),
            team_id=parsed.get("team_id"),
            engineer_id=parsed.get("engineer_id"),
            branch=parsed.get("branch"),
        )

        log.info(f"Orchestrator: intent={result.intent}, repo={result.repo_url}")

        # ── Route to sub-agents ──────────────────────────────────────────────
        try:
            if result.intent in ("assess", "full", "reassess"):
                if assessment_agent and result.repo_url:
                    log.info("Orchestrator → AssessmentAgent")
                    report = assessment_agent.run_full_scan_v2(
                        result.repo_url, branch=result.branch
                    )
                    result.assessment = _serialize_report(report)

            if result.intent in ("study", "full"):
                if curator_agent and result.assessment:
                    log.info("Orchestrator → LearningPathCuratorAgent")
                    result.learning_path = curator_agent.run(
                        result.assessment, result.engineer_id
                    )

                if study_plan_agent and result.learning_path:
                    log.info("Orchestrator → StudyPlanGeneratorAgent")
                    result.study_plan = study_plan_agent.run(
                        result.learning_path,
                        result.engineer_id or "EMP-001",
                    )

            if result.intent in ("insights", "full"):
                if insights_agent:
                    log.info("Orchestrator → ManagerInsightsAgent")
                    result.manager_insights = insights_agent.run(
                        result.team_id or "TEAM-A",
                        result.assessment,
                    )

        except Exception as e:
            log.error(f"Orchestrator sub-agent error: {e}")
            result.errors.append(str(e))

        return result

    def teardown(self):
        if self._agent:
            try:
                self.client.agents.delete_agent(self._agent.id)
            except Exception:
                pass


def _serialize_report(report) -> dict:
    """Convert EnhancedScanReport to a JSON-serializable dict."""
    return {
        "repo_url": report.repo_url,
        "summary": report.summary(),
        "findings_count": len(report.findings),
        "top_findings": [
            {
                "file": r.finding.file,
                "line": r.finding.line,
                "algorithm": r.finding.algorithm,
                "severity": r.finding.severity.value,
                "quantum_risk_score": r.finding.quantum_risk_score,
                "pqc_replacement": r.pqc_replacement,
                "fips_standard": r.fips_standard,
                "iq_confidence": r.iq_confidence,
                "effort_hours": r.migration_effort_hours,
                "status": r.status,
            }
            for r in report.remediation_plan[:10]  # top 10 for context
        ],
        "qass_summary": {
            algo: {
                "logical_qubits": q.logical_qubits,
                "physical_qubits_2030": q.physical_qubits_2030,
                "time_to_break": q.time_to_break_human,
                "breakable_by_2030": q.breakable_by_2030,
                "urgency_multiplier": q.urgency_multiplier,
                "threat_summary": q.threat_summary,
            }
            for algo, q in report.qass_results.items()
        },
        "quantum_circuit_caption": (
            report.quantum_visualization.caption
            if report.quantum_visualization else None
        ),
    }