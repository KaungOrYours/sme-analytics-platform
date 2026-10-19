"""
Puts backend/ on sys.path so evaluation code can import backend/services/*
the same way backend/main.py does (`from services.automl import run_automl`),
without turning backend/ into a package or touching the app's own imports.
Import this before importing anything from `services`.
"""
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
