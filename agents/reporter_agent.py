import logging
import os
from typing import Any, Dict, List
from core.state_manager import StateManager
from tools.report_generator import generate_report

logger = logging.getLogger(__name__)


class ReporterAgent:
    def __init__(self, state_manager: StateManager):
        self.name = "ReporterAgent"
        self.state = state_manager

    def run(self, resolutions: List[Dict[str, Any]]) -> Dict[str, Any]:
        logger.info(f"[{self.name}] Generating professional PDF report")
        self.state.update(pipeline_stage="reporting")

        summary = self.state.get_summary()
        project_id = summary.get("project_id", "NEXBIM")
        output_path = f"NexBIM_Report_{project_id}.pdf"

        try:
            path = generate_report(
                project_summary=summary,
                resolutions=resolutions,
                output_path=output_path
            )
            self.state.update(final_report_path=path)
            self.state.log_agent_action(
                self.name,
                "generate_pdf_report",
                f"Report saved to {path}",
                "success"
            )
            logger.info(f"[{self.name}] Report complete — {path}")
            return {"success": True, "report_path": path}

        except Exception as e:
            logger.error(f"[{self.name}] Report generation failed: {e}")
            self.state.log_agent_action(
                self.name,
                "generate_pdf_report",
                f"Failed: {e}",
                "error"
            )
            return {"success": False, "error": str(e)}