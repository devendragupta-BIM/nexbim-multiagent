import logging
import sys
import os
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger("NexBIM-AutoRouter")


def detect_input_type(file_path: str) -> str:
    """
    The Orchestrator inspects the file itself and decides which
    pipeline to run — this is autonomous routing, not a manual
    mode switch. It checks extension first, then peeks at content
    if the extension is ambiguous.
    """
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == ".ifc":
        logger.info(
            f"[AutoRouter] File extension .ifc detected — "
            f"routing to IFC pipeline"
        )
        return "ifc"

    if ext == ".xml":
        logger.info(
            f"[AutoRouter] File extension .xml detected — "
            f"inspecting content to confirm Navisworks format"
        )
        try:
            with open(file_path, "r", encoding="utf-8",
                     errors="ignore") as f:
                head = f.read(2000)
            if any(tag in head.lower() for tag in
                  ["clashtest", "clashresult", "batchtest"]):
                logger.info(
                    "[AutoRouter] Confirmed Navisworks clash "
                    "report structure — routing to Navisworks pipeline"
                )
                return "navisworks"
            else:
                logger.warning(
                    "[AutoRouter] XML file does not match known "
                    "Navisworks structure — attempting Navisworks "
                    "pipeline anyway as XML is its only known format"
                )
                return "navisworks"
        except Exception as e:
            logger.error(f"[AutoRouter] Could not inspect XML: {e}")
            return "navisworks"

    logger.warning(
        f"[AutoRouter] Unrecognized extension '{ext}' — "
        f"defaulting to IFC pipeline. Supported formats: .ifc, .xml"
    )
    return "ifc"


def run(file_path: str, project_name: str = "NexBIM Project") -> dict:
    logger.info("=" * 60)
    logger.info("NexBIM Auto-Router — Inspecting Input")
    logger.info("=" * 60)

    if not os.path.exists(file_path):
        logger.warning(
            f"File not found at {file_path} — "
            f"falling back to IFC demo mode with mock data"
        )
        input_type = "ifc"
    else:
        input_type = detect_input_type(file_path)

    logger.info(
        f"[AutoRouter] Decision: routing to "
        f"{'IFC' if input_type == 'ifc' else 'NAVISWORKS'} pipeline"
    )
    logger.info("=" * 60)

    if input_type == "navisworks":
        from run_navisworks import run_navisworks_pipeline
        return run_navisworks_pipeline(
            xml_path=file_path,
            project_name=project_name
        )
    else:
        from main import run_pipeline
        return run_pipeline(
            model_path=file_path,
            project_name=project_name
        )


if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = "sample_data/sample.ifc"

    project_name = sys.argv[2] if len(sys.argv) > 2 else "NexBIM Project"

    result = run(file_path, project_name)

    summary = result.get("summary", {})
    print("\n" + "=" * 60)
    print("NEXBIM AUTO-ROUTED PIPELINE — FINAL RESULT")
    print("=" * 60)
    print(f"Project ID       : {summary.get('project_id')}")
    print(f"Total Clashes    : {summary.get('total_clashes')}")
    print(f"Resolved         : {summary.get('resolved_clashes')}")
    print(f"Health Score     : {summary.get('health_score')}/100")
    print(f"Report           : {result.get('report_path')}")
    if result.get("orchestrator_verdict"):
        print(f"\nVerdict: {result.get('orchestrator_verdict')}")
    print("=" * 60)