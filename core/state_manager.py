import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ClashRecord:
    def __init__(self, clash_id: str, element_1_id: str, element_2_id: str,
                 element_1_discipline: str, element_2_discipline: str,
                 clash_type: str, severity: str, location: Dict,
                 description: str, status: str = "open"):
        self.clash_id = clash_id
        self.element_1_id = element_1_id
        self.element_2_id = element_2_id
        self.element_1_discipline = element_1_discipline
        self.element_2_discipline = element_2_discipline
        self.clash_type = clash_type
        self.severity = severity
        self.location = location
        self.description = description
        self.status = status
        self.resolution = None
        self.cost_impact = 0.0
        self.schedule_impact_days = 0
        self.resolved_by_agent = None
        self.resolved_at = None

    def to_dict(self) -> Dict:
        return {
            "clash_id": self.clash_id,
            "element_1_id": self.element_1_id,
            "element_2_id": self.element_2_id,
            "element_1_discipline": self.element_1_discipline,
            "element_2_discipline": self.element_2_discipline,
            "clash_type": self.clash_type,
            "severity": self.severity,
            "location": self.location,
            "description": self.description,
            "status": self.status,
            "resolution": self.resolution,
            "cost_impact": self.cost_impact,
            "schedule_impact_days": self.schedule_impact_days,
            "resolved_by_agent": self.resolved_by_agent,
            "resolved_at": self.resolved_at
        }


class ComplianceIssue:
    def __init__(self, issue_id: str, standard: str, clause: str,
                 element_id: str, description: str,
                 severity: str, recommendation: str):
        self.issue_id = issue_id
        self.standard = standard
        self.clause = clause
        self.element_id = element_id
        self.description = description
        self.severity = severity
        self.recommendation = recommendation
        self.status = "open"

    def to_dict(self) -> Dict:
        return {
            "issue_id": self.issue_id,
            "standard": self.standard,
            "clause": self.clause,
            "element_id": self.element_id,
            "description": self.description,
            "severity": self.severity,
            "recommendation": self.recommendation,
            "status": self.status
        }


class LODViolation:
    def __init__(self, element_id: str, element_type: str,
                 required_lod: int, actual_lod: int,
                 missing_attributes: List[str], severity: str,
                 element_name: str = "", discipline: str = "",
                 completeness: float = 0.0):
        self.element_id = element_id
        self.element_name = element_name
        self.element_type = element_type
        self.discipline = discipline
        self.required_lod = required_lod
        self.actual_lod = actual_lod
        self.missing_attributes = missing_attributes
        self.severity = severity
        self.completeness = completeness

    def to_dict(self) -> Dict:
        return {
            "element_id": self.element_id,
            "element_name": self.element_name,
            "element_type": self.element_type,
            "discipline": self.discipline,
            "required_lod": self.required_lod,
            "actual_lod": self.actual_lod,
            "missing_attributes": self.missing_attributes,
            "severity": self.severity,
            "completeness": self.completeness
        }


class ProjectState:
    def __init__(self, project_id: str, project_name: str):
        self.project_id = project_id
        self.project_name = project_name
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self.model_path = None
        self.model_format = None
        self.total_elements = 0
        self.disciplines_detected = []
        self.clashes: List[ClashRecord] = []
        self.resolved_clashes: List[ClashRecord] = []
        self.compliance_issues: List[ComplianceIssue] = []
        self.lod_violations: List[LODViolation] = []
        self.total_cost_impact = 0.0
        self.total_schedule_impact_days = 0
        self.model_health_score = 0.0
        self.agent_logs: List[Dict[str, Any]] = []
        self.final_report_path = None
        self.pipeline_status = "initialized"
        self.pipeline_stage = "ready"
        self.errors: List[str] = []


class StateManager:
    def __init__(self, project_id: str, project_name: str):
        self.state = ProjectState(
            project_id=project_id,
            project_name=project_name
        )
        logger.info(f"StateManager initialized for project: {project_name}")

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)
        self.state.updated_at = datetime.now().isoformat()

    def add_clash(self, clash: ClashRecord):
        self.state.clashes.append(clash)
        self.state.updated_at = datetime.now().isoformat()

    def resolve_clash(self, clash_id: str, resolution: str,
                      agent_name: str, cost_impact: float = 0.0,
                      schedule_impact: int = 0):
        for clash in self.state.clashes:
            if clash.clash_id == clash_id:
                clash.status = "resolved"
                clash.resolution = resolution
                clash.resolved_by_agent = agent_name
                clash.resolved_at = datetime.now().isoformat()
                clash.cost_impact = cost_impact
                clash.schedule_impact_days = schedule_impact
                self.state.resolved_clashes.append(clash)
                self.state.total_cost_impact += cost_impact
                self.state.total_schedule_impact_days += schedule_impact
                break
        self.state.updated_at = datetime.now().isoformat()

    def add_compliance_issue(self, issue: ComplianceIssue):
        self.state.compliance_issues.append(issue)
        self.state.updated_at = datetime.now().isoformat()

    def add_lod_violation(self, violation: LODViolation):
        self.state.lod_violations.append(violation)
        self.state.updated_at = datetime.now().isoformat()

    def log_agent_action(self, agent_name: str, action: str,
                         result: str, status: str = "success"):
        self.state.agent_logs.append({
            "timestamp": datetime.now().isoformat(),
            "agent": agent_name,
            "action": action,
            "result": result,
            "status": status
        })
        self.state.updated_at = datetime.now().isoformat()
        logger.info(f"[{agent_name}] {action} — {status}")

    def calculate_health_score(self) -> float:
        total_elements = max(self.state.total_elements, 1)
        clash_penalty = len(self.state.clashes) * 1.5
        compliance_penalty = len(self.state.compliance_issues) * 0.8
        lod_penalty = len(self.state.lod_violations) * 0.5
        total_penalty = clash_penalty + compliance_penalty + lod_penalty
        penalty_percent = (total_penalty / total_elements) * 10
        score = max(0.0, 100.0 - penalty_percent)
        self.state.model_health_score = round(score, 2)
        return self.state.model_health_score

    def get_summary(self) -> Dict[str, Any]:
        return {
            "project_id": self.state.project_id,
            "project_name": self.state.project_name,
            "total_elements": self.state.total_elements,
            "disciplines": self.state.disciplines_detected,
            "total_clashes": len(self.state.clashes),
            "resolved_clashes": len(self.state.resolved_clashes),
            "open_clashes": len([
                c for c in self.state.clashes if c.status == "open"
            ]),
            "compliance_issues": len(self.state.compliance_issues),
            "lod_violations": len(self.state.lod_violations),
            "total_cost_impact": self.state.total_cost_impact,
            "schedule_impact_days": self.state.total_schedule_impact_days,
            "health_score": self.state.model_health_score,
            "pipeline_status": self.state.pipeline_status,
            "pipeline_stage": self.state.pipeline_stage,
            "updated_at": self.state.updated_at,
            "agent_logs": [
                {
                    "timestamp": log["timestamp"],
                    "agent": log["agent"],
                    "action": log["action"],
                    "result": log["result"],
                    "status": log["status"]
                }
                for log in self.state.agent_logs
            ],
            "compliance_issues_list": [
                {
                    "standard": i.standard,
                    "clause": i.clause,
                    "description": i.description,
                    "severity": i.severity,
                    "element_id": i.element_id,
                    "recommendation": i.recommendation
                }
                for i in self.state.compliance_issues
            ],
            "lod_violations_list": [
                {
                    "element_name": v.element_name,
                    "element_type": v.element_type,
                    "discipline": v.discipline,
                    "required_lod": v.required_lod,
                    "actual_lod": v.actual_lod,
                    "missing_attributes": v.missing_attributes,
                    "severity": v.severity,
                    "completeness": v.completeness
                }
                for v in self.state.lod_violations
            ]
        }

    def export_state(self, path: str):
        state_dict = {
            "project_id": self.state.project_id,
            "project_name": self.state.project_name,
            "created_at": self.state.created_at,
            "updated_at": self.state.updated_at,
            "model_path": self.state.model_path,
            "total_elements": self.state.total_elements,
            "disciplines_detected": self.state.disciplines_detected,
            "clashes": [c.to_dict() for c in self.state.clashes],
            "resolved_clashes": [
                c.to_dict() for c in self.state.resolved_clashes
            ],
            "compliance_issues": [
                i.to_dict() for i in self.state.compliance_issues
            ],
            "lod_violations": [
                v.to_dict() for v in self.state.lod_violations
            ],
            "total_cost_impact": self.state.total_cost_impact,
            "total_schedule_impact_days": self.state.total_schedule_impact_days,
            "model_health_score": self.state.model_health_score,
            "agent_logs": self.state.agent_logs,
            "pipeline_status": self.state.pipeline_status,
            "pipeline_stage": self.state.pipeline_stage,
            "errors": self.state.errors
        }
        with open(path, "w") as f:
            json.dump(state_dict, f, indent=2, default=str)
        logger.info(f"State exported to {path}")

    def get_state(self) -> ProjectState:
        return self.state