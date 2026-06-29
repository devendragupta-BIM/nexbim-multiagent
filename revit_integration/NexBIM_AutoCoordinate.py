# -*- coding: utf-8 -*-
"""
NexBIM Auto-Coordinate
Runs the full NexBIM multi-agent pipeline directly inside Revit
Place this in your pyRevit scripts folder
"""
import sys
import os
import clr
import json
import tempfile

clr.AddReference("RevitAPI")
clr.AddReference("RevitAPIUI")
clr.AddReference("System.Windows.Forms")

from Autodesk.Revit.DB import (
    FilteredElementCollector,
    IFCExportOptions,
    Transaction
)
from System.Windows.Forms import (
    MessageBox, MessageBoxButtons,
    MessageBoxIcon, DialogResult
)

# Add NexBIM to Python path
NEXBIM_PATH = r"C:\Users\Devendra Kumar Gupta\nexbim-multiagent"
if NEXBIM_PATH not in sys.path:
    sys.path.insert(0, NEXBIM_PATH)

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument


def export_to_ifc(document) -> str:
    tmp_path = tempfile.mktemp(suffix=".ifc")
    options = IFCExportOptions()
    tmp_dir = os.path.dirname(tmp_path)
    tmp_name = os.path.basename(tmp_path)
    with Transaction(document, "NexBIM: Export IFC") as t:
        t.Start()
        document.Export(tmp_dir, tmp_name, options)
        t.Commit()
    return tmp_path


def run_nexbim_pipeline(ifc_path: str, project_name: str) -> dict:
    import uuid
    from core.state_manager import StateManager
    from core.memory import AgentMemory
    from agents.intake_agent import IntakeAgent
    from agents.classifier_agent import ClassifierAgent
    from agents.resolver_agent import ResolverAgent
    from agents.compliance_agent import ComplianceAgent
    from agents.lod_agent import LODAgent
    from agents.reporter_agent import ReporterAgent
    from agents.revit_executor_agent import RevitExecutorAgent
    from tools.revit_connector import RevitConnector

    project_id = f"NEXBIM-{str(uuid.uuid4())[:8].upper()}"
    state = StateManager(project_id=project_id, project_name=project_name)

    connector = RevitConnector(doc=doc, uidoc=uidoc)

    intake = IntakeAgent(state)
    intake_result = intake.run(ifc_path)
    elements = intake_result["elements"]

    classifier = ClassifierAgent(state)
    classification_result = classifier.run(elements)

    resolver = ResolverAgent(state)
    resolution_result = resolver.run(classification_result["clashes"])

    executor = RevitExecutorAgent(state, connector)
    execution_result = executor.run(resolution_result.get("resolutions", []))

    compliance = ComplianceAgent(state)
    compliance.run(elements)

    lod = LODAgent(state)
    lod.run(elements)

    state.calculate_health_score()

    reporter = ReporterAgent(state)
    report_result = reporter.run(resolution_result.get("resolutions", []))

    summary = state.get_summary()

    return {
        "summary": summary,
        "execution": execution_result,
        "report_path": report_result.get("report_path")
    }


def main():
    project_name = doc.Title or "Revit Project"

    confirm = MessageBox.Show(
        f"NexBIM will:\n\n"
        f"1. Export current model to IFC\n"
        f"2. Detect all clashes\n"
        f"3. Resolve clashes using AI\n"
        f"4. Execute fixes in Revit automatically\n"
        f"5. Check IS and ISO compliance\n"
        f"6. Generate PDF coordination report\n\n"
        f"Project: {project_name}\n\n"
        f"Continue?",
        "NexBIM Auto-Coordinate",
        MessageBoxButtons.YesNo,
        MessageBoxIcon.Question
    )

    if confirm != DialogResult.Yes:
        return

    try:
        MessageBox.Show(
            "Exporting model to IFC...\nThis may take a moment.",
            "NexBIM",
            MessageBoxButtons.OK,
            MessageBoxIcon.Information
        )

        ifc_path = export_to_ifc(doc)

        MessageBox.Show(
            "Running NexBIM Multi-Agent Pipeline...\n"
            "AI agents are analyzing your model.",
            "NexBIM",
            MessageBoxButtons.OK,
            MessageBoxIcon.Information
        )

        result = run_nexbim_pipeline(ifc_path, project_name)
        summary = result["summary"]
        execution = result["execution"]

        MessageBox.Show(
            f"NexBIM Auto-Coordinate Complete!\n\n"
            f"Elements Analyzed : {summary['total_elements']}\n"
            f"Clashes Found     : {summary['total_clashes']}\n"
            f"Clashes Resolved  : {summary['resolved_clashes']}\n"
            f"Fixes Executed    : {execution['total_executed']}\n"
            f"Compliance Issues : {summary['compliance_issues']}\n"
            f"LOD Violations    : {summary['lod_violations']}\n"
            f"Health Score      : {summary['health_score']}/100\n\n"
            f"Execution Mode    : {execution['mode'].upper()}\n"
            f"PDF Report        : {result['report_path']}\n\n"
            f"Open the PDF report to see full details.",
            "NexBIM — Pipeline Complete",
            MessageBoxButtons.OK,
            MessageBoxIcon.Information
        )

        if os.path.exists(ifc_path):
            os.remove(ifc_path)

    except Exception as e:
        MessageBox.Show(
            f"NexBIM encountered an error:\n\n{str(e)}\n\n"
            f"Check the logs for details.",
            "NexBIM Error",
            MessageBoxButtons.OK,
            MessageBoxIcon.Error
        )


main()