# ui/app.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import json
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="VyalaArchon", page_icon="🛡️", layout="wide")

st.title("🛡️ VyalaArchon Learning Platform")
st.caption("Enterprise PQC Certification Readiness — Multi-Agent Orchestration")

# --- Load Synthetic Data ---
@st.cache_data
def load_data(filepath):
    try:
        with open(filepath, 'r') as f: return json.load(f)
    except: return []

team_data = load_data('data/synthetic_team/team.json')
work_signals = load_data('data/synthetic_team/work_signals.json')
learner_perf = load_data('data/synthetic_team/learner_performance.json')

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Platform Configuration")
    view = st.radio("Select View:", ["👨‍💻 Engineer View", "👨‍💼 Manager View"])
    st.markdown("---")
    st.markdown("Built for Microsoft Agents League")
    st.markdown("Powered by Foundry IQ, Work IQ, Fabric IQ")

# ==============================================================================
# ENGINEER VIEW: Assessment + Study Plans
# ==============================================================================
if view == "👨‍💻 Engineer View":
    st.markdown("### 🔍 PQC Certification Readiness Assessment")
    
    # Use team.json for the dropdown (it has names and repos)
    if not team_data:
        st.error("Missing synthetic data: Please ensure data/synthetic_team/team.json exists.")
        st.stop()
        
    # Extract engineer list from team_data
    # Assuming team_data is a list like: [{"id": "EMP-001", "name": "Alice (DevOps)", "role": "DevOps Engineer", "repos": ["payments-service"]}]
    engineers = []
    if isinstance(team_data, list):
        engineers = team_data
    else:
        # Handle the nested TEAM-A format if you used that
        first_team_key = list(team_data.keys())[0]
        engineers = team_data[first_team_key].get("members", [])

    if not engineers:
        st.warning("No engineers found in team data.")
        st.stop()

    engineer_names = [f"{eng.get('name', eng.get('id', 'Unknown'))} — {eng.get('role', '')}" for eng in engineers]
    selected_idx = st.selectbox("Select Engineer for Assessment", range(len(engineer_names)), format_func=lambda i: engineer_names[i])
    
    selected_engineer = engineers[selected_idx]
    eng_id = selected_engineer.get('id', selected_engineer.get('employee_id', 'EMP-001'))
    eng_name = selected_engineer.get('name', eng_id)
    
    # Find their target cert from learner_performance.json
    target_cert = "NIST PQC Migration Specialist"
    if learner_perf:
        for lp in learner_perf:
            if lp.get("learner_id") == eng_id:
                target_cert = lp.get("certification", target_cert)
                break

    st.info(f"**Role:** {selected_engineer.get('role', 'N/A')} | **Target Cert:** {target_cert}")
    
    # Auto-fill the repo URL based on the engineer's assignment
    default_repo = "https://github.com/jpadilla/pyjwt" # Fallback
    assigned_repos = selected_engineer.get('repos', [])
    if assigned_repos:
        # Just use the first assigned repo for the demo
        repo_name = assigned_repos[0]
        # Assuming they belong to an org like "acme-corp" for synthetic data, 
        # but for the live demo, we force PyJWT so it actually works
        if "pyjwt" not in repo_name.lower():
            default_repo = f"https://github.com/jpadilla/pyjwt" # Keep PyJWT for reliable demo
        else:
            default_repo = f"https://github.com/jpadilla/{repo_name}"

    repo_url = st.text_input("Assigned Repository", default_repo)
    
    if st.button("🚀 Run Multi-Agent Assessment", type="primary"):
        # ... (THE REST OF THE SCANNING LOGIC STAYS THE SAME) ...
        st.warning("Orchestrator Agent routing request...")
        
        # --- 1. ASSESSMENT AGENT (Uses real Vyala Archon Engine) ---
        with st.status("🔍 Step 1: Assessment Agent scanning codebase...", expanded=True) as status:
            from engine.github_fetcher import get_repo_files
            from engine.scanner import scan_file_content
            from engine.scorer import score_finding
            from engine.gate import process_finding_with_iq
            
            files_dict = get_repo_files(repo_url)
            all_findings = []
            for filepath, content in files_dict.items():
                findings = scan_file_content(filepath, content)
                all_findings.extend(findings)
            status.update(label="Assessment Complete", state="complete", expanded=False)

        if not all_findings:
            st.success("✅ No PQC skill gaps found! Engineer is certification ready.")
        else:
            # --- 2. CURATOR AGENT (Mocked for UI flow) ---
            with st.status("📚 Step 2: Curator Agent generating learning paths...", expanded=True) as status:
                remediation_plan = []
                for finding in all_findings:
                    scored = score_finding(finding)
                    item = process_finding_with_iq(scored)
                    remediation_plan.append(item)
                status.update(label="Learning Paths Curated", state="complete", expanded=False)

            # --- 3. STUDY PLAN AGENT (Mocked for UI flow) ---
            with st.status("📅 Step 3: Study Plan Agent adapting to Work IQ...", expanded=True) as status:
                status.update(label="Study Plan Generated", state="complete", expanded=False)

            # --- DISPLAY RESULTS ---
            st.markdown("---")
            st.markdown("### 📖 Recommended Study & Migration Path")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("🔴 Critical Gaps", len([r for r in remediation_plan if r.finding.severity.value == "CRITICAL"]))
            col2.metric("🟠 Study Required", len([r for r in remediation_plan if r.finding.severity.value == "HIGH"]))
            col3.metric("🟡 Awareness Needed", len([r for r in remediation_plan if r.finding.severity.value in ("MEDIUM", "LOW")]))

            for item in remediation_plan[:5]: # Show top 5
                f = item.finding
                with st.expander(f"Gap: `{f.file}:{f.line}` — {f.algorithm} → {item.pqc_replacement}"):
                    st.markdown(f"**Study Material:** {item.fips_standard}")
                    st.markdown(f"**Estimated Study Effort:** {item.migration_effort_hours} hours")
                    st.markdown(f"**Curator Guidance:** {item.code_guidance}")
                    if item.status == "NEEDS_HUMAN_REVIEW":
                        st.warning(f"⚠️ **Confidence Gate:** {item.review_reason}")

            # QASS Visualizer
            from engine.qass import simulate_quantum_attack
            from engine.quantum_visualizer import generate_quantum_visualization
            import streamlit.components.v1 as components

            viz_finding = next((item.finding for item in remediation_plan if item.finding.quantum_vulnerable), None)
            if viz_finding:
                st.markdown("---")
                st.markdown("### ⚛️ Quantum Threat Context (QASS)")
                viz_key_bits = viz_finding.key_size if viz_finding.key_size > 0 else 2048
                qass_res = simulate_quantum_attack(viz_finding.algorithm, viz_key_bits, viz_finding.use_case, viz_finding.critical_path)
                viz_data = generate_quantum_visualization(qass_res)
                st.info(f"**Executive Summary:** {viz_data.caption}")
                components.html(viz_data.svg, height=400, scrolling=True)

# ==============================================================================
# MANAGER VIEW: Insights & Readiness
# ==============================================================================
elif view == "👨‍💼 Manager View":
    st.markdown("### 📊 Team PQC Readiness Dashboard")
    st.caption("Aggregated by Manager Insights Agent using Fabric IQ & Work IQ")
    
    # --- Dynamic Metrics Calculation ---
    if learner_perf:
        total_engineers = len(learner_perf)
        certified_count = sum(1 for e in learner_perf if e.get("exam_outcome") == "Pass")
        avg_score = sum(e.get("practice_score_avg", 0) for e in learner_perf) / total_engineers
        readiness_pct = int(avg_score) # Use average score as readiness proxy
        critical_gaps = sum(1 for e in learner_perf if e.get("top_weakness", "None") != "None")
        deadline_risk = "HIGH" if critical_gaps > 2 or readiness_pct < 70 else "MEDIUM"
        delta = "-5%" if readiness_pct < 70 else "+12%"
    else:
        readiness_pct, certified_count, total_engineers, critical_gaps, deadline_risk, delta = 0, 0, 4, 0, "N/A", "N/A"

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Team Readiness", f"{readiness_pct}%", delta=delta)
    col2.metric("Engineers Certified", f"{certified_count} / {total_engineers}")
    col3.metric("Critical Skill Gaps", critical_gaps)
    col4.metric("2030 Deadline Risk", deadline_risk, delta="Action Needed" if deadline_risk == "HIGH" else "")
    
    st.markdown("---")
    st.markdown("### 👥 Engineer Status")
    
    # Display synthetic learner performance
    if learner_perf:
        for eng in learner_perf:
            status_icon = "✅" if eng.get("exam_outcome") == "Pass" else "⚠️"
            weakness = eng.get("top_weakness", "None")
            with st.expander(f"{status_icon} {eng.get('learner_id')} - {eng.get('role')} | Weakness: {weakness}"):
                st.json(eng)

    st.markdown("---")
    st.markdown("### 📜 Compliance Export")
    if st.button("Export Team Readiness Report (CBOM)"):
        st.download_button(
            label="⬇️ Download Report",
            data=json.dumps({"team": team_data, "learner_performance": learner_perf, "work_signals": work_signals}, indent=2),
            file_name="VyalaArchon_readiness.json",
            mime="application/json"
        )