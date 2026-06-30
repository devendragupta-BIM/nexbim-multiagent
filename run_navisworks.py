import logging
import uuid
import json
from datetime import datetime
from core.state_manager import StateManager
from core.memory import AgentMemory
from agents.navisworks_agent import NavisworksAgent
from agents.reporter_agent import ReporterAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(
            f"nexbim_nwc_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        ),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("NexBIM-Navisworks")


def run_navisworks_pipeline(
    xml_path: str,
    project_name: str = "NexBIM Navisworks Project"
) -> dict:
    logger.info("=" * 60)
    logger.info("NexBIM — Navisworks Clash Report Pipeline")
    logger.info("=" * 60)

    project_id = f"NWC-{str(uuid.uuid4())[:8].upper()}"
    state = StateManager(project_id=project_id, project_name=project_name)
    memory = AgentMemory()

    # Stage 1 — Parse and Resolve Navisworks Report
    logger.info("STAGE 1: Navisworks Agent — Parse + AI Resolution")
    nwc_agent = NavisworksAgent(state)
    nwc_result = nwc_agent.run(xml_path)

    if not nwc_result["success"]:
        logger.error("Pipeline failed at Navisworks stage")
        return {"summary": state.get_summary(), "resolutions": []}

    # Calculate health score
    state.calculate_health_score()

    # Stage 2 — Generate PDF Report
    logger.info("STAGE 2: Reporter Agent — Generating PDF")
    reporter = ReporterAgent(state)
    report_result = reporter.run(nwc_result.get("resolutions", []))

    # Export and save
    export_path = f"nexbim_nwc_state_{project_id}.json"
    state.export_state(export_path)
    summary = state.get_summary()
    memory.save(project_id, summary)

    logger.info("=" * 60)
    logger.info("NAVISWORKS PIPELINE COMPLETE")
    logger.info("=" * 60)

    return {
        "summary": summary,
        "resolutions": nwc_result.get("resolutions", []),
        "total_cost_impact_inr": nwc_result.get("total_cost_impact_inr", 0),
        "total_schedule_impact_days": nwc_result.get(
            "total_schedule_impact_days", 0
        ),
        "report_path": report_result.get("report_path")
    }


if __name__ == "__main__":
    result = run_navisworks_pipeline(
        xml_path="sample_data/sample_clash_report.xml",
        project_name="BIM Modelling Service India — Navisworks Test"
    )

    summary = result["summary"]
    resolutions = result["resolutions"]

    print("\n" + "=" * 60)
    print("NEXBIM NAVISWORKS PIPELINE RESULTS")
    print("=" * 60)
    print(f"Project ID       : {summary.get('project_id')}")
    print(f"Total Clashes    : {summary.get('total_clashes')}")
    print(f"Resolved         : {summary.get('resolved_clashes')}")
    print(f"Cost Impact      : Rs.{result['total_cost_impact_inr']:,}")
    print(f"Schedule Impact  : {result['total_schedule_impact_days']} days")
    print(f"PDF Report       : {result.get('report_path')}")
    print("=" * 60)

    print("\nAI RESOLUTIONS FROM NAVISWORKS REPORT:")
    print("-" * 60)
    for r in resolutions:
        res = r.get("resolution", {})
        print(f"\nClash ID   : {r['clash_id']}")
        print(f"Test       : {r['test_name']}")
        print(f"Severity   : {r['severity'].upper()}")
        print(f"Distance   : {r['distance_mm']:.0f}mm")
        print(f"Elements   : {r['element_1']} vs {r['element_2']}")
        print(f"Fix        : {res.get('resolution_summary', '—')}")
        print(f"Action     : {res.get('action_required', '—')}")
        print(f"By         : {res.get('responsible_discipline','').upper()}")
        print(f"Standard   : {res.get('reference_standard', '—')}")
        print(f"NWC Action : {res.get('navisworks_action', '—')}")
        print(f"Cost       : Rs.{res.get('estimated_cost_impact_inr',0):,}")
        print(f"Days       : {res.get('estimated_schedule_impact_days',0)}")
        print("-" * 60)