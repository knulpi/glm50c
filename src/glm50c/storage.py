"""CSV logging: append rows, migrate files with an outdated header aside.

The CSV schema is language-invariant (English header and mode values)
regardless of the UI language, so data files stay portable.
"""

import csv
import datetime
from pathlib import Path

CSV_HEADER = ["timestamp", "mode", "distance_mm", "area_m2", "volume_m3",
              "value_a", "value_b"]
# distance_mm = main value (length, current value, sum/result, 3rd volume
# length) or ERROR. value_a/b = extra values, unit depends on mode: mm for
# length modes (continuous min/max, area length/width, volume lengths 1/2,
# addition/subtraction operands), m² for area addition/subtraction.


def format_mm(value: float | None) -> str:
    # Device delivers mm resolution; one decimal covers 0.5 mm values
    return "" if value is None else f"{value * 1000.0:.1f}".rstrip("0").rstrip(".")


def append_row(path: Path, when: datetime.datetime, mode: str,
               distance: str = "", area: str = "", volume: str = "",
               a: str = "", b: str = ""):
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with open(path, "a", newline="") as f:
        w = csv.writer(f, delimiter=";")
        if new:
            w.writerow(CSV_HEADER)
        w.writerow([when.isoformat(timespec="seconds"), mode,
                    distance, area, volume, a, b])


def migrate_old_csv(path: Path) -> Path | None:
    """Move a CSV with a different header aside instead of mixing formats.

    Returns the new location if the file was moved, else None."""
    if not path.exists():
        return None
    with open(path, newline="") as f:
        header = f.readline().strip()
    if header == ";".join(CSV_HEADER):
        return None
    old = path.with_name(f"{path.stem}-old-"
                         f"{datetime.datetime.now():%Y%m%d-%H%M%S}{path.suffix}")
    path.rename(old)
    return old
