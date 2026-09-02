# NumHeader

NumHeader encodes an integer in big-endian (network byte order). This integer is used as the message header to specify the length of the message payload that directly follows it.

NumHeader comes in two variants:
- **NumHeader16**: Uses 1 byte (short form) or 2 bytes (long form). Encodes lengths in the range `0`–`32,895`.
- **NumHeader32**: Uses 1 byte (short form) or 4 bytes (long form). Encodes lengths in the range `0`–`2,147,483,647`.

The most significant bit (bit 7) of the first byte is called the **LONG_BIT**:
- `LONG_BIT = 0`: **Short form** (1-byte header)
- `LONG_BIT = 1`: **Long form** (2- or 4-byte header)

---

## NumHeader16

NumHeader16 uses 1 byte in short form and 2 bytes in long form. It encodes integers in the range `0`–`32,895`.

### Short Form (0 – 127)

```text
+-------+-----------------------+
| Bit 7 |       Bits 6-0        |
+-------+-----------------------+
|   0   |    Length (0 - 127)   |
+-------+-----------------------+
    ^
    +-- LONG_BIT = 0
```

| Field | Bits | Value | Description |
|:---|:---|:---|:---|
| **LONG_BIT** | Byte 0, Bit 7 | `0` | Specifies 1-byte short form |
| **Length** | Byte 0, Bits 6–0 | `0`–`127` | Direct message length in bytes |

### Long Form (128 – 32,895)

```text
+-------------------------------+-------------------------------+
|             Byte 0            |             Byte 1            |
+-------+-----------------------+-------------------------------+
| Bit 7 |       Bits 6-0        |            Bits 7-0           |
+-------+-----------------------+-------------------------------+
|   1   |      Value (MSB)      |          Value (LSB)          |
+-------+-----------------------+-------------------------------+
    ^   \_______________________________________________________/
    |                               |
LONG_BIT = 1               15-bit Value (0 - 32,767)
```

| Field | Bits | Encoded Value | Decoded Length |
|:---|:---|:---|:---|
| **LONG_BIT** | Byte 0, Bit 7 | `1` | Specifies 2-byte long form |
| **Value** | Byte 0 (Bits 6–0) + Byte 1 (Bits 7–0) | `128`–`32,767` | $y = x$ (`128`–`32,767`) |
| **Value** | Byte 0 (Bits 6–0) + Byte 1 (Bits 7–0) | `0`–`127` | $y = 32,768 + x$ (`32,768`–`32,895`) |

```{note}
**NumHeader16 Long Form Range Extension:**
Because values `0`–`127` are already encodable in the 1-byte short form, NumHeader16 repurposes values `0`–`127` in long form to extend the maximum range from `32,767` up to `32,895` ($32,768 + 127$).
```

---

## NumHeader32

NumHeader32 uses 1 byte in short form and 4 bytes in long form. It encodes integers in the range `0`–`2,147,483,647` ($2^{31} - 1$).

### Short Form (0 – 127)

The short form of NumHeader32 is identical to NumHeader16:

```text
+-------+-----------------------+
| Bit 7 |       Bits 6-0        |
+-------+-----------------------+
|   0   |    Length (0 - 127)   |
+-------+-----------------------+
    ^
    +-- LONG_BIT = 0
```

| Field | Bits | Value | Description |
|:---|:---|:---|:---|
| **LONG_BIT** | Byte 0, Bit 7 | `0` | Specifies 1-byte short form |
| **Length** | Byte 0, Bits 6–0 | `0`–`127` | Direct message length in bytes |

### Long Form (128 – 2,147,483,647)

```text
+-------------------------------+---------------+---------------+---------------+
|             Byte 0            |     Byte 1    |     Byte 2    |     Byte 3    |
+-------+-----------------------+---------------+---------------+---------------+
| Bit 7 |       Bits 6-0        |    Bits 7-0   |    Bits 7-0   |    Bits 7-0   |
+-------+-----------------------+---------------+---------------+---------------+
|   1   |                               Value (31-bit)                          |
+-------+-----------------------------------------------------------------------+
    ^
    +-- LONG_BIT = 1
```

| Field | Bits | Value Range | Description |
|:---|:---|:---|:---|
| **LONG_BIT** | Byte 0, Bit 7 | `1` | Specifies 4-byte long form |
| **Length** | Bytes 0–3 (Bits 30–0) | `128`–`2,147,483,647` | 31-bit big-endian message length |

---

## NumHeader Examples

| Value | NumHeader16 | NumHeader32 |
|:---|:---|:---|
| 127 | `"\x7F"` | `"\x7F"` |
| 128 | `"\x80\x80"` | `"\x80\x00\x00\x80"` |
| 32,767 | `"\xFF\xFF"` | `"\x80\x00\x7F\xFF"` |
| 32,768 | `"\x80\x00"` | `"\x80\x00\x80\x00"` |
| 32,895 | `"\x80\x7F"` | `"\x80\x00\x80\x7F"` |
| 2,147,483,647 | *(Out of range)* | `"\xFF\xFF\xFF\xFF"` |

```{note}
The table above demonstrates how values are represented in hexadecimal form using C99 string literals.

In Python, prefix byte literals with `b`:
* Example: `b"\x80\x80"`
```