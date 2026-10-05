# RemoteFile v1.1

RemoteFile is a binary, message-based protocol used to synchronize virtual memory regions across a point-to-point communication link (such as a TCP socket, UNIX domain socket, or shared memory). It acts as the application transport layer of an active APX session.

```{note}
For an architectural overview, memory model rationale, and high-level diagrams, see [The RemoteFile Protocol in Internal Design](../../design/remotefile.md).
```

## Overview of RemoteFile v1.1

RemoteFile v1.1 extends the baseline RemoteFile v1.0 protocol with enhanced handshake negotiation, explicit error signaling, server runtime monitoring, and cryptographic authentication:

- **Protocol Greeting & Handshake**: Employs protocol identifier `RMFP/1.1\n` with explicit framing size (`Message-Size`) and client role (`Connection-Type`) declarations.
- **Connection Identifier Assignment (`RMF_CMD_ACCEPT_HEADER`)**: Replaces the basic acknowledgement response with an explicit command delivering a server-assigned 32-bit connection ID.
- **Rich Error Reporting (`RMF_CMD_NACK`)**: Expands negative acknowledgement from an empty opcode into a structured command containing a 32-bit error code and an optional node name string.
- **Cryptographic File Authentication (`RMF_CMD_PUBLISH_SIGNED_FILE`)**: Introduces file publication with attached digital signatures (ECDSA P-256), enabling zero-trust authentication of node interfaces.
- **Runtime Connection Monitoring (`RMF_CMD_CONNECTION_CREATE`, `RMF_CMD_CONNECTION_REVOKE`)**: Allows monitoring extensions to receive real-time connection lifecycle events.
- **Expanded File Types**: Formalizes support for dynamic files with 8-, 16-, and 32-bit length headers, device files, and streaming FIFO queues.

---

## Memory Model & Addressing

RemoteFile models communication as bidirectional memory synchronization. Each peer maintains two 1GB ($2^{30}$ bytes) virtual memory spaces:

| Memory Map | Address Range | Description |
|:---|:---|:---|
| **Local Map** | `0x00000000` – `0x3FFFFBFF` | Mapped files owned and published by the local endpoint (1,073,740,800 bytes). |
| **Remote Map** | `0x00000000` – `0x3FFFFFFF` | Mirrored files published by the remote peer, including the control area (1,073,741,824 bytes). |

The last 1KB (1024 bytes) of the remote address space (`0x3FFFFC00` – `0x3FFFFFFF`) is reserved for the **Control Area**, which is used to exchange commands such as file announcements, open/close requests, and connection lifecycle events.

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

- The first line must be the protocol identifier: `RMFP/1.1\n`
- Subsequent lines contain optional key-value attributes formatted as `Key: Value\n`
- The greeting message must terminate with an additional newline (`\n`).

**Example Greeting:**
```text
RMFP/1.1
Message-Size: 32


```

**Monitor Client Greeting Example:**
```text
RMFP/1.1
Message-Size: 32
Connection-Type: Monitor


```

### Greeting Constraints

- **Maximum Length**: The total length of the greeting message must not exceed 127 bytes. This ensures that the message length fits within the 1-byte short form of both NumHeader16 and NumHeader32.
- **Line Endings**: Every line must end with a single UNIX newline (`\n`, `0x0A`).

### Greeting Attributes

| Attribute | Format | Description |
|:---|:---|:---|
| `Message-Size` | `16` or `32` | Declares the NumHeader framing variant used for all subsequent messages from the client (default `32`). |
| `NumHeader-Format` | `16` or `32` | Legacy alias for `Message-Size` used in RemoteFile v1.0. |
| `Connection-Type` | `Default`, `Monitor`, or `Event` | Declares the connection role and subscription scope. Default is `Default`. |

**Connection Types:**
- `Default`: Standard node client that publishes and receives APX virtual files.
- `Monitor`: Administrative and monitoring client (used by `apx_info` and monitoring extensions) that receives server state updates and connection lifecycle events.
- `Event`: Event-stream subscription client.

### Handshake Sequence

In RemoteFile v1.1, the handshake protocol proceeds as follows:

1. **Client Greeting**: The client connects and sends its `RMFP/1.1` text header.
2. **Server Acceptance**:
   - The server validates the protocol version and parameters.
   - The server assigns a unique 32-bit `ConnectionId` to the session.
   - The server transmits `RMF_CMD_ACCEPT_HEADER` (`CmdType = 20`) containing the assigned `ConnectionId` to the client's Control Area (`0x3FFFFC00`).
   - *(In contrast to RemoteFile v1.0, where the server replied with a bare 4-byte `RMF_CMD_ACK`).*
3. **Session Active**: After receiving the accept command, the client and server transition to active binary message exchange.

---

## Binary Data Messages

After the greeting handshake completes, all communication consists exclusively of binary write messages.

Each write message payload contains:
1. **Address Header**: Encodes the target start address and fragmentation flags (2 or 4 bytes).
2. **Data Buffer**: The raw payload bytes to write into remote memory.

$$	ext{Data Buffer Length} = 	ext{Total Message Payload Length} - 	ext{Address Header Length}$$

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

| `CmdType` Constant | Value | Version | Description |
|:---|:---:|:---:|:---|
| `RMF_CMD_ACK` | 0 | v1.0 | Command Acknowledged |
| `RMF_CMD_NACK` | 1 | v1.1 | Negative Acknowledged (error code and node name) |
| *Reserved* | 2 | — | Reserved |
| `RMF_CMD_FILE_INFO` | 3 | v1.0 | Publish / announce an unauthenticated file |
| `RMF_CMD_REVOKE_FILE` | 4 | v1.0 | Revoke / unmap a published file |
| `RMF_CMD_HEARTBEAT_RQST` | 5 | v1.0 | Heartbeat Request |
| `RMF_CMD_HEARTBEAT_RSP` | 6 | v1.0 | Heartbeat Response |
| `RMF_CMD_PING_RQST` | 7 | v1.0 | Ping Request with timestamp |
| `RMF_CMD_PING_RSP` | 8 | v1.0 | Ping Response with timestamp |
| *Reserved* | 9 | — | Reserved |
| `RMF_CMD_FILE_OPEN` | 10 | v1.0 | Open a published file |
| `RMF_CMD_FILE_CLOSE` | 11 | v1.0 | Close an opened file |
| `RMF_CMD_ACCEPT_HEADER` | 20 | v1.1 | Handshake Protocol Header Accepted with Connection ID |
| `RMF_CMD_CONNECTION_CREATE` | 21 | v1.1 | New connection created notification |
| `RMF_CMD_CONNECTION_REVOKE` | 22 | v1.1 | Connection closed / revoked notification |
| `RMF_CMD_PUBLISH_SIGNED_FILE` | 23 | v1.1 | Publish / announce a cryptographically signed file |

---

### Handshake & Acknowledgment Commands

**Header Accepted Command (`RMF_CMD_ACCEPT_HEADER`):**
Sent by the server to a newly connected client upon validating its `RMFP/1.1` greeting header. It confirms successful negotiation and informs the client of its unique 32-bit connection identifier.

| Offset | Field | Type | Value Range | Description |
|:---:|:---|:---:|:---|:---|
| 0 | `CmdType` | `U32LE` | `20` (`RMF_CMD_ACCEPT_HEADER`) | Command Identifier |
| 4 | `ConnectionId` | `U32LE` | $0$ – $2^{32}-1$ | Assigned 32-bit Connection ID |

Total size: **8 bytes**.

**Acknowledge Command (`RMF_CMD_ACK`):**
Sent as a positive response to a command (and used in v1.0 for handshake confirmation).

| Offset | Field | Type | Value | Description |
|:---:|:---|:---:|:---|:---|
| 0 | `CmdType` | `U32LE` | `0` (`RMF_CMD_ACK`) | Command Identifier |

Total size: **4 bytes**.

---

### Error Handling Commands

**Negative Acknowledge Command (`RMF_CMD_NACK`):**
Sent to signal that an operation failed, an invalid command was received, or node verification failed. In RemoteFile v1.1, `NACK` conveys a 32-bit error code along with an optional null-terminated node name string identifying the failing component.

| Offset | Field | Type | Value Range | Description |
|:---:|:---|:---:|:---|:---|
| 0 | `CmdType` | `U32LE` | `1` (`RMF_CMD_NACK`) | Command Identifier |
| 4 | `ErrorCode` | `U32LE` | See Error Codes below | APX Error Code |
| 8 | `NodeName` | String | ASCII | Null-terminated name of the affected node (or `0x00` if no node is specified) |

Total size: $8 + 	ext{strlen(NodeName)} + 1$ bytes (minimum **9 bytes**).

#### Common APX Error Codes

| Error Code | Name | Description |
|:---:|:---|:---|
| `0` | `APX_NO_ERROR` | Success / no error |
| `1` | `APX_INVALID_ARGUMENT_ERROR` | Invalid or malformed argument |
| `3` | `APX_PARSE_ERROR` | Syntax or grammar parsing error |
| `10` | `APX_UNSUPPORTED_ERROR` | Command or feature unsupported by peer |
| `21` | `APX_NODE_ALREADY_EXISTS_ERROR` | Node definition already registered |
| `24` | `APX_FILE_ALREADY_EXISTS_ERROR` | File already mapped at requested address |
| `49` | `APX_FILE_NOT_FOUND_ERROR` | Referenced file not found |
| `65` | `APX_INVALID_HEADER_ERROR` | Malformed or unsupported protocol greeting |
| `79` | `APX_SIGNATURE_MISSING_ERROR` | Node definition requires signature but none provided |
| `80` | `APX_SIGNATURE_VERIFICATION_ERROR` | Cryptographic signature verification failed |

---

### File Management Commands

**FileInfo Command (`RMF_CMD_FILE_INFO`):**
Announces that an unauthenticated file is available and mapped at a specific start address in the sender's local memory map.

| Offset | Field | Type | Value Range | Description |
|:---:|:---|:---:|:---|:---|
| 0 | `CmdType` | `U32LE` | `3` (`RMF_CMD_FILE_INFO`) | Command Identifier |
| 4 | `StartAddress` | `U32LE` | `0` – `0x3FFFFBFF` | Start address of the file |
| 8 | `FileSize` | `U32LE` | `0` – `0x3FFFFC00` | Maximum size of the file in bytes |
| 12 | `FileType` | `U16LE` | `0` – `5` | File type descriptor (see below) |
| 14 | `DigestType` | `U16LE` | `0` – `2` | Checksum algorithm (see below) |
| 16 | `DigestData` | `UINT8[32]` | Bytes | 32-byte digest payload (zero-padded if unused) |
| 48 | `FileName` | String | ASCII | Null-terminated file name string |

The total size of the `FileInfo` structure is $48 + 	ext{strlen(FileName)} + 1$ bytes. Because the maximum command length is 1024 bytes, the maximum file name length is **975 bytes** (excluding the null terminator).

**PublishSignedFile Command (`RMF_CMD_PUBLISH_SIGNED_FILE`):**
Announces a cryptographically signed file. This command is typically used to publish `.apx` node definition files accompanied by an asymmetric digital signature for peer authentication.

| Offset | Field | Type | Value Range | Description |
|:---:|:---|:---:|:---|:---|
| 0 | `CmdType` | `U32LE` | `23` (`RMF_CMD_PUBLISH_SIGNED_FILE`) | Command Identifier |
| 4 | `StartAddress` | `U32LE` | `0` – `0x3FFFFBFF` | Start address of the file |
| 8 | `FileSize` | `U32LE` | `0` – `0x3FFFFC00` | Maximum size of the file in bytes |
| 12 | `FileType` | `U16LE` | `0` – `5` | File type descriptor (see below) |
| 14 | `SignatureType` | `U16LE` | `0` – `1` | Cryptographic signature type (see below) |
| 16 | `SignatureData` | `UINT8[64]` | Bytes | 64-byte cryptographic signature payload |
| 80 | `FileName` | String | ASCII | Null-terminated file name string |

The fixed header size of `PublishSignedFile` is **80 bytes**. The total structure size is $80 + 	ext{strlen(FileName)} + 1$ bytes. The maximum file name length is **943 bytes** (excluding the null terminator).

#### FileType Values

| Value | Identifier | Description |
|:---:|:---|:---|
| `0` | `FixedFile` | Fixed-size memory region (default for signals and definitions) |
| `1` | `DynamicFile8` | Dynamically sized file with 8-bit length header |
| `2` | `DynamicFile16` | Dynamically sized file with 16-bit length header |
| `3` | `DynamicFile32` | Dynamically sized file with 32-bit length header |
| `4` | `DeviceFile` | Stream-backed device file |
| `5` | `FileStream` | Streaming FIFO queue |

#### DigestType Values

| Value | Identifier | Description |
|:---:|:---|:---|
| `0` | `NoDigest` | No checksum provided |
| `1` | `SHA-1` | 20-byte SHA-1 hash (padded to 32 bytes) |
| `2` | `SHA-256` | 32-byte SHA-256 hash |

#### SignatureType Values

| Value | Identifier | Description |
|:---:|:---|:---|
| `0` | `NoSignature` | No cryptographic signature provided |
| `1` | `ECDSA_P256` | 64-byte raw ECDSA signature over NIST P-256 curve (concatenated 32-byte $r$ and 32-byte $s$ integers) |

#### Signed File Verification Flow

When a server is configured with `require-signed-nodes = true`:

1. **Publication**: The client sends `RMF_CMD_PUBLISH_SIGNED_FILE` with `SignatureType = 1` (`ECDSA_P256`) and the 64-byte signature extracted from the node's companion `.sig` file.
2. **Open Request**: The server maps the remote file and sends `RMF_CMD_FILE_OPEN`.
3. **Data Transmission**: The client writes the complete `.apx` definition payload to the remote address.
4. **Signature Verification**: Upon receiving the full file (`MORE_BIT = 0`), the server computes the SHA-256 hash of the payload and verifies the ECDSA signature against its list of configured trusted public keys.
5. **Acceptance / Rejection**:
   - If verified: The server parses the definition and publishes corresponding `.in` / `.out` / `.cout` / `.cin` files.
   - If verification fails: The server transmits `RMF_CMD_NACK` with `ErrorCode = 80` (`APX_SIGNATURE_VERIFICATION_ERROR`) and the node's name, discarding the untrusted node.
   - If an unsigned announcement (`RMF_CMD_FILE_INFO`) is received for a node definition: The server rejects the node with `ErrorCode = 79` (`APX_SIGNATURE_MISSING_ERROR`).

**FileRevoke Command (`RMF_CMD_REVOKE_FILE`):**
Unmaps a previously announced file. If the remote peer currently has the file open, it is automatically closed.

| Offset | Field | Type | Value | Description |
|:---:|:---|:---:|:---|:---|
| 0 | `CmdType` | `U32LE` | `4` (`RMF_CMD_REVOKE_FILE`) | Command Identifier |
| 4 | `StartAddress` | `U32LE` | `0` – `0x3FFFFBFF` | Start address of the file to revoke |

Total size: **8 bytes**.

**Multiple FileInfo Packing:**
Multiple `FileInfo` or `PublishSignedFile` structures may be packed into a single 1024-byte control write. When packing multiple structures:
- Only the **first structure** includes the 4-byte `CmdType` field.
- Subsequent structures begin immediately after the null terminator of the preceding file name (starting directly with `StartAddress`).

---

### Connection Lifecycle & Monitoring Commands

These commands are emitted by the server to connections operating in `Monitor` mode (`Connection-Type: Monitor`), allowing runtime diagnostic utilities (such as `apx-info`) to track client connections in real time.

**ConnectionCreate Command (`RMF_CMD_CONNECTION_CREATE`):**
Notifies monitoring clients that a new peer connection has connected and entered a given state.

| Offset | Field | Type | Value Range | Description |
|:---:|:---|:---:|:---|:---|
| 0 | `CmdType` | `U32LE` | `21` (`RMF_CMD_CONNECTION_CREATE`) | Command Identifier |
| 4 | `ConnectionId` | `U32LE` | $0$ – $2^{32}-1$ | Unique connection identifier |
| 8 | `ConnectionState` | `UINT8` | `0` – `3` | Connection state (see below) |
| 9 | `ConnectionTag` | String | ASCII | Null-terminated string label or client address |

Total size: $9 + 	ext{strlen(ConnectionTag)} + 1$ bytes.

#### ConnectionState Values

| Value | Identifier | Description |
|:---:|:---|:---|
| `0` | `APX_CONNECTION_STATE_CREATED` | Connection object created |
| `1` | `APX_CONNECTION_STATE_CONNECTING` | Physical socket connection established, greeting pending |
| `2` | `APX_CONNECTION_STATE_ACCEPTED` | Protocol greeting accepted and active |
| `3` | `APX_CONNECTION_STATE_CLOSED` | Connection terminated |

**ConnectionRevoke Command (`RMF_CMD_CONNECTION_REVOKE`):**
Notifies monitoring clients that an active connection has disconnected or has been closed.

| Offset | Field | Type | Value Range | Description |
|:---:|:---|:---|:---|:---|
| 0 | `CmdType` | `U32LE` | `22` (`RMF_CMD_CONNECTION_REVOKE`) | Command Identifier |
| 4 | `ConnectionId` | `U32LE` | $0$ – $2^{32}-1$ | Identifier of the revoked connection |

Total size: **8 bytes**.

---

### Diagnostic Commands

Used to verify transport liveness, measure round-trip latency, and test route paths.

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
Requests to open a remote file announced via a preceding `FileInfo` or `PublishSignedFile` command.

| Offset | Field | Type | Value Range | Description |
|:---:|:---|:---:|:---|:---|
| 0 | `CmdType` | `U32LE` | `10` (`RMF_CMD_FILE_OPEN`) | Command Identifier |
| 4 | `StartAddress` | `U32LE` | `0` – `0x3FFFFBFF` | Start address of the remote file to open |

Total size: **8 bytes**.

**FileClose Command (`RMF_CMD_FILE_CLOSE`):**
Closes a previously opened remote file.

| Offset | Field | Type | Value Range | Description |
|:---:|:---|:---:|:---|:---|
| 0 | `CmdType` | `U32LE` | `11` (`RMF_CMD_FILE_CLOSE`) | Command Identifier |
| 4 | `StartAddress` | `U32LE` | `0` – `0x3FFFFBFF` | Start address of the remote file to close |

Total size: **8 bytes**.

---

## Comparison: RemoteFile v1.0 vs v1.1

The following table summarizes the protocol changes between RemoteFile v1.0 and RemoteFile v1.1:

| Feature | RemoteFile v1.0 | RemoteFile v1.1 |
|:---|:---|:---|
| **Greeting Header** | `RMFP/1.0\n` | `RMFP/1.1\n` |
| **Greeting Framing Attr** | `NumHeader-Format: 16\|32` | `Message-Size: 16\|32` (with `NumHeader-Format` alias) |
| **Greeting Role Attr** | None | `Connection-Type: Default\|Monitor\|Event` |
| **Handshake Response** | `RMF_CMD_ACK` (4 bytes) | `RMF_CMD_ACCEPT_HEADER` (8 bytes, includes `ConnectionId`) |
| **Error Signaling** | Empty `RMF_CMD_NACK` (opcode only) | Structured `RMF_CMD_NACK` with `ErrorCode` and `NodeName` |
| **Signed File Publication** | Not supported | `RMF_CMD_PUBLISH_SIGNED_FILE` (ECDSA P-256, 64-byte signature) |
| **Connection Monitoring** | Not supported | `RMF_CMD_CONNECTION_CREATE`, `RMF_CMD_CONNECTION_REVOKE` |
| **Virtual File Types** | Fixed (`0`), Dynamic (`1`), Stream (`2`) | Fixed (`0`), Dynamic8 (`1`), Dynamic16 (`2`), Dynamic32 (`3`), Device (`4`), Stream (`5`) |
| **Backward Compatibility** | Client baseline | Server supports both v1.0 and v1.1 clients simultaneously |
