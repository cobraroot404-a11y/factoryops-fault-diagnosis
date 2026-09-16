import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_PATH = os.path.join(ROOT, "backend")
WORKER_PATH = os.path.join(ROOT, "worker")
for p in (BACKEND_PATH, WORKER_PATH):
    if p not in sys.path:
        sys.path.insert(0, p)
