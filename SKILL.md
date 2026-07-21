---
name: Keti
description: Task-driven agent skill for end-to-end academic research, literature crawling, UML generation (via Archify), hardware/software code execution, experimental verification, report compilation, and presentation deck (PPT) generation.
version: 1.0.0
license: Apache
authors:
  - Academic Agent Community
repository: https://github.com/tt-a1i/academic-research-task-master
tags:
  - academic-research
  - task-driven
  - web-crawler
  - archify-uml
  - experiment-runner
  - pptx-generator
  - skill-autodiscovery
dependencies:
  python: ">=3.10"
  system:
    - git
  pypi:
    - python-pptx>=0.6.21
    - matplotlib>=3.8.0
    - pandas>=2.1.0
    - requests>=2.31.0
    - openpyxl>=3.1.2
    - weasyprint>=60.0
---

# 🎓 Academic Research Task Master (`SKILL.md`)

An enterprise-grade, **Task-Driven Architecture (TDA)** Agent Skill for automating complex scientific research, embedded/real-time system experiments, hardware architecture diagramming, academic report synthesis, and PPT deck generation.

---

## 🌟 Key Features & Design Philosophy

1. **Task-Driven Execution (DAG Pipeline)**: Avoids LLM context drift by breaking complex research workflows into structured, trackable `task.md` sub-files.
2. **Zero-Hallucination Asset Linking**: All generated reports and presentation decks strictly bind to real local asset paths with verified hashes (`manifest.json`).
3. **UML Architecture Integration**: Seamlessly interfaces with **Archify Skill** to compile Diagrams-as-Code into vector SVG/PNG diagrams.
4. **Dynamic Skill Discovery & Auto-Download**: Scans local `./skills/` directories and automatically discovers/clones open-source compatible skills (`SKILL.md` compliant) when capabilities are missing.
5. **Incremental Feedback Engine**: Selectively recompiles affected downstream sub-tasks upon receiving advisor feedback, eliminating redundant re-computation.

---

## 📂 Repository Directory Structure

```directory
academic-research-task-master/
├── SKILL.md                         # This Skill Specification File
├── README.md                        # Quick Start & User Guide
├── LICENSE                          # MIT License
├── requirements.txt                 # Python Dependencies
├── templates/
│   ├── master_task_template.md     # Master task DAG template
│   └── lab_presentation_style.pptx # Default Lab PPTX template
├── scripts/
│   ├── probe_environment.py        # System environment dependency probe
│   ├── verify_deliverables.py      # Task deliverables verification loop
│   └── skill_discovery.py          # Dynamic skill scanner & downloader
└── docs/
    └── ARCHITECTURE.md              # Technical System Architecture
```

---

## 🤖 Agent System Instructions (Core Prompt)

```markdown
# AGENT SYSTEM PROMPT: ACADEMIC_RESEARCH_TASK_MASTER

You are an expert academic research assistant operating under strict Task-Driven Execution rules. Your objective is to manage the end-to-end research lifecycle—from literature retrieval to experimental coding, UML diagramming, report writing, and presentation deck generation.

### 1. EXECUTION RULES & SAFETY GUARDRAILS
1. Task-Driven Architecture:
   - NEVER generate all project artifacts in a single unconstrained output.
   - ALWAYS break the workflow down into modular task files in `./tasks/` (e.g., `01_task_literature.md`, `03_task_implementation.md`).
   - DO NOT unlock downstream tasks until the current task's deliverables pass automated verification.
2. Asset Grounding & Dual-Storage Rule:
   - All images in reports and PPTs MUST exist in local storage (`./assets/crawled_images/` or `./assets/local_exp_images/`).
   - Every asset MUST be indexed in `./assets/manifest.json`. Placeholder images or fake experimental data are strictly prohibited.
3. Feedback & Retry Protocol:
   - When code or tests fail, update the `[Error Logs]` section in the respective `task.md`.
   - Max retry limit = 3 attempts. If failure persists, halt execution and raise a structured issue report to the user.

### 2. DYNAMIC SKILL DISCOVERY & RUNTIME EXPANSION
When encountering unsupported capabilities (e.g., logical circuit waveform plotting, complex LaTeX rendering):
1. Scan Local: Check `./skills/` for compliant `SKILL.md` definitions.
2. Discover Remote: Query open-source repositories/Skill Hubs for MIT/Apache-2.0 licensed Agent Skills.
3. Validate & Auto-Clone: Verify safety (no malicious scripts) and clone into `./skills/external/<skill-name>/`.
4. Dynamic Mount: Register in `./skills/manifest_skills.json` and inject capabilities into active runtime context.

### 3. THIRD-PARTY SKILL INTEGRATION MATRIX
- Archify Skill: Compile UML DSL (`.arch`) into architecture, sequence, and flowchart PNG/SVGs.
- Academic Crawler Skill: Search Google Scholar, IEEE, ArXiv, Wikipedia via API/safety wrappers.
- Code Interpreter Skill: Run software/hardware benchmarks, generate log CSVs and Matplotlib plots.
- PPT Master Skill: Inject real charts, diagrams, and speaker notes into PowerPoint templates.
```

---

## 📋 Task File Specification (`task.md` Template)

Every sub-task file created in `./tasks/` MUST conform to this schema:

```markdown
# 📋 TASK-FILE: 04_task_experiments.md

## 1. Task Metadata
- **Task ID**: 04-EXP
- **Project Title**: [User Research Project Name]
- **Status**: [ ] Pending  [ ] In-Progress  [ ] Completed  [ ] Failed
- **Dependencies**: `03_task_implementation.md`
- **Data Source**: `./src/experiments/logs/raw_data.csv`

## 2. Execution Steps
1. [ ] Execute benchmark script: `python benchmark.py --data ./src/experiments/logs/raw_data.csv`
2. [ ] Call `Archify Skill` to compile system state transition diagram:
       `output_path: ./assets/archify_images/state_machine.png`
3. [ ] Generate performance comparison charts via Matplotlib to `./assets/local_exp_images/fig_latency.png` (>=300 DPI)
4. [ ] Write metrics output to `./experiments/metrics.json`
5. [ ] Update metadata index in `./assets/manifest.json`

## 3. Deliverable Verification Rules
- **Rule 1 (File Existence)**: File `./assets/local_exp_images/fig_latency.png` exists and size > 50KB.
- **Rule 2 (JSON Validation)**: File `./experiments/metrics.json` contains `mean_latency`, `throughput`, `power_mw`.
- **Rule 3 (Exit Code)**: Execution script exits with code 0.

## 4. Error Logs & Retries
- [Attempt 1]: Passed
- [Attempt 2]: N/A
- [Attempt 3]: N/A

## 5. Revision Log
- YYYY-MM-DD: Task initialized.
```

---

## 🗄️ Metadata Schema (`assets/manifest.json`)

```json
{
  "crawled_ref_images": [
    {
      "id": "ref_img_001",
      "filename": "fig1_architecture.png",
      "path": "assets/crawled_images/fig1_architecture.png",
      "source_url": "https://doi.org/10.1145/xxxxxx",
      "citation": "Author et al., 2025, ISCA",
      "caption": "Intermittent computing system checkpointing pipeline"
    }
  ],
  "archify_diagrams": [
    {
      "id": "arch_seq_001",
      "filename": "power_failure_sequence.png",
      "path": "assets/archify_images/power_failure_sequence.png",
      "source_script": "docs/diagrams/power_sequence.arch",
      "diagram_type": "sequence",
      "caption": "Non-volatile power-loss recovery sequence"
    }
  ],
  "local_exp_images": [
    {
      "id": "exp_img_001",
      "filename": "latency_comparison.png",
      "path": "assets/local_exp_images/latency_comparison.png",
      "generated_by": "src/experiments/plot_latency.py",
      "timestamp": "2026-07-21T18:00:00",
      "caption": "Latency comparison under varying power interruption frequencies"
    }
  ]
}
```

---

## 🛠️ Environment Probe Script (`scripts/probe_environment.py`)

```python
import sys
import shutil

def check_environment():
    required_pypi = ["pptx", "matplotlib", "pandas", "requests", "openpyxl", "weasyprint"]
    required_tools = ["git"]
    
    print("🔍 [Probe] Running System Environment & Skill Dependency Probe...")
    
    missing_pypi = []
    for pkg in required_pypi:
        try:
            __import__(pkg)
        except ImportError:
            missing_pypi.append(pkg)
            
    missing_tools = [tool for tool in required_tools if shutil.which(tool) is None]
    
    if missing_pypi or missing_tools:
        print("⚠️ [Warning] Missing Dependencies Detected:")
        if missing_pypi:
            print(f"  - Missing Python Packages: {missing_pypi}")
            print(f"    Fix: pip install {' '.join(missing_pypi)}")
        if missing_tools:
            print(f"  - Missing System Tools: {missing_tools}")
        return False
        
    print("✅ [Success] All environment dependencies and probes passed!")
    return True

if __name__ == "__main__":
    if not check_environment():
        sys.exit(1)
```

---

## 🚀 Quick Start Guide for GitHub Users

1. **Clone the Skill Repository**:
   ```bash
   git clone https://github.com/tt-a1i/academic-research-task-master.git ./skills/academic-research-task-master
   ```
2. **Install Python Dependencies**:
   ```bash
   pip install -r ./skills/academic-research-task-master/requirements.txt
   ```
3. **Mount to Agent Framework**:
   Import `SKILL.md` into your LLM Agent framework (e.g., Cursor, Claude Code, Dify, AutoGen, CrewAI).
4. **Trigger Research Pipeline**:
   Provide project metadata (Title, Direction, Major, Advisor) to start automatic task generation!

---

## 📄 License

Distributed under the **Apache License**. Free for academic, personal, and commercial research automation.
