import logging
import uuid
import json
from datetime import datetime
from core.state_manager import StateManager
from core.memory import AgentMemory
from agents.intake_agent import IntakeAgent
from agents.classifier_agent import ClassifierAgent
from agents.resolver_agent import ResolverAgent
from agents.compliance_agent import ComplianceAgent
from agents.lod_agent import LODAgent
from agents.reporter_agent import ReporterAgent
from agents.orchestrator import Orchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(
            f"nexbim_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        ),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("NexBIM")


def run_pipeline(model_path: str, project_name: str = "NexBIM Project") -> dict:
    logger.info("=" * 60)
    logger.info("NexBIM Multi-Agent System v1.0 — Pipeline Starting")
    logger.info("=" * 60)

    project_id = f"NEXBIM-{str(uuid.uuid4())[:8].upper()}"
    state = StateManager(project_id=project_id, project_name=project_name)
    memory = AgentMemory()

    orchestrator = Orchestrator(state)
    orchestrator.think(
        "Pipeline initiated. Beginning model intake before any "
        "coordination decisions can be made."
    )

    # ── STAGE 1: Model Intake ──────────────────────────────────────────
    logger.info("STAGE 1: Model Intake Agent")
    intake = IntakeAgent(state)
    intake_result = intake.run(model_path)

    if not intake_result["success"]:
        logger.error("Pipeline failed at intake stage")
        return {
            "summary": state.get_summary(),
            "resolutions": [],
            "total_cost_impact_inr": 0,
            "total_schedule_impact_days": 0,
            "report_path": None,
            "orchestrator_verdict": "Pipeline failed at intake stage.",
            "reasoning_trace": orchestrator.get_full_trace()
        }

    elements = intake_result["elements"]
    orchestrator.agent_speaks(
        "IntakeAgent", "Orchestrator",
        f"Parsed {len(elements)} elements across "
        f"{len(intake_result['disciplines'])} disciplines. "
        f"Ready for clash analysis.",
        {"element_count": len(elements)}
    )

    # ── STAGE 2: Clash Classification ─────────────────────────────────
    logger.info("STAGE 2: Clash Classifier Agent")
    classifier = ClassifierAgent(state)
    classification_result = classifier.run(elements)

    if not classification_result["success"]:
        logger.error("Pipeline failed at classification stage")
        return {
            "summary": state.get_summary(),
            "resolutions": [],
            "total_cost_impact_inr": 0,
            "total_schedule_impact_days": 0,
            "report_path": None,
            "orchestrator_verdict": "Pipeline failed at classification stage.",
            "reasoning_trace": orchestrator.get_full_trace()
        }

    orchestrator.agent_speaks(
        "ClassifierAgent", "Orchestrator",
        f"Found {classification_result['total_clashes']} clashes — "
        f"{classification_result['critical']} critical, "
        f"{classification_result['major']} major, "
        f"{classification_result['minor']} minor.",
        classification_result
    )

    routing = orchestrator.decide_severity_routing(
        classification_result["clashes"]
    )

    # ── STAGE 3: AI Clash Resolution ───────────────────────────────────
    logger.info("STAGE 3: AI Clash Resolver Agent (Groq LLaMA 3.3 70B)")
    resolver = ResolverAgent(state)
    resolution_result = resolver.run(classification_result["clashes"])

    if not resolution_result["success"]:
        logger.error("Pipeline failed at resolution stage")
        return {
            "summary": state.get_summary(),
            "resolutions": [],
            "total_cost_impact_inr": 0,
            "total_schedule_impact_days": 0,
            "report_path": None,
            "orchestrator_verdict": "Pipeline failed at resolution stage.",
            "reasoning_trace": orchestrator.get_full_trace()
        }

    orchestrator.agent_speaks(
        "ResolverAgent", "Orchestrator",
        f"Generated {resolution_result['total_resolved']} resolutions. "
        f"Total estimated impact: "
        f"Rs.{resolution_result['total_cost_impact_inr']:,} "
        f"and {resolution_result['total_schedule_impact_days']} days.",
        {"resolved": resolution_result["total_resolved"]}
    )

    # ── STAGE 4: Compliance Check ──────────────────────────────────────
    logger.info("STAGE 4: Compliance Agent (IS + ISO Standards)")
    compliance = ComplianceAgent(state)
    compliance_result = compliance.run(elements)

    orchestrator.agent_speaks(
        "ComplianceAgent", "Orchestrator",
        f"Checked against 8 standards. Found "
        f"{compliance_result['total_issues']} issues "
        f"({compliance_result['critical']} critical, "
        f"{compliance_result['major']} major).",
        compliance_result
    )

    for r in resolution_result.get("resolutions", []):
        conflict = orchestrator.review_resolution_conflict(
            r.get("resolution", {}),
            compliance_result.get("issues", [])
        )
        if conflict.get("conflict"):
            orchestrator.think(
                f"Resolution for {r['clash_id']} flagged for review — "
                f"overlaps with {len(conflict['related_issues'])} "
                f"existing compliance findings in the same discipline."
            )

    # ── STAGE 5: LOD Check ─────────────────────────────────────────────
    logger.info("STAGE 5: LOD Agent (Level of Development)")
    lod = LODAgent(state)
    lod_result = lod.run(elements)

    orchestrator.agent_speaks(
        "LODAgent", "Orchestrator",
        f"Validated LOD across all elements. "
        f"{lod_result['total_violations']} violations found, "
        f"{lod_result['critical']} critical.",
        lod_result
    )

    # ── HEALTH SCORE ────────────────────────────────────────────────────
    health_score = state.calculate_health_score()
    orchestrator.think(
        f"All agents reported. Computing composite health score from "
        f"clash severity, compliance gaps, and LOD completeness. "
        f"Final score: {health_score}/100."
    )

    # ── STAGE 6: PDF Report ────────────────────────────────────────────
    logger.info("STAGE 6: Reporter Agent — Generating PDF")
    reporter = ReporterAgent(state)
    report_result = reporter.run(resolution_result.get("resolutions", []))

    # ── EXPORT AND SAVE ────────────────────────────────────────────────
    export_path = f"nexbim_state_{project_id}.json"
    state.export_state(export_path)
    summary = state.get_summary()

    verdict = orchestrator.synthesize_final_verdict(summary)
    trace = orchestrator.get_full_trace()

    memory.save(project_id, summary)

    logger.info("=" * 60)
    logger.info("ORCHESTRATOR FINAL VERDICT:")
    logger.info(verdict)
    logger.info("=" * 60)
    logger.info("ALL 6 STAGES COMPLETE")
    logger.info(json.dumps(summary, indent=2, default=str))
    logger.info("=" * 60)

    return {
        "summary": summary,
        "resolutions": resolution_result.get("resolutions", []),
        "total_cost_impact_inr": resolution_result.get(
            "total_cost_impact_inr", 0
        ),
        "total_schedule_impact_days": resolution_result.get(
            "total_schedule_impact_days", 0
        ),
        "report_path": report_result.get("report_path"),
        "orchestrator_verdict": verdict,
        "reasoning_trace": trace
    }


if __name__ == "__main__":
    result = run_pipeline(
        model_path="sample_data/sample.ifc",
        project_name="BIM Modelling Service India — Test Project"
    )

    summary = result["summary"]
    resolutions = result["resolutions"]

    print("\n" + "=" * 60)
    print("NEXBIM MULTI-AGENT PIPELINE RESULTS")
    print("=" * 60)
    print(f"Project ID         : {summary.get('project_id')}")
    print(f"Project Name       : {summary.get('project_name')}")
    print(f"Total Elements     : {summary.get('total_elements')}")
    print(f"Disciplines        : {', '.join(summary.get('disciplines', []))}")
    print(f"Total Clashes      : {summary.get('total_clashes')}")
    print(f"Resolved Clashes   : {summary.get('resolved_clashes')}")
    print(f"Open Clashes       : {summary.get('open_clashes')}")
    print(f"Compliance Issues  : {summary.get('compliance_issues')}")
    print(f"LOD Violations     : {summary.get('lod_violations')}")
    print(f"Health Score       : {summary.get('health_score')}/100")
    print(f"Cost Impact        : Rs.{result['total_cost_impact_inr']:,}")
    print(f"Schedule Impact    : {result['total_schedule_impact_days']} days")
    print(f"PDF Report         : {result.get('report_path')}")
    print("=" * 60)

    print("\n" + "=" * 60)
    print("ORCHESTRATOR FINAL VERDICT")
    print("=" * 60)
    print(result.get("orchestrator_verdict", ""))
    print("=" * 60)

    print("\nAGENT COMMUNICATION LOG:")
    print("-" * 60)
    for msg in result.get("reasoning_trace", {}).get("agent_messages", []):
        print(f"[{msg['from']} → {msg['to']}] {msg['message']}")
    print("-" * 60)

    print("\nORCHESTRATOR REASONING TRACE:")
    print("-" * 60)
    for thought in result.get("reasoning_trace", {}).get("reasoning_trace", []):
        print(f"[{thought['agent']}] {thought['thought']}")
    print("-" * 60)

    print("\nAI CLASH RESOLUTIONS:")
    print("-" * 60)
    for r in resolutions:
        res = r.get("resolution", {})
        print(f"\nClash ID   : {r['clash_id']}")
        print(f"Severity   : {r['severity'].upper()}")
        print(f"Elements   : {r['element_1']} vs {r['element_2']}")
        print(f"Fix        : {res.get('resolution_summary', '—')}")
        print(f"By         : {res.get('responsible_discipline', '—').upper()} team")
        print(f"Standard   : {res.get('reference_standard', '—')}")
        print(f"Cost       : Rs.{res.get('estimated_cost_impact_inr', 0):,}")
        print(f"Days       : {res.get('estimated_schedule_impact_days', 0)} days")
        print("-" * 60)

    if result.get("report_path"):
        print(f"\nPDF report saved: {result['report_path']}")