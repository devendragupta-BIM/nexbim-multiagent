import sys
import os
import uuid
import json
import tempfile
import asyncio
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.state_manager import StateManager
from core.memory import AgentMemory
from agents.intake_agent import IntakeAgent
from agents.classifier_agent import ClassifierAgent
from agents.resolver_agent import ResolverAgent
from agents.compliance_agent import ComplianceAgent
from agents.lod_agent import LODAgent
from agents.reporter_agent import ReporterAgent

app = FastAPI(title="NexBIM API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

app.mount("/static", StaticFiles(directory="dashboard/static"), name="static")

pipeline_status = {}


@app.get("/", response_class=HTMLResponse)
async def root():
    with open("dashboard/static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/run")
async def run_pipeline(
    background_tasks: BackgroundTasks,
    project_name: str = Form(...),
    file: UploadFile = File(None)
):
    job_id = f"NEXBIM-{str(uuid.uuid4())[:8].upper()}"
    pipeline_status[job_id] = {
        "status": "running",
        "stage": "starting",
        "stages_complete": [],
        "result": None,
        "error": None
    }

    if file and file.filename:
        content = await file.read()
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".ifc")
        tmp.write(content)
        tmp.close()
        model_path = tmp.name
    else:
        model_path = "sample_data/sample.ifc"

    background_tasks.add_task(
        execute_pipeline, job_id, model_path, project_name
    )
    return JSONResponse({"job_id": job_id})


async def execute_pipeline(job_id: str, model_path: str, project_name: str):
    def update(stage: str, complete: list):
        pipeline_status[job_id]["stage"] = stage
        pipeline_status[job_id]["stages_complete"] = complete

    try:
        state = StateManager(project_id=job_id, project_name=project_name)
        memory = AgentMemory()
        complete = []

        update("intake", complete)
        intake = IntakeAgent(state)
        intake_result = intake.run(model_path)
        complete.append("intake")
        update("classification", complete)

        elements = intake_result["elements"]
        classifier = ClassifierAgent(state)
        classification_result = classifier.run(elements)
        complete.append("classification")
        update("resolution", complete)

        resolver = ResolverAgent(state)
        resolution_result = resolver.run(classification_result["clashes"])
        complete.append("resolution")
        update("compliance", complete)

        compliance = ComplianceAgent(state)
        compliance.run(elements)
        complete.append("compliance")
        update("lod", complete)

        lod = LODAgent(state)
        lod.run(elements)
        complete.append("lod")
        update("report", complete)

        state.calculate_health_score()
        reporter = ReporterAgent(state)
        report_result = reporter.run(resolution_result.get("resolutions", []))
        complete.append("report")

        export_path = f"nexbim_state_{job_id}.json"
        state.export_state(export_path)
        summary = state.get_summary()
        memory.save(job_id, summary)

        pipeline_status[job_id] = {
            "status": "complete",
            "stage": "done",
            "stages_complete": complete,
            "result": {
                "summary": summary,
                "resolutions": resolution_result.get("resolutions", []),
                "report_path": report_result.get("report_path")
            },
            "error": None
        }

    except Exception as e:
        pipeline_status[job_id] = {
            "status": "error",
            "stage": "error",
            "stages_complete": [],
            "result": None,
            "error": str(e)
        }


@app.get("/status/{job_id}")
async def get_status(job_id: str):
    return JSONResponse(pipeline_status.get(job_id, {"status": "not_found"}))


@app.get("/report/{job_id}")
async def download_report(job_id: str):
    path = f"NexBIM_Report_{job_id}.pdf"
    if os.path.exists(path):
        return FileResponse(
            path,
            media_type="application/pdf",
            filename=f"NexBIM_Report_{job_id}.pdf"
        )
    return JSONResponse({"error": "Report not found"}, status_code=404)