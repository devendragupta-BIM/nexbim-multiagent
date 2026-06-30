import logging
import json
from typing import Any, Dict, List
from groq import Groq
from core.config import config
from core.state_manager import StateManager, ClashRecord
from tools.navisworks_parser import NavisworksParser

logger = logging.getLogger(__name__)


class NavisworksAgent:
    def __init__(self, state_manager: StateManager):
        self.name = "NavisworksAgent"
        self.state = state_manager
        self.client = Groq(api_key=config.GROQ_API_KEY)

    def _build_resolution_prompt(self, clash: Dict) -> str:
        return f"""You are a senior BIM coordination engineer with 15 years
of experience resolving MEP, structural and architectural clashes.
You follow ISO 19650 standards and Indian construction codes.

This clash was detected in Navisworks. Provide a specific resolution:

CLASH DETAILS:
- Clash ID      : {clash.get('clash_id')}
- Type          : {clash.get('clash_type')}
- Severity      : {clash.get('severity').upper()}
- Test Name     : {clash.get('test_name')}
- Distance      : {abs(clash.get('distance_m', 0))*1000:.0f}mm penetration/gap
- Element 1     : {clash.get('element_1_name')} 
                  ({clash.get('element_1_discipline')})
                  Category: {clash.get('element_1_type')}
                  Level: {clash.get('element_1_level')}
- Element 2     : {clash.get('element_2_name')} 
                  ({clash.get('element_2_discipline')})
                  Category: {clash.get('element_2_type')}
                  Level: {clash.get('element_2_level')}
- Description   : {clash.get('description')}
- Location      : {json.dumps(clash.get('location', {}))}

Respond ONLY in this exact JSON format:
{{
    "resolution_summary": "One clear sentence describing the fix",
    "responsible_discipline": "mep/structural/architectural",
    "action_required": "specific action to take",
    "alternative_solution": "backup solution if primary fails",
    "estimated_cost_impact_inr": 50000,
    "estimated_schedule_impact_days": 2,
    "priority": "immediate/this_week/this_month",
    "reference_standard": "relevant IS or ISO standard",
    "navisworks_action": "what to update in Navisworks after fix",
    "notes": "additional technical notes"
}}"""

    def _call_groq(self, prompt: str) -> Dict[str, Any]:
        try:
            response = self.client.chat.completions.create(
                model=config.GROQ_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert BIM coordination engineer. "
                            "Always respond with valid JSON only. No extra text."
                        )
                    },
                    {"role": "user", "content": prompt}
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
            "action_required": "Review in Navisworks and coordinate with leads",
            "alternative_solution": "Schedule coordination meeting",
            "estimated_cost_impact_inr": 50000,
            "estimated_schedule_impact_days": 2,
            "priority": "this_week",
            "reference_standard": "ISO 19650-2",
            "navisworks_action": "Mark clash as reviewed after resolution",
            "notes": "Manual coordination required"
        }

    def run(self, xml_path: str) -> Dict[str, Any]:
        logger.info(f"[{self.name}] Parsing Navisworks report: {xml_path}")
        self.state.update(pipeline_stage="navisworks_intake")

        parser = NavisworksParser(xml_path)
        clashes = parser.parse()
        nwc_summary = parser.get_summary()

        if not clashes:
            logger.warning(f"[{self.name}] No clashes found in report")
            return {
                "success": True,
                "total_clashes": 0,
                "resolutions": [],
                "summary": nwc_summary
            }

        logger.info(
            f"[{self.name}] Found {len(clashes)} clashes — "
            f"resolving with AI"
        )
        self.state.update(pipeline_stage="navisworks_resolution")

        disciplines = set()
        for clash in clashes:
            disciplines.add(clash["element_1_discipline"])
            disciplines.add(clash["element_2_discipline"])
            clash_record = ClashRecord(
                clash_id=clash["clash_id"],
                element_1_id=clash["element_1_id"],
                element_2_id=clash["element_2_id"],
                element_1_discipline=clash["element_1_discipline"],
                element_2_discipline=clash["element_2_discipline"],
                clash_type=clash["clash_type"],
                severity=clash["severity"],
                location=clash["location"],
                description=clash["description"],
                status="open"
            )
            self.state.add_clash(clash_record)

        self.state.update(
            disciplines_detected=list(disciplines),
            total_elements=len(set(
                [c["element_1_id"] for c in clashes] +
                [c["element_2_id"] for c in clashes]
            ))
        )

        resolutions = []
        total_cost = 0
        total_days = 0

        for clash in clashes:
            logger.info(
                f"[{self.name}] Resolving {clash['clash_id']} "
                f"({clash['severity'].upper()}) — "
                f"{clash['element_1_name']} vs {clash['element_2_name']}"
            )
            prompt = self._build_resolution_prompt(clash)
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

            resolutions.append({
                "clash_id": clash["clash_id"],
                "clash_name": clash["clash_name"],
                "test_name": clash["test_name"],
                "severity": clash["severity"],
                "clash_type": clash["clash_type"],
                "distance_mm": abs(clash["distance_m"]) * 1000,
                "element_1": clash["element_1_name"],
                "element_2": clash["element_2_name"],
                "element_1_discipline": clash["element_1_discipline"],
                "element_2_discipline": clash["element_2_discipline"],
                "level": clash["element_1_level"],
                "location": clash["location"],
                "resolution": resolution
            })

            logger.info(
                f"[{self.name}] Resolved {clash['clash_id']} — "
                f"Cost: Rs.{cost:,} | Days: {days}"
            )

        self.state.log_agent_action(
            self.name,
            "resolve_navisworks_clashes",
            (f"Resolved {len(resolutions)} Navisworks clashes — "
             f"Total cost: Rs.{total_cost:,} | "
             f"Schedule: {total_days} days"),
            "success"
        )

        logger.info(
            f"[{self.name}] Complete — "
            f"{len(resolutions)} resolutions generated"
        )

        return {
            "success": True,
            "total_clashes": len(clashes),
            "critical": nwc_summary["critical"],
            "major": nwc_summary["major"],
            "minor": nwc_summary["minor"],
            "total_cost_impact_inr": total_cost,
            "total_schedule_impact_days": total_days,
            "resolutions": resolutions,
            "summary": nwc_summary
        }