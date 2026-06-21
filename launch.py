import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
cmd = [sys.executable, str(root / "pdf_auto_sender.py")]
cmd.extend(sys.argv[1:])
subprocess.run(cmd, cwd=root, check=False)
