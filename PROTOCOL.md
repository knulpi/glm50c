# Bosch GLM 50 C — Bluetooth protocol notes

Reverse engineered against a GLM 50 C (model **0601072C00**), verified
empirically on 2026-08-28 with BlueZ 5.85. No affiliation with Bosch; all of
this may differ on other firmware revisions.

## Transport

Bluetooth **Classic** SPP (RFCOMM), channel **5**. A plain stdlib socket is
enough — no root, no `rfcomm bind`, no pybluez:

```python
s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
s.connect((mac, 5))
```

The device must be in Bluetooth mode (Bluetooth button) and must **not** be
connected to the MeasureOn phone app at the same time — it accepts only one
client.

## Enabling push mode

```text
TX  c0 55 02 01 00 1a
```

switches auto-sync on: from then on the device pushes a frame by itself on
every press of the measure button. Without this, the device stays silent.

## Push frames

Every push frame is **20 bytes**:

```text
RX  c0 55 10 <type> <3 bytes> <payload: 3 × float32 LE from byte 7> <CRC>
```

Byte 3 is the frame type; the payload holds up to three little-endian
float32 values starting at byte 7 (all lengths in meters, areas in m²,
volumes in m³).

| Type | Meaning | Payload floats |
|---|---|---|
| `0x02` | laser on/off event | — (ignore) |
| `0x06` | single length measurement | [distance, ?, ?] |
| `0x0A` | continuous measurement (tracking) | [current, min, max] |
| `0x0E` | area: 1st partial measurement | [0, length, 0] |
| `0x12` | area result | [area m², length, width] |
| `0x16` | volume: 1st partial measurement | [0, length, 0] |
| `0x1A` | volume: 2nd partial measurement | [0, length, 0] |
| `0x1E` | volume result | [volume m³, 3rd length, 0] |
| `0x42` | addition result | [sum, a, b] |
| `0x46` | subtraction result | [result, a, b] |
| `0x4A` | area addition | [sum, a, b] in m² |
| `0x4E` | area subtraction (by type pattern, unverified) | [result, a, b] in m² |
| `0xF2` | mode change | [mode ID, 0, 0] |
| `0xFE` | failed measurement | [active mode ID, 0, 0] |

Mode IDs (as float): **1** length, **2** continuous, **4** area,
**7** volume. For measurement frames the relation
`mode_id = (type - 2) / 4` holds.

Notes:

- `0xFE` reports only that a measurement failed and which mode was active —
  the cause (too close / too far) is not distinguishable from the frame.
- The response to the auto-sync command is a short ack without the `c0`
  prefix; a robust parser should resync on the `c0 55 10` header.

## CRC

The final byte is a checksum, but it does **not** follow any simple CRC-8
scheme — brute force over polynomial/init/xor-out combinations found no
match. Practical approach: validate frames via header + fixed length and
ignore the CRC.
