"""Bluetooth Classic SPP protocol of the Bosch GLM 50 C (0601072C00).

Reverse engineered; see PROTOCOL.md in the repository for the full frame
reference. Summary:

  TX  c0 55 02 01 00 1a           enable auto-sync -> device pushes a frame
                                  on every press of the measure button.
  RX  c0 55 10 <16 B payload> <CRC>   20-byte push frame; frame type in
                                  byte 3, payload floats (LE) from byte 7.

The CRC does not follow any simple CRC-8 scheme (brute force over
poly/init/xorout failed); frames are validated via header + length instead.

The connection is a plain RFCOMM socket (AF_BLUETOOTH from the stdlib) —
no rfcomm bind, no root, no pybluez. The device must be in Bluetooth mode
and must not be connected to the phone app (MeasureOn) at the same time.
"""

import socket
import struct

DEFAULT_CHANNEL = 5
FRAME_HEADER = b"\xc0\x55\x10"
FRAME_LEN = 20
CMD_AUTOSYNC_ON = bytes.fromhex("c0550201001a")

# Mode IDs as reported by mode-change frames (0xF2); for measurement frames
# the relation is mode_id = (frame_type - 2) / 4.
MODE_LENGTH = 1.0
MODE_CONTINUOUS = 2.0
MODE_AREA = 4.0
MODE_VOLUME = 7.0


def connect(mac: str, channel: int) -> socket.socket:
    s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    s.settimeout(10)
    s.connect((mac, channel))
    s.send(CMD_AUTOSYNC_ON)
    s.settimeout(1)
    return s


def parse_frames(buffer: bytearray):
    """Cut complete push frames out of the buffer, yield (kind, value) events."""
    while True:
        idx = buffer.find(FRAME_HEADER)
        if idx < 0:
            # Eventually drop residue (e.g. the auto-sync ack without c0 prefix)
            if len(buffer) > 4 * FRAME_LEN:
                del buffer[: -len(FRAME_HEADER)]
            return
        if idx:
            del buffer[:idx]
        if len(buffer) < FRAME_LEN:
            return
        frame = bytes(buffer[:FRAME_LEN])
        del buffer[:FRAME_LEN]
        if frame[3] == 0x06:  # single measurement (0x02 = laser event, ignored)
            (meters,) = struct.unpack_from("<f", frame, 7)
            if 0.0 < meters < 100.0:
                yield ("measurement", meters)
        elif frame[3] == 0xF2:  # mode change, float = mode ID
            (code,) = struct.unpack_from("<f", frame, 7)
            yield ("mode", code)
        elif frame[3] == 0xFE:  # failed measurement; float = active mode, NOT
            (code,) = struct.unpack_from("<f", frame, 7)  # the failure cause
            yield ("error", code)
        elif frame[3] == 0x12:  # area result: [area m², length, width]
            yield ("area", struct.unpack_from("<fff", frame, 7))
        elif frame[3] in (0x0E, 0x16):  # 1st partial measurement (area / volume)
            yield ("partial", (1, struct.unpack_from("<f", frame, 11)[0]))
        elif frame[3] == 0x1A:  # volume, 2nd partial measurement: [0, length, 0]
            yield ("partial", (2, struct.unpack_from("<f", frame, 11)[0]))
        elif frame[3] == 0x1E:  # volume result: [volume m³, 3rd length, 0]
            yield ("volume", struct.unpack_from("<ff", frame, 7))
        elif frame[3] == 0x0A:  # continuous measurement: [current, min, max]
            yield ("continuous", struct.unpack_from("<fff", frame, 7))
        elif frame[3] == 0x42:  # addition: [sum, a, b]
            yield ("add", struct.unpack_from("<fff", frame, 7))
        elif frame[3] == 0x46:  # subtraction: [result, a, b]
            yield ("subtract", struct.unpack_from("<fff", frame, 7))
        elif frame[3] == 0x4A:  # area addition: [sum, a, b] in m²
            yield ("area_add", struct.unpack_from("<fff", frame, 7))
        elif frame[3] == 0x4E:  # area subtraction (by type pattern, unverified)
            yield ("area_subtract", struct.unpack_from("<fff", frame, 7))
        elif frame[3] != 0x02:  # ignore laser events, surface anything unknown
            yield ("unknown", (frame[3], struct.unpack_from("<fff", frame, 7)))
