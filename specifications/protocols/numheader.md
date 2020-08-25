---
layout: default
title: NumHeader
permalink: /specification/protocol/numheader
parent: Protocols
grand_parent: Specifications
has_toc: false
nav_order: 1
---

# NumHeader

NumHeader encodes an integer in big endian, or network byte order. This integer is used as the message length (the message header).
The integer is parsed first, which tells you how many bytes the rest of the message is (message length). The message payload directly follows the
message length.

NumHeader comes in two versions: *NumHeader16* and *NumHeader32*. The former uses 1 ot 2 bytes to encode the integer while the latter uses
1 or 4 bytes.

The most significant bit of the first byte is called the LONG_BIT. When the bit is set it uses long form (2 or 4 bytes), when the bit is 0 it uses short form (1 byte).

## NumHeader16

NumHeader16 uses 1 byte in short form and 2 bytes in long form. It can encode integers in the range 0-32895.

**NumHeader16 - short form (0-127)**:

<table>
  <thead>
    <tr>
      <th colspan="2">Byte 0</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>BIT 7</td>
      <td>BITS 6-0</td>
    </tr>
    <tr>
      <td>LONG_BIT</td>
      <td>VALUE</td>
    </tr>
    <tr>
      <td>0</td>
      <td>0-127</td>
    </tr>
  </tbody>
</table>

**NumHeader16 - longform form (128-32895)**:

<table>
  <thead>
    <tr>
      <th colspan="2">Byte 0</th>
      <th colspan="1">Byte 1</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>BIT 7</td>
      <td>BITS 6-0</td>
      <td>BITS 7-0</td>
    </tr>
    <tr>
      <td colspan="1">LONG_BIT</td>
      <td colspan="2">VALUE</td>
    </tr>
    <tr>
      <td colspan="1">1</td>
      <td colspan="2">0-32767</td>
    </tr>
  </tbody>
</table>

---
**NOTE**

When LONG_BIT is 1:
- Value range 128-32767 is treated normally as ```y = x```.
- Value range 0-127 is interpreted as ```y = 32768+x``` where x is the value.
- Value is encoded as big endian.

---

## NumHeader32

NumHeader32 uses 1 byte in short form and 4 bytes in long form. It can encode integers in the range 0-2147483647.
The short form of NumHeader32 is identical to short of NumHeader16.

**NumHeader32 - short form (0-127)**:

<table>
  <thead>
    <tr>
      <th colspan="2">Byte 0</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>BIT 7</td>
      <td>BITS 6-0</td>
    </tr>
    <tr>
      <td>LONG_BIT</td>
      <td>VALUE</td>
    </tr>
    <tr>
      <td>0</td>
      <td>0-127</td>
    </tr>
  </tbody>
</table>

**NumHeader32 - longform form (128-2147483647)**:

<table>
  <thead>
    <tr>
      <th colspan="2">Byte 0</th>
      <th colspan="1">Byte 1</th>
      <th colspan="1">Byte 2</th>
      <th colspan="1">Byte 3</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>BIT 7</td>
      <td>BITS 6-0</td>
      <td>BITS 7-0</td>
      <td>BITS 7-0</td>
      <td>BITS 7-0</td>
    </tr>
    <tr>
      <td colspan="1">LONG_BIT</td>
      <td colspan="4">VALUE</td>
    </tr>
    <tr>
      <td colspan="1">1</td>
      <td colspan="2">128-2147483647</td>
    </tr>
  </tbody>
</table>

## NumHeader Examples

| Value      | NumHeader16  | NumHeader32          |
|:-----------|:-------------|:---------------------|
| 127        | `"\x7F"`     | `"\x7F"`             |
| 128        | `"\x80\x80"` | `"\x80\x00\x00\x80"` |
| 32767      | `"\xFF\xFF"` | `"\x80\x00\x7F\xFF"` |
| 32768      | `"\x80\00"`  | `"\x80\x00\x80\x00"` |
| 32895      | `"\x80\7F"`  | `"\x80\x00\x80\x7F"` |
| 2147483647 | -            | `"\xFF\xFF\xFF\xFF"` |


---
**NOTE**

The table above demonstrates how (integer) values are represented in hexadecimal form using string literals. These literals are valid C99 strings.

In python you will need to prepend each string literal with the character b.

Example: `"\x80\x80" –> b"\x80\x80"`

---