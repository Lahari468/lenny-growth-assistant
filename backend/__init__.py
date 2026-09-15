import sys
from pathlib import Path

# Automatically ensure backend and root directories are on sys.path
backend_dir = Path(__file__).resolve().parent
root_dir = backend_dir.parent

for p in (str(backend_dir), str(root_dir)):
    if p not in sys.path:
        sys.path.insert(0, p)
