---
layout: default
title: Serialization Rules
permalink: /specification/vm/serialization_rules
parent: APX VM
grand_parent: Specifications
has_toc: true
nav_order: 3
---

# APX Data Serialization Rules
{: .no_toc }

This document defines the binary serialization and deserialization rules for the APX (AUTOSAR Port eXchange) Virtual Machine, detailing how each data type (TypeCode) is encoded into a byte buffer. It also specifies the architectural mechanism for handling dynamic data structures in memory-mapped environments via deterministic slot padding (`padded_next`).

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## 1. Overview and Core Principles

APX is designed for high-performance inter-process, inter-core, and networked communication in embedded and distributed automotive software systems.

### 1.1 Packed Binary Serialization
In almost all scenarios, APX serializes data **densely packed without inter-field padding or structural alignment**. Data fields are placed consecutively into the binary stream byte-for-byte, matching the semantics of packed structures (e.g. `#pragma pack(push, 1)` in C/C++).

- No compiler-induced alignment bytes (e.g. aligning 16-bit or 32-bit values to even or 4-byte boundaries).
- Consecutive fields in records/structs are placed immediately adjacent to one another.

### 1.2 Endianness
All multi-byte numeric primitives (`UINT16`, `UINT32`, `UINT64`, `INT16`, `INT32`, `INT64`) and multi-byte character code units (`CHAR16`, `CHAR32`) are serialized in **Standard Little-Endian (LE)** byte order, regardless of the host machine's native CPU architecture.

### 1.3 Memory-Mapped Determinism
At lower layers of the APX communication pipeline (such as shared memory files, byte port maps, and virtual bus adapters), buffers are memory-mapped. This requires that the **maximum memory footprint and offsets of all data structures and fields are statically predictable**.

To support variable-length data (such as dynamic arrays and dynamic strings) without causing subsequent data elements to shift in memory offset, APX implements a specialized **slot padding mechanism** (see [Section 3](#3-the-padding-mechanism-for-memory-mapped-predictability)).

---

## 2. Serialization Rules by Data Type (TypeCode)

This section specifies how individual data types are serialized and deserialized by the APX Virtual Machine.

### 2.1 Summary of TypeCodes

| TypeCode | ID | Byte Size | Native / Scripting Equivalent | Description |
|:---|:---:|:---:|:---|:---|
| `UINT8` | 0 | 1 | `uint8_t` / `int` | 8-bit unsigned integer |
| `UINT16` | 1 | 2 | `uint16_t` / `int` | 16-bit unsigned integer (little-endian) |
| `UINT32` | 2 | 4 | `uint32_t` / `int` | 32-bit unsigned integer (little-endian) |
| `UINT64` | 3 | 8 | `uint64_t` / `int` | 64-bit unsigned integer (little-endian) |
| `INT8` | 4 | 1 | `int8_t` / `int` | 8-bit signed two's complement integer |
| `INT16` | 5 | 2 | `int16_t` / `int` | 16-bit signed two's complement integer (little-endian) |
| `INT32` | 6 | 4 | `int32_t` / `int` | 32-bit signed two's complement integer (little-endian) |
| `INT64` | 7 | 8 | `int64_t` / `int` | 64-bit signed two's complement integer (little-endian) |
| `BOOL` | 8 | 1 | `bool` | Boolean value (`0x00` = false, `0x01` = true) |
| `BYTE` | 9 | 1 | `uint8_t` / `bytes` | Raw byte / blob code unit |
| `RECORD` | 10 | Variable | `struct` / `dict` / `hash` | Composite record structure |
| `RESERVED` | 11 | N/A | N/A | Reserved for future use |
| `CHAR` | 12 | 1 | `char` / `str` | ASCII character code unit |
| `CHAR8` | 13 | 1 | `char8_t` / `str` | UTF-8 character code unit |
| `CHAR16` | 14 | 2 | `char16_t` / `str` | UTF-16 character code unit (little-endian) |
| `CHAR32` | 15 | 4 | `char32_t` / `str` | UTF-32 character code unit (little-endian) |

---

### 2.2 Unsigned Integers (`UINT8`, `UINT16`, `UINT32`, `UINT64`)

Unsigned integer types represent non-negative binary integers.

- **`UINT8`** (1 byte): Encoded as a single byte in range `0..255`.
- **`UINT16`** (2 bytes): Encoded as 2 bytes in little-endian format (least significant byte first), range `0..65,535`.
- **`UINT32`** (4 bytes): Encoded as 4 bytes in little-endian format, range `0..4,294,967,295`.
- **`UINT64`** (8 bytes): Encoded as 8 bytes in little-endian format, range `0..18,446,744,073,709,551,615`.

#### Byte Layout Example (`UINT16` = `0x1234`):
```
Offset 0: 0x34 (LSB)
Offset 1: 0x12 (MSB)
```

#### Byte Layout Example (`UINT32` = `0x01020304`):
```
Offset 0: 0x04 (LSB)
Offset 1: 0x03
Offset 2: 0x02
Offset 3: 0x01 (MSB)
```

---

### 2.3 Signed Integers (`INT8`, `INT16`, `INT32`, `INT64`)

Signed integer types represent two's complement binary integers.

- **`INT8`** (1 byte): Encoded as a single signed byte, range `-128..127`.
- **`INT16`** (2 bytes): Encoded as 2 bytes two's complement in little-endian format, range `-32,768..32,767`.
- **`INT32`** (4 bytes): Encoded as 4 bytes two's complement in little-endian format, range `-2,147,483,648..2,147,483,647`.
- **`INT64`** (8 bytes): Encoded as 8 bytes two's complement in little-endian format, range `-9,223,372,036,854,775,808..9,223,372,036,854,775,807`.

#### Byte Layout Example (`INT16` = `-2` / `0xFFFE`):
```
Offset 0: 0xFE
Offset 1: 0xFF
```

---

### 2.4 Boolean (`BOOL`)

- **Size**: 1 byte.
- **Values**:
  - `0x00`: `false`
  - `0x01`: `true`
- **Serialization Behavior**: Any non-zero truthy input in the high-level variant (e.g. `true`, `1`) is normalized and written as `0x01`.
- **Deserialization Behavior**: `0x00` deserializes to `false`; any non-zero value (`!= 0`) deserializes to `true`.

---

### 2.5 Raw Bytes / Blob (`BYTE`)

- **Unit Size**: 1 byte per element.
- **Usage**: Used for raw binary blobs, payload buffers, or cryptographic digests.
- **Fixed Byte Array (`BYTE[N]`)**: Exactly `N` bytes are copied directly into the buffer. The in-memory payload length must match `N` exactly.
- **Dynamic Byte Array (`BYTE[<=N]`)**: Prefixed by a dynamic length header (`1`, `2`, or `4` bytes), followed by `K <= N` active bytes. Unused allocated capacity (`N - K`) is handled via slot padding (see [Section 3](#3-the-padding-mechanism-for-memory-mapped-predictability)).

---

### 2.6 Characters and Strings (`CHAR`, `CHAR8`, `CHAR16`, `CHAR32`)

#### 2.6.1 Scalar Characters (Array Length = 0)
When encoded as a scalar character, a single character code unit is packed directly:
- `CHAR` / `CHAR8`: 1 byte (ASCII / UTF-8 code unit).
- `CHAR16`: 2 bytes (UTF-16 code unit, little-endian).
- `CHAR32`: 4 bytes (UTF-32 code unit, little-endian).

#### 2.6.2 Fixed-Length Strings (`CHAR[N]`, `CHAR8[N]`)
Fixed-length strings allocate exactly `N * element_size` bytes in the buffer:
- **No dynamic length prefix** is written.
- If the in-memory string length `L <= N`, the serializer writes the string bytes and **zero-fills (null-pads)** the remaining `N - L` bytes up to the full buffer capacity `N`.
- If `L > N`, a buffer error (`APX_BUFFER_BOUNDARY_ERROR` / `VALUE_LENGTH_ERROR`) is raised.

**Example: Fixed String `CHAR[6]` with value `"Hi"`:**
```
Offset 0: 'H' (0x48)
Offset 1: 'i' (0x69)
Offset 2: 0x00 (null padding)
Offset 3: 0x00 (null padding)
Offset 4: 0x00 (null padding)
Offset 5: 0x00 (null padding)
Total size: 6 bytes
```

#### 2.6.3 Dynamic Strings (`CHAR[<=N]`, `CHAR8[<=N]`)
Dynamic strings are variable-length character sequences with a declared maximum capacity `N`:
- **Length Prefix**: `1`, `2`, or `4` bytes indicating the actual string length `K` (`K <= N`).
- **Payload**: Exactly `K` character bytes (no null-terminator is required in the packed payload).
- **Slot Padding**: The buffer pointer is padded out to `N` when moving to subsequent fields.

---

### 2.7 Records (Structs)

A record is a composite data structure containing an ordered sequence of named fields.

#### 2.7.1 Field Ordering and Packing
- Fields are serialized in the **exact declaration order** defined in the APX IDL specification.
- **No structure alignment or compiler-inserted padding** exists between fields. For example, a `UINT8` followed by a `UINT32` occupies exactly 5 contiguous bytes ($1 + 4$).

#### 2.7.2 Nested Records
- A record field may itself be a child record.
- The child record's fields are serialized inline in sequence.

#### 2.7.3 Arrays of Records (`RECORD[N]` and `RECORD[<=N]`)
- **Fixed Array of Records (`RECORD[N]`)**: All `N` record instances are serialized consecutively. Each record instance occupies its full static maximum record size.
- **Dynamic Array of Records (`RECORD[<=N]`)**: Prefixed by the array length integer ($K \le N$), followed by $K$ serialized record instances.

> **Note**: When each record element contains dynamic fields, each record element is padded to its maximum static record size before the next record element begins (see [Section 3.3](#example-2-array-of-records-containing-a-dynamic-string)).

---

### 2.8 Queued Port Serialization (`QUEUED_DATA`)

For queued provide/require ports, the port buffer stores a queue of elements:
- **Queue Length Prefix**: Encodes the current number of valid elements queued in the buffer ($0 \le K_{\text{queue}} \le N_{\text{queue}}$).
- **Element Storage**: A pre-allocated array of $N_{\text{queue}}$ slots, each of size $\text{ElementSize}$.
- **Queue Header Calculation**:
  $$\text{Total Port Buffer Size} = \text{QueueStorageSize} + (N_{\text{queue}} \times \text{ElementSize})$$
  $$\text{Queue Length} = \frac{\text{MaxDataSize} - \text{QueueStorageSize}}{\text{ElementSize}}$$

---

## 3. The Padding Mechanism for Memory-Mapped Predictability

### 3.1 The Problem: Fluctuation in Memory-Mapped Offsets

In low-level APX implementations, data communication relies on memory-mapped buffers (such as shared memory files or memory regions mapped directly to device drivers):

1. **Deterministic Offsets**: Downstream consumers, receivers, and port decoders rely on fixed byte offsets within the memory map to read individual fields without parsing previous fields.
2. **Dynamic Data Dilemma**: When a dynamic array or dynamic string exists inside a record or before other fields, serializing only the active elements ($K < N_{\text{max}}$) would cause all subsequent fields to slide forward to a lower memory offset.
3. **Array of Records Dilemma**: In an array of records where each record contains a dynamic field, variable record lengths would destroy the uniform stride required to index element $i$ at $\text{base} + i \times \text{record\_size}$.

To solve this, APX introduces **slot padding (`padded_next`)**.

---

### 3.2 The Architectural Solution: Slot Padding (`padded_next`)

Whenever a dynamic array (or dynamic string/record element) is encountered during serialization or deserialization:

1. **Dynamic Length Prefix Determination**: The array is prefixed with an unsigned integer indicating the active element count $K$ ($0 \le K \le N_\text{max}$). The prefix size is determined by the declared maximum capacity $N_\text{max}$:

   | Maximum Array Length ($N_{\text{max}}$) | SizeType Enum | Prefix Encoding | Prefix Size |
   |:---|:---|:---|:---:|
   | $1 \le N_{\text{max}} \le 255$ | `UINT8` (`0`) | `uint8_t` | 1 byte |
   | $256 \le N_{\text{max}} \le 65,535$ | `UINT16` (`1`) | `uint16_t` (little-endian) | 2 bytes |
   | $65,536 \le N_{\text{max}} \le 4,294,967,295$ | `UINT32` (`2`) | `uint32_t` (little-endian) | 4 bytes |

2. **Calculate Maximum Slot Boundary**: The data serialization engine calculates the address or offset where the dynamic array **would end** if it were populated to its maximum capacity $N_{\text{max}}$:
   $$\text{padded\_next} = \text{current\_buffer\_pos} + \text{LengthPrefixSize} + (N_{\text{max}} \times \text{ElementSize})$$

3. **Serialize Active Payload**: The data serialization engine writes/reads the dynamic length prefix $K$ and the $K$ active elements.

4. **Advance Pointer Before Next Item**: Before serializing or deserializing the *next* sibling field or subsequent data element, the data serialization engine invokes `prepare_for_buffer_write()` / `prepare_for_buffer_read()`. If `padded_next` is set, the active buffer pointer (`next`) is advanced directly to `padded_next`, safely skipping all unwritten/padding bytes in the slot and resetting `padded_next` to null.

---

### 3.3 Concrete Byte Layout Examples

#### Example 1: Record with Dynamic String and Sibling Field

**Type Definition:**
```yaml
# Record with a dynamic string (max 8 chars) and a uint32 status code
{"Name"a[<=8]"Status"L}
```

- Max capacity of `"Name"`: 1 byte (length prefix for $N \le 255$) + 8 bytes = 9 bytes.
- Size of `"Status"`: 4 bytes (`UINT32`).
- Total static record size: $9 + 4 = 13$ bytes.

**Scenario A: Full string `"ABCDEFGH"` (8 chars, `Status = 0x12345678`):**
```
Offset  0:     0x08        (Length = 8)
Offset  1..8:  "ABCDEFGH" (8 bytes payload)
Offset  9..12: 0x78, 0x56, 0x34, 0x12 (Status, little-endian)
Total written: 13 bytes
```

**Scenario B: Short string `"Hi"` (2 chars, `Status = 0x12345678`):**
```
Offset  0:     0x02        (Length = 2)
Offset  1..2:  "Hi"      (2 bytes payload)
Offset  3..8:  [PADDING]   (6 unused bytes, skipped by padded_next)
Offset  9..12: 0x78, 0x56, 0x34, 0x12 (Status, written at deterministic offset 9)
Total slot:    13 bytes
```

Because `prepare_for_buffer_write()` jumps from offset 3 to offset 9 before writing `"Status"`, the `"Status"` field **always remains at byte offset 9**, preserving memory-mapped integrity.

---

#### Example 2: Array of Records Containing a Dynamic String

**Type Definition:**
```yaml
# Array of 2 records, each with a dynamic string (max 4 chars) and a uint8 id
{"Label"a[<=4]"Id"C}[2]
```

- Each record maximum size: $(1 \text{ byte len} + 4 \text{ bytes payload}) + 1 \text{ byte Id} = 6 \text{ bytes}$.
- Array total size: $2 \times 6 = 12$ bytes.

**Data to serialize:**
- Element 0: `{"Label": "Cat", "Id": 10}` (Length = 3)
- Element 1: `{"Label": "A",   "Id": 20}` (Length = 1)

**Serialized Byte Stream:**
```
-- Element 0 (Record 0, starts at offset 0) --
Offset  0:     0x03          (Label length = 3)
Offset  1:     'C'
Offset  2:     'a'
Offset  3:     't'
Offset  4:     [PADDING]     (1 byte padding up to max 4 chars)
Offset  5:     0x0A          (Id = 10)

-- Element 1 (Record 1, starts at offset 6) --
Offset  6:     0x01          (Label length = 1)
Offset  7:     'A'
Offset  8..10: [PADDING]     (3 bytes padding up to max 4 chars)
Offset 11:     0x14          (Id = 20)

Total buffer size: 12 bytes
```

Every record instance occupies exactly 6 bytes. `array_next()` advances across predictable 6-byte boundaries.

---

## 4. Implementation References

### 4.1 C Implementation (`c-apx`)

- **Serializer** (`apx/src/serializer.c`):
  - `write_buffer_reset()` initializes `padded_next = NULL`.
  - `serializer_prepare_for_array()` computes:
    ```c
    self->buffer.padded_next = self->buffer.next + length_size + 
        (self->state->max_array_len * self->state->element_size);
    ```
  - `serializer_prepare_for_buffer_write()` is called before every write operation to advance `self->buffer.next` to `self->buffer.padded_next`.
- **Deserializer** (`apx/src/deserializer.c`):
  - `deserializer_prepare_for_array()` sets `padded_next = next + (max_array_len * element_size)`.
  - `deserializer_prepare_for_buffer_read()` jumps `self->buffer.next = self->buffer.padded_next`.

### 4.2 C++ Implementation (`cpp-apx`)

- **Serializer** (`apx/src/serializer.cpp`):
  - `Serializer::prepare_for_array()` sets `m_buffer.padded_next = m_buffer.next + length_size + (m_state->max_array_len * m_state->element_size);`
  - `Serializer::prepare_for_buffer_write()` (line 1485):
    ```cpp
    /*
     * If more data follows after a dynamic array write we must move the write pointer to
     * the first byte after the dynamic array. Otherwise elements after the dynamic array
     * will start move around in the memory map.
     */
    apx::error_t Serializer::prepare_for_buffer_write()
    {
       if (!is_valid_buffer())
       {
          return APX_MISSING_BUFFER_ERROR;
       }
       if (m_buffer.padded_next != nullptr)
       {
          if ((m_buffer.padded_next < m_buffer.begin) || (m_buffer.padded_next > m_buffer.end))
          {
             return APX_BUFFER_BOUNDARY_ERROR;
          }
          m_buffer.next = m_buffer.padded_next;
          m_buffer.padded_next = nullptr;
       }
       return APX_NO_ERROR;
    }
    ```
- **Deserializer** (`apx/src/deserializer.cpp`):
  - `Deserializer::prepare_for_array()` and `Deserializer::prepare_for_buffer_read()` enforce the same symmetric padding logic for reading.

### 4.3 Python Implementation Guidelines (`py-apx`)

- In `py-apx/src/apx/data/serializer.py`:
  - `WriteBuffer` tracks `padded_write_pos`.
  - `prepare_for_buffer_write()` must be called before packing any new value, advancing `write_pos = padded_write_pos` whenever `padded_write_pos is not None`.
- In `py-apx/src/apx/data/deserializer.py`:
  - `ReadBuffer` tracks `padded_read_pos`.
  - `prepare_for_buffer_read()` synchronizes `read_pos = padded_read_pos` before subsequent unpack operations.

---

## 5. Quick Reference Summary Table

| Data Structure | Length Header | Inter-field Alignment | Unused Capacity Handling | Buffer Stride / Predictability |
|:---|:---:|:---:|:---|:---|
| **Scalar Primitives** (`UINT8`..`INT64`, `BOOL`) | None | 0 bytes | N/A | Fixed width (1, 2, 4, 8 bytes) |
| **Fixed Array** (`T[N]`) | None | 0 bytes | N/A | Fixed width ($N \times \text{elem\_size}$) |
| **Fixed String** (`CHAR[N]` / `CHAR8[N]`) | None | 0 bytes | Null-padded (`0x00`) in place | Fixed width ($N$ bytes) |
| **Dynamic Array** (`T[<=N]`) | 1, 2, or 4 bytes | 0 bytes | Slot padding via `padded_next` | Deterministic slot ($\text{header} + N \times \text{elem\_size}$) |
| **Dynamic String** (`CHAR[<=N]`) | 1, 2, or 4 bytes | 0 bytes | Slot padding via `padded_next` | Deterministic slot ($\text{header} + N$ bytes) |
| **Record / Struct** | None | 0 bytes | Embedded dynamic fields padded via `padded_next` | Fixed record size (sum of max field sizes) |
| **Array of Records** (`RECORD[N]`) | None | 0 bytes | Dynamic fields inside records padded | Fixed array size ($N \times \text{MaxRecordSize}$) |
| **Queued Port** | 1, 2, or 4 bytes | 0 bytes | Tail elements unused in queue buffer | Deterministic port size ($\text{header} + N_{\text{queue}} \times \text{elem\_size}$) |
