import logging
import json
from typing import Any, Dict, List
from groq import Groq
from core.config import config
from core.state_manager import StateManager
from tools.revit_connector import RevitConnector

logger = logging.getLogger(__name__)


class RevitExecutorAgent:
    def __init__(self, state_manager: StateManager,
                 revit_connector: RevitConnector = None):
        self.name = "RevitExecutorAgent"
        self.state = state_manager
        self.connector = revit_connector or RevitConnector()
        self.client = Groq(api_key=config.GROQ_API_KEY)

    def _build_execution_prompt(self, clash: Dict,
                                resolution: Dict) -> str:
        return f"""You are a Revit API automation expert.
Given this clash and its resolution, determine the exact
geometric move needed to fix it.

CLASH:
- Element 1: {clash.get('element_1')} 
  (ID: {clash.get('clash_id')})
- Element 2: {clash.get('element_2')}
- Type: {clash.get('resolution', {}).get('clash_type', 'hard_clash')}
- Description: {clash.get('resolution', {}).get('resolution_summary')}

RESOLUTION:
- Action: {resolution.get('action_required')}
- Responsible: {resolution.get('responsible_discipline')} 
  element moves
- Standard: {resolution.get('reference_standard')}

Determine which element to move and by exactly how much in meters.
MEP elements (ducts, pipes) move — never structural elements.

Respond ONLY in this exact JSON:
{{
    "element_to_move": "element_name",
    "move_x_meters": 0.0,
    "move_y_meters": 0.0,
    "move_z_meters": -0.35,
    "reason": "moving duct down to clear beam"
}}"""

    def _get_move_vector(self, clash: Dict,
                         resolution: Dict) -> Dict[str, float]:
        try:
            prompt = self._build_execution_prompt(clash, resolution)
            response = self.client.chat.completions.create(
                model=config.GROQ_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a Revit API expert. "
                                   "Return only valid JSON."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=256
            )
            raw = response.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw.strip())
        except Exception as e:
            logger.error(f"Failed to get move vector: {e}")
            return {
                "element_to_move": "unknown",
                "move_x_meters": 0.0,
                "move_y_meters": 0.0,
                "move_z_meters": -0.35,
                "reason": "default downward move"
            }

    def run(self, resolutions: List[Dict[str, Any]]) -> Dict[str, Any]:
        logger.info(
            f"[{self.name}] Starting Revit execution "
            f"for {len(resolutions)} resolutions"
        )
        self.state.update(pipeline_stage="revit_execution")

        executed = []
        failed = []

        for r in resolutions:
            res = r.get("resolution", {})
            discipline = res.get("responsible_discipline", "mep")

            if discipline.lower() == "structural":
                logger.info(
                    f"[{self.name}] Skipping {r['clash_id']} — "
                    f"structural elements not auto-moved"
                )
                continue

            move_data = self._get_move_vector(r, res)
            translation = {
                "x": move_data.get("move_x_meters", 0.0),
                "y": move_data.get("move_y_meters", 0.0),
                "z": move_data.get("move_z_meters", -0.35)
            }

            element_to_move = r.get("element_1")
            if "mep" in r.get("element_1", "").lower() or \
               "duct" in r.get("element_1", "").lower() or \
               "pipe" in r.get("element_1", "").lower():
                element_id = r.get("clash_id")
            else:
                element_id = r.get("clash_id")

            success = self.connector.move_element(
                element_id=element_id,
                translation=translation,
                description=(
                    f"NexBIM fix: {r['clash_id']} — "
                    f"{res.get('resolution_summary', '')[:50]}"
                )
            )

            if success:
                executed.append({
                    "clash_id": r["clash_id"],
                    "element": element_to_move,
                    "move": translation,
                    "reason": move_data.get("reason"),
                    "status": "executed"
                })
                logger.info(
                    f"[{self.name}] Executed fix for {r['clash_id']}"
                )
            else:
                failed.append(r["clash_id"])
                logger.warning(
                    f"[{self.name}] Failed fix for {r['clash_id']}"
                )

        exec_summary = self.connector.get_execution_summary()

        self.state.log_agent_action(
            self.name,
            "execute_revit_fixes",
            (f"Executed {len(executed)} fixes in Revit "
             f"({exec_summary['mode']} mode) — "
             f"Failed: {len(failed)}"),
            "success"
        )

        logger.info(
            f"[{self.name}] Complete — "
            f"{len(executed)} fixes executed"
        )

        return {
            "success": True,
            "total_executed": len(executed),
            "total_failed": len(failed),
            "executed_fixes": executed,
            "failed_fixes": failed,
            "mode": exec_summary["mode"],
            "execution_details": exec_summary
        }