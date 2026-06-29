import logging
import json
from typing import Any, Dict, List
from groq import Groq
from core.config import config
from core.state_manager import StateManager, ComplianceIssue

logger = logging.getLogger(__name__)

COMPLIANCE_RULES = {
    "structural": [
        {
            "standard": "IS 456:2000",
            "clause": "Clause 26.5.1",
            "check": "minimum_cover",
            "description": "Minimum clear cover for reinforcement",
            "required_attribute": "ClearCover",
            "min_value": 40
        },
        {
            "standard": "IS 800:2007",
            "clause": "Clause 8.2",
            "check": "slenderness_ratio",
            "description": "Maximum slenderness ratio for compression members",
            "required_attribute": "SlendernessRatio",
            "max_value": 180
        },
        {
            "standard": "IS 1893:2016",
            "clause": "Clause 7.1",
            "check": "seismic_zone",
            "description": "Seismic zone classification required for structural elements",
            "required_attribute": "SeismicZone",
            "required": True
        }
    ],
    "mep": [
        {
            "standard": "IS 10401:2018",
            "clause": "Clause 5.3",
            "check": "duct_clearance",
            "description": "Minimum clearance between ductwork and structural elements",
            "required_attribute": "Clearance",
            "min_value": 50
        },
        {
            "standard": "NBC 2016",
            "clause": "Part 9, Section 3",
            "check": "pipe_insulation",
            "description": "Pipe insulation specification required for MEP elements",
            "required_attribute": "Insulation",
            "required": True
        },
        {
            "standard": "IS 2052:1983",
            "clause": "Clause 4.1",
            "check": "pipe_material",
            "description": "Pipe material specification must be defined",
            "required_attribute": "Material",
            "required": True
        }
    ],
    "architectural": [
        {
            "standard": "NBC 2016",
            "clause": "Part 3, Clause 4.2",
            "check": "fire_rating",
            "description": "Fire rating must be specified for all walls",
            "required_attribute": "FireRating",
            "required": True
        },
        {
            "standard": "IS 3792:1978",
            "clause": "Clause 3.1",
            "check": "wall_thickness",
            "description": "Minimum wall thickness for load bearing walls",
            "required_attribute": "Width",
            "min_value": 200
        }
    ]
}


class ComplianceAgent:
    def __init__(self, state_manager: StateManager):
        self.name = "ComplianceAgent"
        self.state = state_manager
        self.client = Groq(api_key=config.GROQ_API_KEY)

    def _check_element(self, element: Dict, rules: List[Dict]) -> List[Dict]:
        issues = []
        for rule in rules:
            props = element.get("properties", {})
            check = rule.get("check")
            attr = rule.get("required_attribute")

            if rule.get("required"):
                if attr not in props or not props[attr]:
                    issues.append({
                        "element_id": element["id"],
                        "element_name": element["name"],
                        "element_type": element["type"],
                        "standard": rule["standard"],
                        "clause": rule["clause"],
                        "description": rule["description"],
                        "severity": "major",
                        "issue": f"Missing required attribute: {attr}"
                    })

            if "min_value" in rule and attr in props:
                try:
                    val = float(props[attr])
                    if val < rule["min_value"]:
                        issues.append({
                            "element_id": element["id"],
                            "element_name": element["name"],
                            "element_type": element["type"],
                            "standard": rule["standard"],
                            "clause": rule["clause"],
                            "description": rule["description"],
                            "severity": "critical",
                            "issue": (f"{attr} value {val} is below "
                                      f"minimum {rule['min_value']}")
                        })
                except (ValueError, TypeError):
                    pass

            if "max_value" in rule and attr in props:
                try:
                    val = float(props[attr])
                    if val > rule["max_value"]:
                        issues.append({
                            "element_id": element["id"],
                            "element_name": element["name"],
                            "element_type": element["type"],
                            "standard": rule["standard"],
                            "clause": rule["clause"],
                            "description": rule["description"],
                            "severity": "major",
                            "issue": (f"{attr} value {val} exceeds "
                                      f"maximum {rule['max_value']}")
                        })
                except (ValueError, TypeError):
                    pass

        return issues

    def _get_ai_recommendation(self, issue: Dict) -> str:
        try:
            prompt = f"""You are a BIM compliance expert following Indian construction standards.
Provide a brief, specific recommendation to fix this compliance issue:

Element: {issue['element_name']} ({issue['element_type']})
Standard: {issue['standard']} - {issue['clause']}
Issue: {issue['issue']}
Description: {issue['description']}

Respond in ONE sentence with the specific fix required. No JSON, just plain text."""

            response = self.client.chat.completions.create(
                model=config.GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=150
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"AI recommendation failed: {e}")
            return f"Ensure {issue['element_name']} complies with {issue['standard']} {issue['clause']}"

    def run(self, elements: List[Dict[str, Any]]) -> Dict[str, Any]:
        logger.info(f"[{self.name}] Starting compliance check on {len(elements)} elements")
        self.state.update(pipeline_stage="compliance")

        all_issues = []
        for element in elements:
            discipline = element.get("discipline", "")
            rules = COMPLIANCE_RULES.get(discipline, [])
            if not rules:
                continue
            issues = self._check_element(element, rules)
            all_issues.extend(issues)

        critical = [i for i in all_issues if i["severity"] == "critical"]
        major = [i for i in all_issues if i["severity"] == "major"]

        import uuid
        for issue_data in all_issues:
            recommendation = self._get_ai_recommendation(issue_data)
            compliance_issue = ComplianceIssue(
                issue_id=f"CMP-{str(uuid.uuid4())[:8].upper()}",
                standard=issue_data["standard"],
                clause=issue_data["clause"],
                element_id=issue_data["element_id"],
                description=issue_data["description"],
                severity=issue_data["severity"],
                recommendation=recommendation
            )
            self.state.add_compliance_issue(compliance_issue)

        self.state.log_agent_action(
            self.name,
            "check_compliance",
            (f"Found {len(all_issues)} compliance issues — "
             f"Critical: {len(critical)}, Major: {len(major)}"),
            "success"
        )

        logger.info(f"[{self.name}] Complete — {len(all_issues)} issues found")
        return {
            "success": True,
            "total_issues": len(all_issues),
            "critical": len(critical),
            "major": len(major),
            "issues": all_issues
        }