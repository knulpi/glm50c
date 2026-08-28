import struct

from glm50c.protocol import FRAME_HEADER, FRAME_LEN, parse_frames


def frame(ftype: int, *floats: float) -> bytes:
    """Build a 20-byte push frame: header, type, floats from byte 7, CRC stub."""
    payload = b"\x00" * 3 + b"".join(struct.pack("<f", f) for f in floats)
    payload = payload.ljust(15, b"\x00")
    data = FRAME_HEADER + bytes([ftype]) + payload + b"\x00"
    assert len(data) == FRAME_LEN
    return data


def events(data: bytes) -> list:
    return list(parse_frames(bytearray(data)))


def test_single_measurement():
    (kind, meters), = events(frame(0x06, 1.843))
    assert kind == "measurement"
    assert abs(meters - 1.843) < 1e-6


def test_measurement_out_of_range_dropped():
    assert events(frame(0x06, 0.0)) == []
    assert events(frame(0x06, 150.0)) == []


def test_laser_event_ignored():
    assert events(frame(0x02, 1.0)) == []


def test_mode_change():
    assert events(frame(0xF2, 4.0)) == [("mode", 4.0)]


def test_error():
    assert events(frame(0xFE, 7.0)) == [("error", 7.0)]


def test_area_result():
    (kind, (area, length, width)), = events(frame(0x12, 6.0, 2.0, 3.0))
    assert kind == "area"
    assert (area, length, width) == (6.0, 2.0, 3.0)


def test_partial_measurements():
    assert events(frame(0x0E, 0.0, 1.5, 0.0)) == [("partial", (1, 1.5))]
    assert events(frame(0x16, 0.0, 2.5, 0.0)) == [("partial", (1, 2.5))]
    assert events(frame(0x1A, 0.0, 3.5, 0.0)) == [("partial", (2, 3.5))]


def test_volume_result():
    (kind, (volume, length3)), = events(frame(0x1E, 24.0, 4.0))
    assert kind == "volume"
    assert (volume, length3) == (24.0, 4.0)


def test_continuous():
    assert events(frame(0x0A, 1.0, 0.5, 2.0)) == [("continuous", (1.0, 0.5, 2.0))]


def test_add_subtract():
    assert events(frame(0x42, 3.0, 1.0, 2.0)) == [("add", (3.0, 1.0, 2.0))]
    assert events(frame(0x46, 1.0, 2.0, 1.0)) == [("subtract", (1.0, 2.0, 1.0))]
    assert events(frame(0x4A, 5.0, 2.0, 3.0)) == [("area_add", (5.0, 2.0, 3.0))]
    assert events(frame(0x4E, 1.0, 3.0, 2.0)) == [("area_subtract", (1.0, 3.0, 2.0))]


def test_unknown_type_surfaced():
    (kind, (ftype, floats)), = events(frame(0x99, 1.0, 2.0, 3.0))
    assert kind == "unknown"
    assert ftype == 0x99
    assert floats == (1.0, 2.0, 3.0)


def test_frame_split_across_chunks():
    data = frame(0x06, 2.5)
    buf = bytearray(data[:10])
    assert list(parse_frames(buf)) == []      # incomplete: nothing yet
    buf += data[10:]
    (kind, meters), = parse_frames(buf)
    assert kind == "measurement"
    assert abs(meters - 2.5) < 1e-6
    assert buf == bytearray()


def test_resync_after_garbage_prefix():
    buf = bytearray(b"\x01\x02\x03" + frame(0x06, 1.0))
    (kind, _), = parse_frames(buf)
    assert kind == "measurement"


def test_oversized_junk_is_trimmed():
    buf = bytearray(b"\xff" * (5 * FRAME_LEN))
    assert list(parse_frames(buf)) == []
    assert len(buf) == len(FRAME_HEADER)


def test_two_frames_in_one_chunk():
    buf = bytearray(frame(0xF2, 1.0) + frame(0x06, 3.0))
    kinds = [kind for kind, _ in parse_frames(buf)]
    assert kinds == ["mode", "measurement"]
