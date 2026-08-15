import csv
import sys
from datetime import datetime
from pathlib import Path

REQUIRED = {"timestamp", "open", "high", "low", "close"}


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python tools/validate_fcpo_csv.py <file.csv>")
        return 2

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Missing file: {path}")
        return 2

    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        headers = {h.strip().lower() for h in (reader.fieldnames or [])}
        missing = REQUIRED - headers
        if missing:
            print(f"Missing columns: {sorted(missing)}")
            return 1

        rows = []
        bad = 0
        for row in reader:
            try:
                ts = row[next(h for h in row if h.strip().lower() == "timestamp")]
                datetime.fromisoformat(ts.replace("Z", "+00:00"))
                for name in ("open", "high", "low", "close"):
                    value = float(row[next(h for h in row if h.strip().lower() == name)])
                    if value <= 0:
                        raise ValueError(name)
                rows.append(row)
            except Exception:
                bad += 1

    print(f"Rows: {len(rows)}")
    print(f"Invalid rows: {bad}")
    if rows:
        print("First timestamp:", rows[0].get("timestamp"))
        print("Last timestamp:", rows[-1].get("timestamp"))
    print("Result:", "VALID" if rows and not bad else "REVIEW")
    return 0 if rows and not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
