from pathlib import Path
from datetime import datetime, timezone
if __name__ == "__main__":
 print(f"Status report: {Path('evaluation/reports/comparison_summary.md')} ({datetime.now(timezone.utc).isoformat()})")
