---
name: feedback_venv
description: Always activate .venv before running pip or python commands in the avtoNet-analysis project
metadata:
  type: feedback
---

Always activate the virtual environment before installing packages or running Python.

**Why:** The project uses a local `.venv` at `/home/miha/Documents/Work/avtoNet-analysis/.venv`. Running pip without activating it installs to the system Python instead.

**How to apply:** Prefix pip and python commands with `source /home/miha/Documents/Work/avtoNet-analysis/.venv/bin/activate &&` or use the venv's python directly: `/home/miha/Documents/Work/avtoNet-analysis/.venv/bin/python3`.
