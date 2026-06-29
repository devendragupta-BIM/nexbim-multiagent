import logging
from typing import Any, Dict, List
from core.state_manager import StateManager, ClashRecord
from tools.clash_detector import detect_clashes

logger = logging.getLogger(__name__)

class ClassifierAgent:
    def __init__(self, state_manager: StateManager):
        self.name = "ClassifierAgent"
        self.state = state_manager

    def run(self, elements: List[Dict[str, Any]]) -> Dict[str, Any]:
        logger.info(f"[{self.name}] Starting clash detection")
        self.state.update(pipeline_stage="classification")

        raw_clashes = detect_clashes(elements)

        critical = [c for c in raw_clashes if c["severity"] == "critical"]
        major = [c for c in raw_clashes if c["severity"] == "major"]
        minor = [c for c in raw_clashes if c["severity"] == "minor"]

        for clash_data in raw_clashes:
            clash_record = ClashRecord(
                clash_id=clash_data["clash_id"],
                element_1_id=clash_data["element_1_id"],
                element_2_id=clash_data["element_2_id"],
                element_1_discipline=clash_data["element_1_discipline"],
                element_2_discipline=clash_data["element_2_discipline"],
                clash_type=clash_data["clash_type"],
                severity=clash_data["severity"],
                location=clash_data.get("location", {}),
                description=clash_data["description"],
                status="open"
            )
            self.state.add_clash(clash_record)

        self.state.log_agent_action(
            self.name,
            "detect_and_classify",
            (f"Found {len(raw_clashes)} clashes — "
             f"Critical: {len(critical)}, "
             f"Major: {len(major)}, "
             f"Minor: {len(minor)}"),
            "success"
        )

        logger.info(f"[{self.name}] Complete — {len(raw_clashes)} clashes registered")
        return {
            "success": True,
            "total_clashes": len(raw_clashes),
            "critical": len(critical),
            "major": len(major),
            "minor": len(minor),
            "clashes": raw_clashes
        }