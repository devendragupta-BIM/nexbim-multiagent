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
            "report_path": None
        }

    elements = intake_result["elements"]

    # ── STAGE 2: Clash Classification ─────────────────────────────────
    logger.info("STAGE 2: Clash Classifier Agent")
    classifier = ClassifierAgent(state)
    classification_result = classifier.run(elements)

    # ── STAGE 3: AI Clash Resolution ───────────────────────────────────
    logger.info("STAGE 3: AI Clash Resolver Agent (Groq LLaMA 3.3 70B)")
    resolver = ResolverAgent(state)
    resolution_result = resolver.run(classification_result["clashes"])

    # ── STAGE 4: Compliance Check ──────────────────────────────────────
    logger.info("STAGE 4: Compliance Agent (IS + ISO Standards)")
    compliance = ComplianceAgent(state)
    compliance_result = compliance.run(elements)

    # ── STAGE 5: LOD Check ─────────────────────────────────────────────
    logger.info("STAGE 5: LOD Agent (Level of Development)")
    lod = LODAgent(state)
    lod_result = lod.run(elements)

    # ── CALCULATE HEALTH SCORE ─────────────────────────────────────────
    health_score = state.calculate_health_score()
    logger.info(f"Model Health Score: {health_score}/100")

    # ── STAGE 6: PDF Report ────────────────────────────────────────────
    logger.info("STAGE 6: Reporter Agent — Generating PDF")
    reporter = ReporterAgent(state)
    report_result = reporter.run(resolution_result.get("resolutions", []))

    # ── EXPORT AND SAVE ────────────────────────────────────────────────
    export_path = f"nexbim_state_{project_id}.json"
    state.export_state(export_path)
    summary = state.get_summary()
    memory.save(project_id, summary)

    logger.info("=" * 60)
    logger.info("ALL 6 STAGES COMPLETE")
    logger.info(json.dumps(summary, indent=2, default=str))
    logger.info("=" * 60)

    return {
        "summary": summary,
        "resolutions": resolution_result.get("resolutions", []),
        "compliance": compliance_result,
        "lod": lod_result,
        "total_cost_impact_inr": resolution_result.get("total_cost_impact_inr", 0),
        "total_schedule_impact_days": resolution_result.get("total_schedule_impact_days", 0),
        "report_path": report_result.get("report_path")
    }


if __name__ == "__main__":
    result = run_pipeline(
        model_path="sample_data/sample.ifc",
        project_name="BIM Modelling Service India — Test Project"
    )

    summary = result["summary"]
    resolutions = result["resolutions"]
    compliance = result["compliance"]
    lod = result["lod"]

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
    print(f"Compliance Issues  : {compliance.get('total_issues', 0)}")
    print(f"LOD Violations     : {lod.get('total_violations', 0)}")
    print(f"Health Score       : {summary.get('health_score')}/100")
    print(f"Cost Impact        : Rs.{result['total_cost_impact_inr']:,}")
    print(f"Schedule Impact    : {result['total_schedule_impact_days']} days")
    print(f"PDF Report         : {result.get('report_path')}")
    print("=" * 60)

    print("\nCOMPLIANCE SUMMARY:")
    print("-" * 60)
    print(f"Total Issues  : {compliance.get('total_issues', 0)}")
    print(f"Critical      : {compliance.get('critical', 0)}")
    print(f"Major         : {compliance.get('major', 0)}")

    print("\nLOD SUMMARY:")
    print("-" * 60)
    print(f"Total Violations : {lod.get('total_violations', 0)}")
    print(f"Critical         : {lod.get('critical', 0)}")
    print(f"Major            : {lod.get('major', 0)}")
    print(f"Minor            : {lod.get('minor', 0)}")

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