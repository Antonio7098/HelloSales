from __future__ import annotations

import sys
from pathlib import Path

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
src_str = str(SRC_PATH)
if src_str not in sys.path:
    sys.path.insert(0, src_str)

from hello_sales_backend.cli.verify_db import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
