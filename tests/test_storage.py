import datetime

from glm50c.storage import CSV_HEADER, append_row, format_mm, migrate_old_csv

WHEN = datetime.datetime(2026, 8, 28, 12, 0, 0)


def test_format_mm():
    assert format_mm(None) == ""
    assert format_mm(1.8435) == "1843.5"
    assert format_mm(2.0) == "2000"


def test_append_creates_header_once(tmp_path):
    path = tmp_path / "log.csv"
    append_row(path, WHEN, "length", distance="1843.5")
    append_row(path, WHEN, "area", area="2.1280")
    lines = path.read_text().splitlines()
    assert lines[0] == ";".join(CSV_HEADER)
    assert lines[1] == "2026-08-28T12:00:00;length;1843.5;;;;"
    assert lines[2] == "2026-08-28T12:00:00;area;;2.1280;;;"
    assert len(lines) == 3


def test_append_creates_parent_dirs(tmp_path):
    path = tmp_path / "deep" / "dir" / "log.csv"
    append_row(path, WHEN, "length", distance="1")
    assert path.exists()


def test_migrate_moves_old_format_aside(tmp_path):
    path = tmp_path / "log.csv"
    path.write_text("zeitstempel;modus;distanz_mm\n2026-08-28T10:00:00;laenge;500\n")
    moved = migrate_old_csv(path)
    assert moved is not None
    assert not path.exists()
    assert moved.exists()
    assert moved.name.startswith("log-old-")
    assert "laenge" in moved.read_text()


def test_migrate_keeps_current_format(tmp_path):
    path = tmp_path / "log.csv"
    append_row(path, WHEN, "length", distance="1")
    assert migrate_old_csv(path) is None
    assert path.exists()


def test_migrate_missing_file(tmp_path):
    assert migrate_old_csv(tmp_path / "nope.csv") is None
