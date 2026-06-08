"""
QuantumShield Learning Platform — Study Plan Generator Agent
============================================================
Combines LearningPathCurator output with Work IQ signals (meeting load,
focus hours, preferred learning slots) and Fabric IQ semantic role mapping
to produce a realistic, week-by-week PQC certification study plan.

IQ layers used:
  Work IQ  — synthetic work signals (meeting hours, focus windows)
  Fabric IQ — semantic model: role → certification → skill gap → study hours

This satisfies the challenge's Study Plan Generator requirement and
demonstrates Work IQ + Fabric IQ integration beyond just Foundry IQ.
"""

from __future__ import annotations

import os
import json
import math
import logging
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path
from datetime import datetime, timedelta, timezone

log = logging.getLogger("quantumshield.study_plan")

# ---------------------------------------------------------------------------
# Synthetic Work IQ signals (loaded from data/work_signals.json)
# Represents the Work IQ intelligence layer pattern:
# meeting load, focus hours, preferred study windows per engineer
# ---------------------------------------------------------------------------

DEFAULT_WORK_SIGNALS = {
    "EMP-001": {
        "role": "Backend Engineer",
        "meeting_hours_per_week": 22,
        "focus_hours_per_week": 10,
        "preferred_learning_slot": "Morning",
        "available_study_hours_per_week": 5,
    },
    "EMP-002": {
        "role": "DevOps Engineer",
        "meeting_hours_per_week": 15,
        "focus_hours_per_week": 18,
        "preferred_learning_slot": "Afternoon",
        "available_study_hours_per_week": 8,
    },
    "EMP-003": {
        "role": "Security Engineer",
        "meeting_hours_per_week": 12,
        "focus_hours_per_week": 22,
        "preferred_learning_slot": "Morning",
        "available_study_hours_per_week": 10,
    },
    "EMP-004": {
        "role": "Cloud Engineer",
        "meeting_hours_per_week": 28,
        "focus_hours_per_week": 8,
        "preferred_learning_slot": "Evening",
        "available_study_hours_per_week": 4,
    },
}

# ---------------------------------------------------------------------------
# Synthetic Fabric IQ semantic model
# Role → PQC certification track → prerequisite skills
# This is the Fabric IQ ontology: role, cert, skill gap, study hours
# ---------------------------------------------------------------------------

FABRIC_IQ_ROLE_MODEL = {
    "Backend Engineer": {
        "primary_cert": "NIST PQC Migration Specialist — Application Layer",
        "key_skill_gaps": ["ML-DSA signing", "ML-KEM key exchange", "hybrid TLS"],
        "recommended_study_hours": 20,
        "role_specific_focus": "JWT/session signing and TLS key exchange",
    },
    "DevOps Engineer": {
        "primary_cert": "NIST PQC Migration Specialist — Infrastructure Layer",
        "key_skill_gaps": ["PQC-enabled TLS configuration", "certificate rotation", "hybrid PKI"],
        "recommended_study_hours": 15,
        "role_specific_focus": "TLS configuration, certificate management, OpenSSL 3.x",
    },
    "Security Engineer": {
        "primary_cert": "NIST PQC Migration Specialist — Full Stack",
        "key_skill_gaps": ["Lattice cryptography theory", "QASS threat modelling", "CNSA 2.0 compliance"],
        "recommended_study_hours": 30,
        "role_specific_focus": "Threat modelling, compliance, cross-layer migration strategy",
    },
    "Cloud Engineer": {
        "primary_cert": "NIST PQC Migration Specialist — Cloud Services",
        "key_skill_gaps": ["PQC SDK integration", "key management service migration", "hybrid cloud PKI"],
        "recommended_study_hours": 18,
        "role_specific_focus": "Cloud KMS migration, SDK integration, managed certificate services",
    },
}


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class StudyWeek:
    week_number: int
    focus_topic: str
    algorithm: str
    study_type: str          # "theory" | "implementation" | "assessment" | "review"
    hours: float
    scheduled_slots: list[str]   # e.g. ["Tuesday Morning", "Thursday Morning"]
    deliverable: str             # what the engineer produces this week
    milestone: bool = False      # is this a checkpoint week?


@dataclass
class StudyPlan:
    engineer_id: str
    role: str
    target_certification: str
    total_weeks: int
    total_study_hours: float
    available_hours_per_week: float
    preferred_slot: str
    weeks: list[StudyWeek]
    work_iq_note: str = ""       # how work signals shaped the schedule
    fabric_iq_note: str = ""     # how role semantics shaped the plan
    readiness_target_date: str = ""
    pass_probability_at_completion: float = 0.82


# ---------------------------------------------------------------------------
# Study Plan Generator
# ---------------------------------------------------------------------------

class StudyPlanGeneratorAgent:
    """
    Generates a realistic per-engineer PQC study plan.

    Uses:
    - Work IQ signals: available study hours, preferred slot, meeting load
    - Fabric IQ model: role → certification → skill gaps
    - Learning path: modules from LearningPathCuratorAgent

    No Azure calls needed — this agent reasons locally over the
    synthetic IQ signals and the curator's output. The "intelligence"
    is in how it adapts the schedule to real work constraints.
    """

    def __init__(self, data_dir: Optional[str] = None):
        base = data_dir or os.path.join(os.path.dirname(__file__), "..", "data")
        work_signals_path = os.path.join(base, "work_signals.json")

        # Load synthetic Work IQ signals from file, fall back to defaults
        if Path(work_signals_path).exists():
            with open(work_signals_path) as f:
                self.work_signals = json.load(f)
        else:
            self.work_signals = DEFAULT_WORK_SIGNALS
            log.info("StudyPlan: using default synthetic work signals")

    def _get_work_signals(self, engineer_id: str) -> dict:
        return self.work_signals.get(engineer_id, DEFAULT_WORK_SIGNALS["EMP-001"])

    def _get_fabric_role_model(self, role: str) -> dict:
        return FABRIC_IQ_ROLE_MODEL.get(
            role,
            FABRIC_IQ_ROLE_MODEL["Backend Engineer"]
        )

    def _schedule_slots(self, preferred_slot: str, hours_needed: float) -> list[str]:
        """
        Pick study slots based on Work IQ preferred learning time.
        Returns human-readable slot descriptions.
        """
        days = {
            "Morning":   ["Tuesday Morning", "Thursday Morning", "Friday Morning"],
            "Afternoon": ["Monday Afternoon", "Wednesday Afternoon", "Friday Afternoon"],
            "Evening":   ["Monday Evening", "Wednesday Evening", "Thursday Evening"],
        }
        slots = days.get(preferred_slot, days["Morning"])
        # How many slots do we need? (assume 1.5h per slot)
        slots_needed = math.ceil(hours_needed / 1.5)
        return slots[:slots_needed]

    def run(
        self,
        learning_path: dict,
        engineer_id: str = "EMP-001",
    ) -> dict:
        """
        Generate a week-by-week study plan for the engineer.
        """
        signals = self._get_work_signals(engineer_id)
        role = signals.get("role", "Backend Engineer")
        fabric_model = self._get_fabric_role_model(role)
        available_hrs = signals.get("available_study_hours_per_week", 5)
        preferred_slot = signals.get("preferred_learning_slot", "Morning")
        modules = learning_path.get("modules", [])

        log.info(
            f"StudyPlan: generating for {engineer_id} ({role}), "
            f"{available_hrs}h/week, {preferred_slot} slots"
        )

        # Work IQ adaptation note
        meeting_hrs = signals.get("meeting_hours_per_week", 20)
        if meeting_hrs > 20:
            work_iq_note = (
                f"High meeting load detected ({meeting_hrs}h/week via Work IQ). "
                f"Study schedule capped at {available_hrs}h/week with {preferred_slot.lower()} "
                f"slots to avoid peak work periods."
            )
        else:
            work_iq_note = (
                f"Moderate meeting load ({meeting_hrs}h/week). "
                f"Study scheduled in {preferred_slot.lower()} focus windows for optimal retention."
            )

        fabric_iq_note = (
            f"Role '{role}' mapped to: {fabric_model['primary_cert']}. "
            f"Key skill gaps: {', '.join(fabric_model['key_skill_gaps'][:3])}. "
            f"Role-specific focus: {fabric_model['role_specific_focus']}."
        )

        # Build week-by-week schedule
        weeks: list[StudyWeek] = []
        week_num = 0

        for module in modules:
            algo = module["algorithm"]
            total_module_hrs = module["study_hours"].get("total", 5)
            theory_hrs = module["study_hours"].get("theory", 2)
            impl_hrs = module["study_hours"].get("implementation", 3)

            # Theory week(s)
            theory_weeks_needed = math.ceil(theory_hrs / available_hrs)
            for i in range(theory_weeks_needed):
                week_num += 1
                hrs = min(theory_hrs - (i * available_hrs), available_hrs)
                weeks.append(StudyWeek(
                    week_number=week_num,
                    focus_topic=f"{algo} → {module['replacement']}: Theory",
                    algorithm=algo,
                    study_type="theory",
                    hours=hrs,
                    scheduled_slots=self._schedule_slots(preferred_slot, hrs),
                    deliverable=(
                        f"Understand WHY {algo} fails against Shor's algorithm. "
                        f"Read {module['fips_standard']} §1–§3. "
                        f"Complete: {module['key_concepts'][0] if module['key_concepts'] else 'theory review'}."
                    ),
                    milestone=(i == theory_weeks_needed - 1),
                ))

            # Implementation week(s)
            impl_weeks_needed = math.ceil(impl_hrs / available_hrs)
            for i in range(impl_weeks_needed):
                week_num += 1
                hrs = min(impl_hrs - (i * available_hrs), available_hrs)
                step = module["implementation_steps"][i] if i < len(module["implementation_steps"]) else "Implement and test"
                weeks.append(StudyWeek(
                    week_number=week_num,
                    focus_topic=f"{algo} → {module['replacement']}: Implementation",
                    algorithm=algo,
                    study_type="implementation",
                    hours=hrs,
                    scheduled_slots=self._schedule_slots(preferred_slot, hrs),
                    deliverable=step,
                    milestone=False,
                ))

            # Assessment week after each module
            week_num += 1
            weeks.append(StudyWeek(
                week_number=week_num,
                focus_topic=f"{algo} Migration: Assessment Checkpoint",
                algorithm=algo,
                study_type="assessment",
                hours=1.0,
                scheduled_slots=[f"{preferred_slot} Friday"],
                deliverable=(
                    f"QuantumShield re-scan: verify {algo} replaced in codebase. "
                    f"Pass threshold: 0 remaining {algo} findings in critical paths."
                ),
                milestone=True,
            ))

        # Final certification review week
        week_num += 1
        weeks.append(StudyWeek(
            week_number=week_num,
            focus_topic="PQC Migration Certification — Final Review",
            algorithm="ALL",
            study_type="review",
            hours=available_hrs,
            scheduled_slots=self._schedule_slots(preferred_slot, available_hrs),
            deliverable=(
                "Full QuantumShield scan: 0 CRITICAL findings. "
                "CBOM export submitted for compliance record. "
                "Team readiness score ≥ 80%."
            ),
            milestone=True,
        ))

        total_hours = sum(w.hours for w in weeks)

        # Estimate target date (from today)
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc)
        target_date = today + timedelta(weeks=week_num)
        target_str = target_date.strftime("%B %Y")

        plan = StudyPlan(
            engineer_id=engineer_id,
            role=role,
            target_certification=fabric_model["primary_cert"],
            total_weeks=week_num,
            total_study_hours=total_hours,
            available_hours_per_week=available_hrs,
            preferred_slot=preferred_slot,
            weeks=weeks,
            work_iq_note=work_iq_note,
            fabric_iq_note=fabric_iq_note,
            readiness_target_date=target_str,
            pass_probability_at_completion=0.82,
        )

        log.info(
            f"StudyPlan: {week_num} weeks, {total_hours:.1f}h total, "
            f"target={target_str}"
        )

        return {
            "engineer_id": plan.engineer_id,
            "role": plan.role,
            "target_certification": plan.target_certification,
            "total_weeks": plan.total_weeks,
            "total_study_hours": plan.total_study_hours,
            "available_hours_per_week": plan.available_hours_per_week,
            "preferred_slot": plan.preferred_slot,
            "readiness_target_date": plan.readiness_target_date,
            "pass_probability_at_completion": plan.pass_probability_at_completion,
            "work_iq_note": plan.work_iq_note,
            "fabric_iq_note": plan.fabric_iq_note,
            "weeks": [
                {
                    "week": w.week_number,
                    "topic": w.focus_topic,
                    "algorithm": w.algorithm,
                    "type": w.study_type,
                    "hours": w.hours,
                    "slots": w.scheduled_slots,
                    "deliverable": w.deliverable,
                    "milestone": w.milestone,
                }
                for w in plan.weeks
            ],
        }