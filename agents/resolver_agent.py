import logging
import json
from typing import Any, Dict, List
from groq import Groq
from core.config import config
from core.state_manager import StateManager

logger = logging.getLogger(__name__)


class ResolverAgent:
    def __init__(self, state_manager: StateManager):
        self.name = "ResolverAgent"
        self.state = state_manager
        self.client = Groq(api_key=config.GROQ_API_KEY)

    def _build_prompt(self, clash: Dict[str, Any]) -> str:
        return f"""You are a senior BIM coordination engineer with 15 years of experience
resolving MEP, structural, and architectural clashes in commercial construction projects.
You follow ISO 19650 standards and Indian construction codes (IS standards).

Analyze this BIM clash and provide a specific, actionable resolution:

CLASH DETAILS:
- Clash ID: {clash.get('clash_id')}
- Type: {clash.get('clash_type')}
- Severity: {clash.get('severity').upper()}
- Element 1: {clash.get('element_1_name')} ({clash.get('element_1_discipline')}) - Type: {clash.get('element_1_type')}
- Element 2: {clash.get('element_2_name')} ({clash.get('element_2_discipline')}) - Type: {clash.get('element_2_type')}
- Description: {clash.get('description')}
- Location: {json.dumps(clash.get('location', {}))}

Respond ONLY in this exact JSON format with no extra text:
{{
    "resolution_summary": "One clear sentence describing the fix",
    "responsible_discipline": "which discipline makes the change (mep/structural/architectural)",
    "action_required": "specific action to take",
    "alternative_solution": "backup solution if primary fails",
    "estimated_cost_impact_inr": 50000,
    "estimated_schedule_impact_days": 2,
    "priority": "immediate/this_week/this_month",
    "reference_standard": "relevant IS or ISO standard",
    "notes": "any additional technical notes"
}}"""

    def _call_groq(self, prompt: str) -> Dict[str, Any]:
        try:
            response = self.client.chat.completions.create(
                model=config.GROQ_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert BIM coordination engineer. Always respond with valid JSON only. No extra text."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=1024
            )
            raw = response.choices[0].message.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw.strip())
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return self._fallback_resolution()
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return self._fallback_resolution()

    def _fallback_resolution(self) -> Dict[str, Any]:
        return {
            "resolution_summary": "Manual review required by BIM coordinator",
            "responsible_discipline": "mep",
            "action_required": "Review clash in Navisworks and coordinate with discipline leads",
            "alternative_solution": "Schedule coordination meeting with all discipline engineers",
            "estimated_cost_impact_inr": 50000,
            "estimated_schedule_impact_days": 2,
            "priority": "this_week",
            "reference_standard": "ISO 19650-2",
            "notes": "Automated resolution unavailable — manual coordination required"
        }

    def run(self, clashes: List[Dict[str, Any]]) -> Dict[str, Any]:
        logger.info(f"[{self.name}] Starting resolution for {len(clashes)} clashes")
        self.state.update(pipeline_stage="resolution")

        resolved = []
        failed = []
        total_cost = 0
        total_days = 0

        critical = [c for c in clashes if c["severity"] == "critical"]
        major = [c for c in clashes if c["severity"] == "major"]
        minor = [c for c in clashes if c["severity"] == "minor"]
        priority_order = critical + major + minor

        for clash in priority_order:
            logger.info(
                f"[{self.name}] Resolving {clash['clash_id']} "
                f"({clash['severity'].upper()})"
            )
            prompt = self._build_prompt(clash)
            resolution = self._call_groq(prompt)

            cost = resolution.get("estimated_cost_impact_inr", 0)
            days = resolution.get("estimated_schedule_impact_days", 0)
            total_cost += cost
            total_days += days

            self.state.resolve_clash(
                clash_id=clash["clash_id"],
                resolution=resolution.get("resolution_summary", ""),
                agent_name=self.name,
                cost_impact=cost,
                schedule_impact=days
            )

            resolved.append({
                "clash_id": clash["clash_id"],
                "severity": clash["severity"],
                "element_1": clash["element_1_name"],
                "element_2": clash["element_2_name"],
                "resolution": resolution
            })

            logger.info(
                f"[{self.name}] Resolved {clash['clash_id']} — "
                f"Cost: Rs.{cost:,} | Days: {days}"
            )

        self.state.log_agent_action(
            self.name,
            "resolve_all_clashes",
            (
                f"Resolved {len(resolved)} clashes — "
                f"Total cost impact: Rs.{total_cost:,} | "
                f"Schedule impact: {total_days} days"
            ),
            "success"
        )

        logger.info(f"[{self.name}] Complete — {len(resolved)} resolutions generated")

        return {
            "success": True,
            "total_resolved": len(resolved),
            "total_failed": len(failed),
            "total_cost_impact_inr": total_cost,
            "total_schedule_impact_days": total_days,
            "resolutions": resolved
        }