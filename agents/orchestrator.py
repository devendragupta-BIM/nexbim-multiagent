import logging
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List
from groq import Groq
from core.config import config
from core.state_manager import StateManager

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    The Orchestrator is the decision-making brain of NexBIM.
    It does not just call agents in sequence — it decides WHICH
    agent runs next based on what previous agents found, routes
    conflicting findings between agents, and keeps a visible
    reasoning trace so the multi-agent reasoning is observable,
    not hidden inside a linear script.
    """

    def __init__(self, state_manager: StateManager):
        self.state = state_manager
        self.client = Groq(api_key=config.GROQ_API_KEY)
        self.reasoning_trace: List[Dict[str, Any]] = []
        self.agent_messages: List[Dict[str, Any]] = []

    def think(self, message: str, agent: str = "Orchestrator"):
        """Records a visible reasoning step — this is what makes
        the system observable instead of a black box."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "agent": agent,
            "thought": message
        }
        self.reasoning_trace.append(entry)
        logger.info(f"[THINKING:{agent}] {message}")

    def agent_speaks(self, from_agent: str, to_agent: str,
                     message: str, data: Dict = None):
        """Records one agent passing information or a finding
        to another agent. This is the agent-to-agent communication
        layer that distinguishes real multi-agent systems from
        sequential function calls."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "from": from_agent,
            "to": to_agent,
            "message": message,
            "data": data or {}
        }
        self.agent_messages.append(entry)
        logger.info(f"[{from_agent} → {to_agent}] {message}")

    def decide_severity_routing(self, clashes: List[Dict]) -> Dict[str, Any]:
        """The orchestrator looks at what the Classifier found and
        DECIDES how to proceed — this is real decision-making, not
        a fixed pipeline. If there are zero critical clashes it can
        decide to skip deep AI resolution and use fast-path logic
        to save time and API cost."""
        critical = [c for c in clashes if c["severity"] == "critical"]
        major = [c for c in clashes if c["severity"] == "major"]

        if len(critical) == 0 and len(major) == 0:
            self.think(
                "No critical or major clashes found. "
                "Routing to fast-path resolution to conserve "
                "AI compute — only minor clashes need lightweight review."
            )
            return {"strategy": "fast_path", "priority_agents": []}

        if len(critical) >= 3:
            self.think(
                f"Found {len(critical)} critical clashes. "
                f"This indicates a serious coordination failure. "
                f"Escalating — Compliance Agent and LOD Agent will "
                f"run BEFORE full resolution to check if this is a "
                f"systemic modeling issue rather than isolated clashes."
            )
            return {
                "strategy": "escalate",
                "priority_agents": ["compliance", "lod"]
            }

        self.think(
            f"Found {len(critical)} critical and {len(major)} major "
            f"clashes. Standard resolution pathway — resolving in "
            f"severity order, structural elements treated as fixed "
            f"reference points, MEP elements as the moving party."
        )
        return {"strategy": "standard", "priority_agents": []}

    def review_resolution_conflict(self, resolution: Dict,
                                   compliance_issues: List[Dict]) -> Dict:
        """This is real agent-to-agent reasoning: the Orchestrator
        checks if the Resolver's fix would CREATE a new compliance
        problem, by cross-referencing with what the Compliance Agent
        already knows. If yes, it asks the AI to resolve the conflict
        between two agents' findings."""
        related_issues = [
            i for i in compliance_issues
            if resolution.get("responsible_discipline", "").lower()
            in i.get("description", "").lower()
        ]

        if not related_issues:
            return {"conflict": False}

        self.agent_speaks(
            "ComplianceAgent", "Orchestrator",
            f"Warning — the discipline responsible for this fix "
            f"({resolution.get('responsible_discipline')}) already "
            f"has {len(related_issues)} open compliance issues. "
            f"This fix may need to account for those.",
            {"related_issues": len(related_issues)}
        )

        self.think(
            "Cross-referencing Resolver's fix against Compliance "
            "Agent's findings — checking the fix doesn't violate "
            "a standard the Compliance Agent already flagged."
        )

        return {
            "conflict": True,
            "related_issues": related_issues,
            "note": "Fix should be reviewed alongside compliance findings"
        }

    def synthesize_final_verdict(self, summary: Dict[str, Any]) -> str:
        """The orchestrator's closing statement — a genuine AI-
        generated executive verdict on the project's coordination
        health, written specifically for a CEO/PM audience."""
        try:
            prompt = f"""You are the lead orchestrator AI of a multi-agent
BIM coordination system. Five specialist agents have just completed
analysis of a building project. Write a 3-sentence executive verdict
for a construction company CEO, in a confident, technical, decisive tone.

DATA:
Total elements: {summary.get('total_elements')}
Clashes found: {summary.get('total_clashes')} (all resolved: {summary.get('resolved_clashes')})
Compliance issues: {summary.get('compliance_issues')}
LOD violations: {summary.get('lod_violations')}
Health score: {summary.get('health_score')}/100
Cost impact: Rs.{summary.get('total_cost_impact', 0):,.0f}
Schedule impact: {summary.get('schedule_impact_days')} days

Write only the verdict, no preamble, no markdown."""

            response = self.client.chat.completions.create(
                model=config.GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=200
            )
            verdict = response.choices[0].message.content.strip()
            self.think(f"Final verdict synthesized: {verdict}",
                      agent="Orchestrator")
            return verdict
        except Exception as e:
            logger.error(f"Verdict synthesis failed: {e}")
            return (
                f"Coordination complete. {summary.get('total_clashes')} "
                f"clashes resolved, health score "
                f"{summary.get('health_score')}/100. "
                f"Review the full report for details."
            )

    def get_full_trace(self) -> Dict[str, Any]:
        return {
            "reasoning_trace": self.reasoning_trace,
            "agent_messages": self.agent_messages,
            "total_thoughts": len(self.reasoning_trace),
            "total_communications": len(self.agent_messages)
        }