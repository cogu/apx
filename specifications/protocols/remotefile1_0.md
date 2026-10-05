# RemoteFile v1.0

RemoteFile is a binary, message-based protocol used to synchronize virtual memory regions across a point-to-point communication link (such as a TCP socket, UNIX domain socket, or shared memory). It acts as the application transport layer of an active APX session.

```{note}
For an architectural overview, memory model rationale, and high-level diagrams, see [The RemoteFile Protocol in Internal Design](../../design/remotefile.md).
```

## Memory Model & Addressing

RemoteFile models communication as bidirectional memory synchronization. Each peer maintains two 1GB ($2^{30}$ bytes) virtual memory spaces:

| Memory Map | Address Range | Description |
|:---|:---|:---|
| **Local Map** | `0x00000000` – `0x3FFFFBFF` | Mapped files owned and published by the local endpoint (1,073,740,800 bytes). |
| **Remote Map** | `0x00000000` – `0x3FFFFFFF` | Mirrored files published by the remote peer, including the control area (1,073,741,824 bytes). |

The last 1KB (1024 bytes) of the remote address space (`0x3FFFFC00` – `0x3FFFFFFF`) is reserved for the **Control Area**, which is used to exchange commands such as file announcements and open/close requests.

### Normative Addressing Rules

**Rule 1 (Data Area Writes):**
> A memory write targeting an address below `0x3FFFFC00` is illegal unless:
> 1. A file exists at that address range.
> 2. The file mapped at that address range has been previously opened by the remote peer.
>
> Any write targeting an unopened file or exceeding file bounds must be ignored or treated as a protocol error.

**Rule 2 (Control Area Writes):**
> A memory write targeting the Control Area (`0x3FFFFC00` – `0x3FFFFFFF`) is valid if and only if:
> 1. The start address of the write is **exactly** `0x3FFFFC00`.
> 2. The total length of the write does not exceed 1024 bytes.

**Rule 3 (Data Synchronization):**
> As long as an opened file remains active, any local modification to that file's memory buffer must be immediately transmitted to the remote peer as a binary write command covering the modified byte range.

---

## Wire Framing & Transport

RemoteFile is transport-agnostic and relies on point-to-point streaming connections. On stream-oriented transports (such as TCP or UNIX domain sockets), message framing must be provided by [NumHeader](numheader.md).

For TCP connections, **NumHeader32** is the recommended framing protocol.

Each transmitted message consists of:
1. **Message Header**: Length prefix encoded using NumHeader (1, 2, or 4 bytes).
2. **Message Payload**: The message body (greeting text or binary write payload).

---

## Greeting Handshake

Upon establishing a physical connection, the client must send a **Greeting Header** as the very first message. The greeting is a multi-line text string (the only text-based message in the protocol) formatted similarly to an HTTP/MIME header.

### Greeting Format

- The first line must be the protocol identifier: `RMFP/1.0\n`
- Subsequent lines contain optional key-value attributes formatted as `Key: Value\n`
- The greeting message must terminate with an additional newline (`\n`).

**Example Greeting:**
```text
RMFP/1.0\nNumHeader: 32\n\n
```

### Greeting Constraints

- **Maximum Length**: The total length of the greeting message must not exceed 127 bytes. This ensures that the message length fits within the 1-byte short form of both NumHeader16 and NumHeader32.
- **Line Endings**: Every line must end with a single UNIX newline (`\n`, `0x0A`).

### Greeting Attributes

| Attribute | Format | Description |
|:---|:---|:---|
| `NumHeader` | `16` or `32` | Declares the NumHeader framing variant used for all subsequent messages from the client. |

---

## Binary Data Messages

After the greeting handshake completes, all communication consists exclusively of binary write messages.

Each write message payload contains:
1. **Address Header**: Encodes the target start address and fragmentation flags (2 or 4 bytes).
2. **Data Buffer**: The raw payload bytes to write into remote memory.

$$\text{Data Buffer Length} = \text{Total Message Payload Length} - \text{Address Header Length}$$

### AddressHeader Formats

The AddressHeader comes in two forms depending on the target memory address:

**Low Address Form (0 – 16,383):**
Occupies 2 bytes. Used for fast, compact updates to frequently changing data buffers.

```text
+-------------------------------+-----------------------+
|             Byte 0            |         Byte 1        |
+-------+-------+---------------+-----------------------+
| Bit 7 | Bit 6 |    Bits 5-0   |        Bits 7-0       |
+-------+-------+---------------+-----------------------+
|   0   |   M   |  Address MSB  |      Address LSB      |
+-------+-------+---------------+-----------------------+
    ^       ^   \_______________________________________/
    |       |                       |
HIGH_BIT=0  |           14-bit Address (0 - 16,383)
            |
        MORE_BIT (0 = final packet, 1 = more packets follow)
```

| Field | Bits | Value Range | Description |
|:---|:---|:---|:---|
| **HIGH_BIT** | Byte 0, Bit 7 | `0` | Specifies 2-byte Low Address form |
| **MORE_BIT** | Byte 0, Bit 6 | `0` or `1` | Fragmentation flag (`1` = more packets follow) |
| **Address** | Byte 0 (Bits 5–0) + Byte 1 (Bits 7–0) | `0`–`16,383` | 14-bit big-endian start address |

**High Address Form (16,384 – 1,073,741,823):**
Occupies 4 bytes. Used for larger address ranges and the Control Area.

```text
+-------------------------------+-----------+-----------+-----------+
|             Byte 0            |   Byte 1  |   Byte 2  |   Byte 3  |
+-------+-------+---------------+-----------+-----------+-----------+
| Bit 7 | Bit 6 |    Bits 5-0   |  Bits 7-0 |  Bits 7-0 |  Bits 7-0 |
+-------+-------+---------------+-----------+-----------+-----------+
|   1   |   M   |                      Address (30-bit)             |
+-------+-------+---------------------------------------------------+
    ^       ^   \___________________________________________________/
    |       |                             |
HIGH_BIT=1  |             30-bit Address (0 - 1,073,741,823)
            |
        MORE_BIT (0 = final packet, 1 = more packets follow)
```

| Field | Bits | Value Range | Description |
|:---|:---|:---|:---|
| **HIGH_BIT** | Byte 0, Bit 7 | `1` | Specifies 4-byte High Address form |
| **MORE_BIT** | Byte 0, Bit 6 | `0` or `1` | Fragmentation flag (`1` = more packets follow) |
| **Address** | Bytes 0–3 (Bits 29–0) | `16,384`–`1,073,741,823` | 30-bit big-endian start address |

### AddressHeader Flags

- **`HIGH_BIT` (Bit 7 of Byte 0)**:
  - `0`: Low address form (2-byte header, 14-bit address range `0`–`16,383`).
  - `1`: High address form (4-byte header, 30-bit address range `16,384`–`1,073,741,823`).
- **`MORE_BIT` (Bit 6 of Byte 0)**:
  - Used for message fragmentation. Set to `1` if additional data packets follow for the same logical write operation.
  - Set to `0` on the final packet to signal the end of the write operation.
  - Upper application layers must not be notified until the complete write operation has been received (`MORE_BIT = 0`).

### Framing Scenarios

| Scenario | NumHeader Format | Address Format | Use Case |
|:---|:---|:---|:---|
| **Short & Low** | Short (1 byte) | Low (2 bytes) | Writing 0–127 bytes to address 0–16,383 |
| **Long & Low** | Long (2 or 4 bytes) | Low (2 bytes) | Writing $\ge 128$ bytes to address 0–16,383 |
| **Short & High** | Short (1 byte) | High (4 bytes) | Writing 0–127 bytes to address $\ge 16,384$ |
| **Long & High** | Long (2 or 4 bytes) | High (4 bytes) | Writing $\ge 128$ bytes to address $\ge 16,384$ |

### Byte Layout Examples

**Short Length & Low Address (1-byte NumHeader + 2-byte AddressHeader):**

| Byte | Protocol | Meaning |
|:---:|:---|:---|
| 0 | NumHeader16/32 | Message Header (Length) |
| 1 | RemoteFile | Address Header (MSB) |
| 2 | RemoteFile | Address Header (LSB) |
| 3..N | Payload | Data Buffer |

**Long Length & Low Address (4-byte NumHeader32 + 2-byte AddressHeader):**

| Byte | Protocol | Meaning |
|:---:|:---|:---|
| 0–3 | NumHeader32 | Message Header (31-bit Big-Endian length) |
| 4 | RemoteFile | Address Header (MSB) |
| 5 | RemoteFile | Address Header (LSB) |
| 6..N | Payload | Data Buffer |

**Short Length & High Address (1-byte NumHeader + 4-byte AddressHeader):**

| Byte | Protocol | Meaning |
|:---:|:---|:---|
| 0 | NumHeader16/32 | Message Header (Length) |
| 1–4 | RemoteFile | Address Header (30-bit Big-Endian address, `HIGH_BIT = 1`) |
| 5..N | Payload | Data Buffer |

**Long Length & High Address (4-byte NumHeader32 + 4-byte AddressHeader):**

| Byte | Protocol | Meaning |
|:---:|:---|:---|
| 0–3 | NumHeader32 | Message Header (31-bit Big-Endian length) |
| 4–7 | RemoteFile | Address Header (30-bit Big-Endian address, `HIGH_BIT = 1`) |
| 8..N | Payload | Data Buffer |

---

## Control Commands

Control commands are issued by writing binary command structures to the Control Area at start address `0x3FFFFC00`.

Command payload fields use **Little-Endian (LE)** byte order for multi-byte integers.

### Command Identifiers (`CmdType`)

The first 4 bytes (`U32LE`) of any control command payload identify the command:

| `CmdType` Constant | Value | Description |
|:---|:---:|:---|
| `RMF_CMD_ACK` | 0 | Command Acknowledged |
| `RMF_CMD_NACK` | 1 | Command Negative Acknowledged |
| *Reserved* | 2 | Reserved |
| `RMF_CMD_FILE_INFO` | 3 | Publish / announce a file |
| `RMF_CMD_REVOKE_FILE` | 4 | Revoke / unmap a published file |
| `RMF_CMD_HEARTBEAT_RQST` | 5 | Heartbeat Request |
| `RMF_CMD_HEARTBEAT_RSP` | 6 | Heartbeat Response |
| `RMF_CMD_PING_RQST` | 7 | Ping Request with timestamp |
| `RMF_CMD_PING_RSP` | 8 | Ping Response with timestamp |
| *Reserved* | 9 | Reserved |
| `RMF_CMD_FILE_OPEN` | 10 | Open a published file |
| `RMF_CMD_FILE_CLOSE` | 11 | Close an opened file |

---

### Acknowledge Commands

**Acknowledge (`RMF_CMD_ACK`):**
Sent as a positive response to a previously received command.

| Offset | Field | Type | Value | Description |
|:---:|:---|:---:|:---|:---|
| 0 | `CmdType` | `U32LE` | `0` (`RMF_CMD_ACK`) | Command Identifier |

**Negative Acknowledge (`RMF_CMD_NACK`):**
Sent as an error response to a previously received command.

| Offset | Field | Type | Value | Description |
|:---:|:---|:---:|:---|:---|
| 0 | `CmdType` | `U32LE` | `1` (`RMF_CMD_NACK`) | Command Identifier |

---

### File Management Commands

**FileInfo Command (`RMF_CMD_FILE_INFO`):**
Announces that a file is available and mapped at a specific start address in the sender's local memory map.

| Offset | Field | Type | Value Range | Description |
|:---:|:---|:---:|:---|:---|
| 0 | `CmdType` | `U32LE` | `3` (`RMF_CMD_FILE_INFO`) | Command Identifier |
| 4 | `StartAddress` | `U32LE` | `0` – `0x3FFFFBFF` | Start address of the file |
| 8 | `FileSize` | `U32LE` | `0` – `0x3FFFFC00` | Maximum size of the file in bytes |
| 12 | `FileType` | `U16LE` | `0` – `2` | File type descriptor (see below) |
| 14 | `DigestType` | `U16LE` | `0` – `2` | Checksum algorithm (see below) |
| 16 | `DigestData` | `UINT8[32]` | Bytes | 32-byte digest payload (zero-padded if unused) |
| 48 | `FileName` | String | ASCII | Null-terminated file name string |

The total size of the `FileInfo` structure is $48 + \text{strlen(FileName)} + 1$ bytes. Because the maximum command length is 1024 bytes, the maximum file name length is **975 bytes** (excluding the null terminator).

**FileType Values:**

| Value | Identifier | Description |
|:---:|:---|:---|
| 0 | `FixedFile` | Fixed-size memory region (default) |
| 1 | `DynamicFile` | Dynamically sized file |
| 2 | `FileStream` | Streaming FIFO data |

**DigestType Values:**

| Value | Identifier | Description |
|:---:|:---|:---|
| 0 | `NoDigest` | No checksum provided |
| 1 | `SHA-1` | 20-byte SHA-1 hash |
| 2 | `SHA-256` | 32-byte SHA-256 hash |

**Multiple FileInfo Packing:**
Multiple `FileInfo` structures may be packed into a single 1024-byte control write. When packing multiple structures:
- Only the **first structure** includes the 4-byte `CmdType` field.
- Subsequent structures begin immediately after the null terminator of the preceding file name (starting directly with `StartAddress`).

**FileRevoke Command (`RMF_CMD_REVOKE_FILE`):**
Unmaps a previously announced file. If the remote peer currently has the file open, it is automatically closed.

| Offset | Field | Type | Value | Description |
|:---:|:---|:---:|:---|:---|
| 0 | `CmdType` | `U32LE` | `4` (`RMF_CMD_REVOKE_FILE`) | Command Identifier |
| 4 | `StartAddress` | `U32LE` | `0` – `0x3FFFFBFF` | Start address of the file to revoke |

---

### Diagnostic Commands

Used to verify transport liveness, measure latency, and test route paths.

**Heartbeat Request (`RMF_CMD_HEARTBEAT_RQST`):**

| Offset | Field | Type | Value | Description |
|:---:|:---|:---:|:---|:---|
| 0 | `CmdType` | `U32LE` | `5` (`RMF_CMD_HEARTBEAT_RQST`) | Command Identifier |

**Heartbeat Response (`RMF_CMD_HEARTBEAT_RSP`):**

| Offset | Field | Type | Value | Description |
|:---:|:---|:---:|:---|:---|
| 0 | `CmdType` | `U32LE` | `6` (`RMF_CMD_HEARTBEAT_RSP`) | Command Identifier |

**Ping Request (`RMF_CMD_PING_RQST`):**

| Offset | Field | Type | Value Range | Description |
|:---:|:---|:---:|:---|:---|
| 0 | `CmdType` | `U32LE` | `7` (`RMF_CMD_PING_RQST`) | Command Identifier |
| 4 | `StartAddress` | `U32LE` | Address or `0xFFFFFFFF` | Target file address (`0xFFFFFFFF` for general peer) |
| 8 | `TimeStampSec` | `U32LE` | `0` – $2^{32}-1$ | Origin timestamp seconds |
| 12 | `TimeStampMilliSec` | `U32LE` | `0` – $2^{32}-1$ | Origin timestamp milliseconds |

**Ping Response (`RMF_CMD_PING_RSP`):**
Echoes back the fields from the corresponding `Ping Request`.

| Offset | Field | Type | Value Range | Description |
|:---:|:---|:---:|:---|:---|
| 0 | `CmdType` | `U32LE` | `8` (`RMF_CMD_PING_RSP`) | Command Identifier |
| 4 | `StartAddress` | `U32LE` | Address | Echoed target file address |
| 8 | `TimeStampSec` | `U32LE` | `0` – $2^{32}-1$ | Echoed timestamp seconds |
| 12 | `TimeStampMilliSec` | `U32LE` | `0` – $2^{32}-1$ | Echoed timestamp milliseconds |

---

### File Open & Close Commands

**FileOpen Command (`RMF_CMD_FILE_OPEN`):**
Requests to open a remote file announced via a preceding `FileInfo` command.

| Offset | Field | Type | Value Range | Description |
|:---:|:---|:---:|:---|:---|
| 0 | `CmdType` | `U32LE` | `10` (`RMF_CMD_FILE_OPEN`) | Command Identifier |
| 4 | `StartAddress` | `U32LE` | `0` – `0x3FFFFBFF` | Start address of the remote file to open |

**FileClose Command (`RMF_CMD_FILE_CLOSE`):**
Closes a previously opened remote file.

| Offset | Field | Type | Value Range | Description |
|:---:|:---|:---:|:---|:---|
| 0 | `CmdType` | `U32LE` | `11` (`RMF_CMD_FILE_CLOSE`) | Command Identifier |
| 4 | `StartAddress` | `U32LE` | `0` – `0x3FFFFBFF` | Start address of the remote file to close |
