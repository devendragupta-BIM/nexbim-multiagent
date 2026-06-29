# NexBIM — Multi-Agent AI System for BIM Coordination

> Production-grade multi-agent AI system that autonomously coordinates BIM projects — detecting clashes, resolving conflicts using LLaMA 3.3 70B, checking compliance against Indian construction standards, validating Level of Development, and generating professional PDF reports.

Built by **Devendra Gupta** — Civil Engineering Student, BIM Automation Intern at BIM Modelling Service India, Gurugram.

---

## What NexBIM Does

Traditional BIM coordination requires teams of engineers spending days manually detecting clashes, checking compliance, and writing reports. NexBIM automates this entire workflow in under 60 seconds using a pipeline of 6 specialized AI agents.

**Input:** An IFC or BIM model file  
**Output:** A complete professional coordination report with AI-generated resolutions

---

## Pipeline — 6 Agents Working Together
Model File

│

▼

[Agent 1] Intake Agent

Parse IFC/BIM model, extract all elements and disciplines

│

▼

[Agent 2] Classifier Agent

Detect geometric and clearance clashes across disciplines

│

▼

[Agent 3] Resolver Agent  ←  Groq LLaMA 3.3 70B

AI reasons about each clash and generates specific resolutions

with Indian construction standards (IS codes + ISO 19650)

│

▼

[Agent 4] Compliance Agent  ←  Groq LLaMA 3.3 70B

Check model against IS 456, IS 800, IS 1893, IS 2052,

IS 10401, NBC 2016, ISO 19650 standards

│

▼

[Agent 5] LOD Agent

Validate every element against Level of Development requirements

Flag missing attributes and completeness percentage

│

▼

[Agent 6] Reporter Agent

Generate professional PDF coordination report

│

▼

PDF Report + JSON State Export + Session Memory

---

## Sample Output

From a single run on a building model with 8 elements:

| Metric | Result |
|--------|--------|
| Elements Parsed | 8 |
| Disciplines Detected | MEP, Structural, Architectural |
| Clashes Found | 2 (1 Critical, 1 Major) |
| Clashes Resolved | 2 |
| Compliance Issues | 11 |
| LOD Violations | 8 |
| Health Score | 80.25 / 100 |
| Cost Impact | Rs. 60,000 |
| Schedule Impact | 2 days |
| Time to Complete | ~30 seconds |

---

## AI Clash Resolution Example

**Clash:** HVAC-DUCT-001 vs BM-001 — CRITICAL  
**AI Resolution:** Reroute HVAC-DUCT-001 to avoid penetration with BM-001 by 300mm. Modify duct segment to follow available structural voids and maintain minimum 50mm clearance from structural elements as per IS 10401.  
**Standard:** IS 10401:2018 and ISO 19650-2:2018  
**Cost Impact:** Rs. 30,000  
**Schedule Impact:** 1 working day  

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| AI Reasoning | Groq LLaMA 3.3 70B |
| Agent Framework | Custom Python (zero framework dependency) |
| BIM Parsing | ifcopenshell + custom IFC parser |
| Vector Memory | ChromaDB |
| PDF Generation | ReportLab |
| Automation | n8n compatible |
| Language | Python 3.11 |

---

## Project Structure
nexbim-multiagent/

├── agents/

│   ├── intake_agent.py        # Parses BIM models

│   ├── classifier_agent.py    # Detects clashes

│   ├── resolver_agent.py      # AI clash resolution

│   ├── compliance_agent.py    # IS + ISO standards check

│   ├── lod_agent.py           # LOD validation

│   └── reporter_agent.py      # PDF report generation

├── core/

│   ├── state_manager.py       # Shared project state

│   ├── memory.py              # Cross-session memory

│   └── config.py              # Configuration

├── tools/

│   ├── ifc_parser.py          # IFC file parser

│   ├── clash_detector.py      # Geometric clash detection

│   ├── report_generator.py    # PDF engine

│   └── bcf_writer.py          # BCF format output

├── knowledge_base/            # ChromaDB vector store

├── sample_data/               # Sample BIM files

├── main.py                    # Pipeline entry point

└── requirements.txt

---

## Installation

```bash
# Clone the repository
git clone https://github.com/devendragupta-BIM/nexbim-multiagent.git
cd nexbim-multiagent

# Install dependencies
pip install langchain langchain-groq langchain-community
pip install chromadb streamlit python-dotenv
pip install groq reportlab pandas lxml

# Set up environment
cp .env.example .env
# Edit .env and add your Groq API key
# Get free key at https://console.groq.com
```

---

## Usage

**Run on sample data:**
```bash
python main.py
```

**Run on your own IFC file:**

Edit the last section of `main.py`:
```python
result = run_pipeline(
    model_path="path/to/your/model.ifc",
    project_name="Your Project Name"
)
```

Then run:
```bash
python main.py
```

The system will produce:
- A PDF coordination report in the project folder
- A JSON state export with complete data
- A log file with full agent execution trace

---

## Standards Covered

| Standard | Area |
|----------|------|
| IS 456:2000 | Concrete structures |
| IS 800:2007 | Steel structures |
| IS 1893:2016 | Seismic design |
| IS 2052:1983 | Pipe specifications |
| IS 10401:2018 | Ductwork clearances |
| NBC 2016 | National Building Code |
| ISO 19650-1 | BIM information management |
| ISO 19650-2 | Asset delivery |

---

## Roadmap

- [x] IFC model parsing
- [x] Multi-discipline clash detection
- [x] AI clash resolution with IS/ISO standards
- [x] Compliance checking
- [x] LOD validation
- [x] Professional PDF report generation
- [x] Session memory and state export
- [ ] Streamlit web dashboard
- [ ] Navisworks API integration
- [ ] Revit API integration
- [ ] BCF file export
- [ ] Real-time 4D schedule agent
- [ ] Digital twin integration

---

## About the Builder

**Devendra Gupta**  
Civil Engineering Student — Jharkhand University of Technology (2025–2029)  
BIM Automation Intern — BIM Modelling Service India, Gurugram  

Also built:
- NexBIM v17.0 — AI Copilot embedded inside Autodesk Revit
- NexBIM AI Platform — RAG-based BIM intelligence with 14 tools
- Suraksh — Pre-earthquake safety intelligence startup

Connect on LinkedIn: [linkedin.com/in/devendra-gupta-b943b4377](https://linkedin.com/in/devendra-gupta-b943b4377)

---

## License

MIT License — Free to use, modify, and distribute with attribution.

---

*NexBIM is an independent research project demonstrating the application of multi-agent AI systems to real-world BIM coordination workflows.*