"""
One-click setup + launch script.
Run:  python run.py
"""
import subprocess
import sys
import shutil
from pathlib import Path


def header(msg):
    print(f"\n{'='*60}\n  {msg}\n{'='*60}")


def step(msg):
    print(f"  ▶  {msg}")


def ok(msg):
    print(f"  ✅  {msg}")


def err(msg):
    print(f"  ❌  {msg}")


# ── 1. Check Python version ───────────────────────────────────────
header("AI Knowledge System — Startup")
if sys.version_info < (3, 9):
    err(f"Python 3.9+ required. You have {sys.version}")
    sys.exit(1)
ok(f"Python {sys.version.split()[0]}")


# ── 2. Create .env if missing ─────────────────────────────────────
env_file = Path(".env")
env_example = Path(".env.example")

if not env_file.exists():
    if env_example.exists():
        shutil.copy(env_example, env_file)
        step(".env created from .env.example")
        print("\n" + "!"*60)
        print("  ACTION REQUIRED:")
        print("  Open .env and add your GEMINI_API_KEY")
        print("  Get a free key at: https://aistudio.google.com/")
        print("!"*60)
        sys.exit(0)
else:
    # Check if key is set
    content = env_file.read_text()
    if "your_gemini_api_key_here" in content:
        print("\n" + "!"*60)
        print("  ⚠️  Please set your GEMINI_API_KEY in .env")
        print("  Get a free key at: https://aistudio.google.com/")
        print("!"*60)
        ans = input("\n  Continue anyway? (y/N): ").strip().lower()
        if ans != "y":
            sys.exit(0)


# ── 3. Install dependencies ───────────────────────────────────────
header("Installing dependencies...")
step("Running: pip install -r requirements.txt")
result = subprocess.run(
    [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"],
    capture_output=False,
)
if result.returncode != 0:
    err("Dependency installation failed. Check requirements.txt.")
    sys.exit(1)
ok("All dependencies installed")


# ── 4. Ensure data directories ────────────────────────────────────
for d in ["data/uploads", "data/vectors", "data/logs"]:
    Path(d).mkdir(parents=True, exist_ok=True)
ok("Data directories ready")


# ── 5. Launch FastAPI server ──────────────────────────────────────
header("Starting server at http://localhost:8000")
print("  📖  API Docs : http://localhost:8000/docs")
print("  🌐  Web UI   : open frontend/index.html in your browser")
print("  📊  Metrics  : http://localhost:8000/metrics/")
print("\n  Press Ctrl+C to stop\n")

subprocess.run([
    sys.executable, "-m", "uvicorn",
    "app.main:app",
    "--reload",
    "--host", "0.0.0.0",
    "--port", "8000",
])
