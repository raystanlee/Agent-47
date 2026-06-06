# Agent 47 — Project Instructions

## Project identity

Personal AI agent system extending into embodied AI / robotic manipulation. Owner: Ray (raystanlee on GitHub). Goal: competitive advantage as a data scientist at the intersection of agents, perception, and manipulation.

## Repository layout

```
Agent 47/                           # project root
├── (existing Agent 47 stack)
├── AGENTS.md                       # this file
└── robot/                          # robotics work
    ├── CONTEXT.md                  # current state, dataset paths, gotchas
    ├── evaluate.py                 # ACT policy evaluation script
    ├── manipulation_tool.py        # Week 3: MCP tool wrapping ACTPolicy (to be written)
    └── (datasets and checkpoints live in ~/.cache/huggingface/lerobot/, not here)
```

Robotics work lives as a `robot/` subdirectory inside Agent 47 — NOT a separate project. The reason: trained ACT policy will be exposed as an MCP tool (`execute_manipulation`) inside the existing agent, alongside the existing `capture_scene` tool.

## Stack

### Agent 47 core

- NVIDIA Orin Nano (Ubuntu 22.04.5, aarch64) at `192.168.0.133`, user `raymond`
- Intel RealSense D435I on Orin
- FastAPI perception server on port 8000 (systemd service)
- YOLO11n → TensorRT engine (`yolo11n.engine`), ~12ms inference
- Images save to `/Users/ray/AgentWorkspace/last_capture.jpg`
- LLMs: `claude-sonnet-4-6` (main), `claude-haiku-4-5-20251001` (intent routing)
- MCP servers: GitHub (HTTP), Brave (stdio), Gmail (stdio), local (stdio with dynamic tools)
- `capture_scene` MCP tool is the architectural pattern to replicate for `execute_manipulation`

### Robotics environment

- macOS Apple Silicon (M4 Pro, arm64)
- Conda env `lerobot` at `/opt/miniconda3/envs/lerobot/` (Python 3.12)
- LeRobot 0.5.1 via `pip install 'lerobot[feetech]'`
- ffmpeg 8.0.1 (downgrade to 7.1.1 if torchcodec issues arise)

### Session setup (robotics work)

```bash
conda activate lerobot
cd "/Users/ray/Agent 47"
set -a && source .env && set +a
```

## Code style

- Python 3.12, type hints throughout
- OOP for stateful components (manipulation tool, policy wrappers); functions for stateless utilities
- Modular: separate concerns into files, no scripts >300 lines
- Follow existing Agent 47 patterns — `capture_scene` is the MCP tool template
- Docstrings on public methods explaining *why* not *what*
- No premature abstraction — write the concrete thing first, refactor when a second use case appears

## Current state

**Week 2 complete.**
- SO-ARM101 assembled, calibrated, teleoperation at 60 Hz
- 24 clean pick-and-place episodes recorded at `raystanlee/pick_object_drop_blue_bin`
- ACT policy trained on Mac M4 Pro (MPS), final loss 0.045
- Evaluation: **5/5 successful pick-and-place runs** using `robot/evaluate.py`
- Note: policy is sensitive to lighting — match training conditions

See `robot/CONTEXT.md` for full hardware details, dataset paths, and gotchas.

## Conventions

- Don't wrap `lerobot-train` — it's a CLI, not a library function.
- Don't rename or restructure the existing Agent 47 code without an explicit ask.
- Don't modularize dataset recording — it's a one-shot CLI command.
- Don't run `lerobot-record` with `sudo` — creates root-owned files in the HF cache.
- Model checkpoints stay out of git — push to Hugging Face Hub instead.
