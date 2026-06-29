import streamlit as st
import sys
import os
import json
import tempfile
from datetime import datetime
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.state_manager import StateManager
from core.memory import AgentMemory
from agents.intake_agent import IntakeAgent
from agents.classifier_agent import ClassifierAgent
from agents.resolver_agent import ResolverAgent
from agents.compliance_agent import ComplianceAgent
from agents.lod_agent import LODAgent
from agents.reporter_agent import ReporterAgent
import uuid

st.set_page_config(
    page_title="NexBIM — Multi-Agent BIM Coordination",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #1B3A6B 0%, #2E86AB 100%);
        padding: 2rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #1B3A6B;
    }
    .metric-label {
        font-size: 0.8rem;
        color: #7F8C8D;
        margin-top: 4px;
    }
    .stage-complete {
        background: #d4edda;
        border: 1px solid #27AE60;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        color: #155724;
        margin: 4px 0;
    }
    .stage-running {
        background: #fff3cd;
        border: 1px solid #F39C12;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        color: #856404;
        margin: 4px 0;
    }
    .clash-critical {
        background: #f8d7da;
        border-left: 4px solid #E74C3C;
        padding: 1rem;
        border-radius: 0 8px 8px 0;
        margin: 8px 0;
    }
    .clash-major {
        background: #fff3cd;
        border-left: 4px solid #F39C12;
        padding: 1rem;
        border-radius: 0 8px 8px 0;
        margin: 8px 0;
    }
    .clash-minor {
        background: #d4edda;
        border-left: 4px solid #27AE60;
        padding: 1rem;
        border-radius: 0 8px 8px 0;
        margin: 8px 0;
    }
    .agent-log-row {
        background: #F4F6F9;
        border-radius: 6px;
        padding: 0.5rem 1rem;
        margin: 4px 0;
        font-size: 0.85rem;
    }
    .health-good { color: #27AE60; font-size: 2.5rem; font-weight: 700; }
    .health-warn { color: #F39C12; font-size: 2.5rem; font-weight: 700; }
    .health-bad  { color: #E74C3C; font-size: 2.5rem; font-weight: 700; }
    .stButton > button {
        background: #1B3A6B;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 2rem;
        font-size: 1rem;
        font-weight: 600;
        width: 100%;
    }
    .stButton > button:hover {
        background: #2E86AB;
    }
</style>
""", unsafe_allow_html=True)


def run_pipeline_streamlit(model_path: str, project_name: str,
                           status_container, progress_bar):
    project_id = f"NEXBIM-{str(uuid.uuid4())[:8].upper()}"
    state = StateManager(project_id=project_id, project_name=project_name)
    memory = AgentMemory()
    results = {}

    stages = [
        "Model Intake",
        "Clash Detection",
        "AI Resolution",
        "Compliance Check",
        "LOD Validation",
        "Report Generation"
    ]

    def update_status(stage_idx, stage_name, done=False):
        with status_container:
            st.markdown("**Pipeline Progress:**")
            for i, s in enumerate(stages):
                if i < stage_idx:
                    st.markdown(
                        f'<div class="stage-complete">✅ {s}</div>',
                        unsafe_allow_html=True
                    )
                elif i == stage_idx:
                    if done:
                        st.markdown(
                            f'<div class="stage-complete">✅ {s}</div>',
                            unsafe_allow_html=True
                        )
                    else:
                        st.markdown(
                            f'<div class="stage-running">⚙️ {s} — Running...</div>',
                            unsafe_allow_html=True
                        )
                else:
                    st.markdown(
                        f'<div style="padding:0.5rem 1rem;margin:4px 0;'
                        f'color:#999;border-radius:8px;background:#f5f5f5;">'
                        f'⬜ {s}</div>',
                        unsafe_allow_html=True
                    )
        progress_bar.progress((stage_idx + (1 if done else 0.5)) / len(stages))

    # Stage 1
    update_status(0, "Model Intake")
    intake = IntakeAgent(state)
    intake_result = intake.run(model_path)
    results["intake"] = intake_result
    update_status(0, "Model Intake", done=True)

    if not intake_result["success"]:
        st.error("Pipeline failed at intake stage")
        return None, None

    elements = intake_result["elements"]

    # Stage 2
    update_status(1, "Clash Detection")
    classifier = ClassifierAgent(state)
    classification_result = classifier.run(elements)
    results["classification"] = classification_result
    update_status(1, "Clash Detection", done=True)

    # Stage 3
    update_status(2, "AI Resolution")
    resolver = ResolverAgent(state)
    resolution_result = resolver.run(classification_result["clashes"])
    results["resolution"] = resolution_result
    update_status(2, "AI Resolution", done=True)

    # Stage 4
    update_status(3, "Compliance Check")
    compliance = ComplianceAgent(state)
    compliance_result = compliance.run(elements)
    results["compliance"] = compliance_result
    update_status(3, "Compliance Check", done=True)

    # Stage 5
    update_status(4, "LOD Validation")
    lod = LODAgent(state)
    lod_result = lod.run(elements)
    results["lod"] = lod_result
    update_status(4, "LOD Validation", done=True)

    # Health score
    state.calculate_health_score()

    # Stage 6
    update_status(5, "Report Generation")
    reporter = ReporterAgent(state)
    report_result = reporter.run(resolution_result.get("resolutions", []))
    results["report"] = report_result
    update_status(5, "Report Generation", done=True)

    progress_bar.progress(1.0)

    export_path = f"nexbim_state_{project_id}.json"
    state.export_state(export_path)
    summary = state.get_summary()
    memory.save(project_id, summary)

    return summary, results


def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1 style="margin:0;font-size:2.5rem;">🏗️ NexBIM</h1>
        <p style="margin:0.5rem 0 0;font-size:1.1rem;opacity:0.9;">
            Multi-Agent AI System for BIM Coordination
        </p>
        <p style="margin:0.3rem 0 0;font-size:0.85rem;opacity:0.7;">
            Powered by Groq LLaMA 3.3 70B · ISO 19650 · IS Codes
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.markdown("## ⚙️ Project Setup")
        st.markdown("---")

        project_name = st.text_input(
            "Project Name",
            value="BIM Coordination Project",
            placeholder="Enter your project name"
        )

        st.markdown("### 📁 Upload BIM Model")
        uploaded_file = st.file_uploader(
            "Upload IFC file",
            type=["ifc"],
            help="Upload your IFC BIM model file"
        )

        use_sample = st.checkbox(
            "Use sample data (demo mode)",
            value=True,
            help="Run with built-in mock BIM data"
        )

        st.markdown("---")
        st.markdown("### 🤖 Agents")
        st.markdown("""
        <div style="font-size:0.85rem;color:#555;">
        ✅ Intake Agent<br>
        ✅ Classifier Agent<br>
        ✅ Resolver Agent (AI)<br>
        ✅ Compliance Agent<br>
        ✅ LOD Agent<br>
        ✅ Reporter Agent
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 📋 Standards")
        st.markdown("""
        <div style="font-size:0.8rem;color:#555;">
        • IS 456:2000 — Concrete<br>
        • IS 800:2007 — Steel<br>
        • IS 1893:2016 — Seismic<br>
        • IS 2052:1983 — Pipes<br>
        • IS 10401:2018 — Ducts<br>
        • NBC 2016 — Building Code<br>
        • ISO 19650 — BIM Standard
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        run_button = st.button("🚀 Run NexBIM Pipeline")

    # Main content
    if "results" not in st.session_state:
        st.session_state.results = None
        st.session_state.summary = None

    if run_button:
        if not project_name:
            st.error("Please enter a project name")
            st.stop()

        if uploaded_file:
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=".ifc"
            ) as tmp:
                tmp.write(uploaded_file.getvalue())
                model_path = tmp.name
        elif use_sample:
            model_path = "sample_data/sample.ifc"
        else:
            st.error("Please upload an IFC file or enable demo mode")
            st.stop()

        st.markdown("## ⚙️ Running Pipeline")
        status_container = st.container()
        progress_bar = st.progress(0)

        with st.spinner("NexBIM agents working..."):
            summary, results = run_pipeline_streamlit(
                model_path=model_path,
                project_name=project_name,
                status_container=status_container,
                progress_bar=progress_bar
            )

        if summary:
            st.session_state.summary = summary
            st.session_state.results = results
            st.success("✅ Pipeline complete! Scroll down to see results.")
            st.rerun()

    if st.session_state.summary:
        summary = st.session_state.summary
        results = st.session_state.results

        st.markdown("## 📊 Executive Summary")
        c1, c2, c3, c4, c5, c6 = st.columns(6)

        def metric_card(col, value, label, color="#1B3A6B"):
            col.markdown(f"""
            <div class="metric-card">
                <div class="metric-value" style="color:{color};">{value}</div>
                <div class="metric-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

        health = summary.get("health_score", 0)
        health_color = (
            "#27AE60" if health >= 75 else
            "#F39C12" if health >= 50 else
            "#E74C3C"
        )

        metric_card(c1, summary.get("total_elements", 0),
                    "Total Elements", "#1B3A6B")
        metric_card(c2, summary.get("total_clashes", 0),
                    "Clashes Found", "#E74C3C")
        metric_card(c3, summary.get("resolved_clashes", 0),
                    "Resolved", "#27AE60")
        metric_card(c4, summary.get("compliance_issues", 0),
                    "Compliance Issues", "#F39C12")
        metric_card(c5, summary.get("lod_violations", 0),
                    "LOD Violations", "#E74C3C")
        metric_card(c6, f"{health}/100",
                    "Health Score", health_color)

        st.markdown("---")

        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("### 💰 Project Impact")
            cost = summary.get("total_cost_impact", 0)
            days = summary.get("schedule_impact_days", 0)
            disciplines = ", ".join(summary.get("disciplines", []))

            st.info(f"**Cost Impact:** Rs.{cost:,.0f}")
            st.warning(f"**Schedule Impact:** {days} working days")
            st.success(f"**Disciplines:** {disciplines}")
            st.info(f"**Project ID:** {summary.get('project_id')}")

        with col2:
            st.markdown("### 🎯 Health Score")
            health_class = (
                "health-good" if health >= 75 else
                "health-warn" if health >= 50 else
                "health-bad"
            )
            st.markdown(
                f'<div class="{health_class}" '
                f'style="text-align:center;padding:1rem;">'
                f'{health}/100</div>',
                unsafe_allow_html=True
            )
            if health >= 75:
                st.success("Model is in good health")
            elif health >= 50:
                st.warning("Model needs attention")
            else:
                st.error("Model has critical issues")

        st.markdown("---")
        st.markdown("## 🔴 Clash Resolutions")

        resolutions = results.get("resolution", {}).get("resolutions", [])
        if resolutions:
            for r in resolutions:
                res = r.get("resolution", {})
                sev = r.get("severity", "minor")
                css_class = f"clash-{sev}"

                st.markdown(f"""
                <div class="{css_class}">
                    <strong>{r.get('clash_id')} — {sev.upper()}</strong><br>
                    <strong>Elements:</strong> {r.get('element_1')} vs {r.get('element_2')}<br>
                    <strong>Fix:</strong> {res.get('resolution_summary', '—')}<br>
                    <strong>Action:</strong> {res.get('action_required', '—')}<br>
                    <strong>Standard:</strong> {res.get('reference_standard', '—')}<br>
                    <strong>Cost:</strong> Rs.{res.get('estimated_cost_impact_inr', 0):,} |
                    <strong>Days:</strong> {res.get('estimated_schedule_impact_days', 0)} |
                    <strong>Priority:</strong> {res.get('priority', '—').upper()}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("No clashes found")

        st.markdown("---")

        col3, col4 = st.columns(2)

        with col3:
            st.markdown("## 📋 Compliance Issues")
            comp_list = summary.get("compliance_issues_list", [])
            if comp_list:
                for issue in comp_list:
                    sev = issue.get("severity", "major")
                    color = (
                        "#E74C3C" if sev == "critical" else
                        "#F39C12" if sev == "major" else
                        "#27AE60"
                    )
                    with st.expander(
                        f"{issue.get('standard')} — {issue.get('clause')}"
                    ):
                        st.markdown(
                            f"**Severity:** :{color}[{sev.upper()}]"
                        )
                        st.markdown(
                            f"**Issue:** {issue.get('description')}"
                        )
                        st.markdown(
                            f"**Fix:** {issue.get('recommendation')}"
                        )
            else:
                st.success("No compliance issues found")

        with col4:
            st.markdown("## 📐 LOD Violations")
            lod_list = summary.get("lod_violations_list", [])
            if lod_list:
                for v in lod_list:
                    sev = v.get("severity", "major")
                    missing = ", ".join(v.get("missing_attributes", []))
                    with st.expander(
                        f"{v.get('element_name')} — LOD {v.get('required_lod')} required"
                    ):
                        st.markdown(f"**Type:** {v.get('element_type')}")
                        st.markdown(
                            f"**LOD:** Required {v.get('required_lod')} "
                            f"/ Actual {v.get('actual_lod')}"
                        )
                        st.markdown(
                            f"**Completeness:** {v.get('completeness')}%"
                        )
                        st.markdown(f"**Severity:** {sev.upper()}")
                        st.markdown(f"**Missing:** {missing}")
            else:
                st.success("All elements meet LOD requirements")

        st.markdown("---")
        st.markdown("## 📜 Agent Execution Log")

        agent_logs = summary.get("agent_logs", [])
        for log in agent_logs:
            ts = log.get("timestamp", "")
            if "T" in ts:
                ts = ts.split("T")[1][:8]
            status = log.get("status", "").upper()
            icon = "✅" if status == "SUCCESS" else "❌"
            st.markdown(f"""
            <div class="agent-log-row">
                {icon} <strong>{log.get('agent')}</strong> —
                {log.get('action')} |
                {log.get('result')} |
                <span style="color:#999;">{ts}</span>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("## 📄 Download Report")

        report_path = results.get("report", {}).get("report_path")
        if report_path and os.path.exists(report_path):
            with open(report_path, "rb") as f:
                pdf_bytes = f.read()
            st.download_button(
                label="⬇️ Download PDF Coordination Report",
                data=pdf_bytes,
                file_name=f"NexBIM_Report_{summary.get('project_id')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        else:
            st.warning("PDF report not found")

        st.markdown("---")
        st.markdown("""
        <div style="text-align:center;color:#999;font-size:0.8rem;">
            NexBIM Multi-Agent System v1.0 |
            Powered by Groq LLaMA 3.3 70B |
            Built by Devendra Gupta
        </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()