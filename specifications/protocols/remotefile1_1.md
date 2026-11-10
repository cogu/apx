# RemoteFile v1.1 (Unreleased)

RemoteFile is a binary, message-based protocol used to synchronize virtual memory regions across a point-to-point communication link (such as a TCP socket, UNIX domain socket, or shared memory). It acts as the application transport layer of an active APX session.

```{note}
For an architectural overview, memory model rationale, and high-level diagrams, see [The RemoteFile Protocol in Internal Design](../../design/remotefile.md).
```

## Overview of RemoteFile v1.1

RemoteFile v1.1 extends the baseline RemoteFile v1.0 protocol with enhanced handshake negotiation, explicit error signaling, compressed definitions, stream files, and cryptographic authentication:

- **Protocol Greeting & Handshake**: Employs protocol identifier `RMFP/1.1\n` with explicit framing size (`Message-Size`) and client role (`Connection-Type`) declarations.
- **Connection Identifier Assignment (`RMF_CMD_ACCEPT_HEADER`)**: Replaces the basic acknowledgement response with an explicit command delivering a server-assigned 32-bit connection ID.
- **Rich Error Reporting (`RMF_CMD_NACK`)**: Expands negative acknowledgement from an empty opcode into a structured command containing a 32-bit error code and an optional node name string.
- **Cryptographic File Authentication (`RMF_CMD_PUBLISH_SIGNED_FILE`)**: Introduces file publication with attached digital signatures (ECDSA P-256), enabling zero-trust authentication of node interfaces.
- **Compressed Definition Transfer (`RMF_CMD_PUBLISH_COMPRESSED_FILE`, `RMF_CMD_PUBLISH_SIGNED_COMPRESSED_FILE`)**: Supports unsigned and signed APX definitions using zlib-wrapped DEFLATE, including payloads precompressed during embedded code generation.
- **Application-Level Events**: Monitoring and logging events use independent event identifiers carried in stream payloads, not RemoteFile control-command identifiers.
- **Stream Files (`FileStream`)**: Formalizes block-preserving streaming over RemoteFile with dedicated buffer negotiation (`RMF_CMD_STREAM_OPEN`, `RMF_CMD_STREAM_OPEN_RSP`), cumulative credit-based flow control (`RMF_CMD_STREAM_WINDOW_UPDATE`), and per-stream abort signaling (`RMF_CMD_STREAM_ABORT`).
- **Expanded File Types**: Formalizes support for dynamic files with 8-, 16-, and 32-bit length headers, device files, and streaming FIFO queues.

---

## Memory Model & Addressing

RemoteFile models communication as bidirectional memory synchronization. Each peer maintains two 1GB ($2^{30}$ bytes) virtual memory spaces:

| Memory Map | Address Range | Description |
|:---|:---|:---|
| **Local Map** | `0x00000000` – `0x3FFFFBFF` | Mapped files owned and published by the local endpoint (1,073,740,800 bytes). |
| **Remote Map** | `0x00000000` – `0x3FFFFFFF` | Mirrored files published by the remote peer, including the control area (1,073,741,824 bytes). |

The last 1KB (1024 bytes) of the remote address space (`0x3FFFFC00` – `0x3FFFFFFF`) is reserved for the **Control Area**, which is used to exchange commands such as file announcements, open/close requests, and stream control.

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
> While an ordinary memory-mapped file remains open, local modifications must be
> propagated to the remote mirror without unnecessary delay. An implementation
> may batch updates during a bounded application operation and transmit coalesced
> byte ranges when that operation completes. Coalesced writes may include
> unchanged bytes between modified ranges, but must preserve the resulting file
> contents and application-level ordering dependencies.
>
> This synchronizes memory state, not a history of every intermediate value
> written during the operation.

This rule does not permit coalescing or discarding `FileStream` blocks. Their
message boundaries and delivery semantics are defined in the stream-file
sections below.

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
| `NumHeader-Format` | `16` or `32` | Accepted alias for `Message-Size` in RemoteFile v1.1, retained for compatibility with the legacy greeting attribute. |
| `Connection-Type` | `Default`, `Monitor`, or `Event` | Declares the connection role and subscription scope. Default is `Default`. |

A RemoteFile v1.1 server MUST accept either `Message-Size` or
`NumHeader-Format` to select the same framing variant. Clients need send only
one of these equivalent attributes. Both accept `16` or `32`; omitting the
attribute selects `32`. Accepting the legacy attribute name does not change
the negotiated protocol version: an `RMFP/1.1` greeting still receives
`RMF_CMD_ACCEPT_HEADER`, not the v1.0 `RMF_CMD_ACK`.

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
| `RMF_CMD_PUBLISH_SIGNED_FILE` | 21 | v1.1 | Publish / announce a cryptographically signed file |
| `RMF_CMD_PUBLISH_COMPRESSED_FILE` | 22 | v1.1 | Publish / announce a zlib-compressed unsigned APX definition |
| `RMF_CMD_PUBLISH_SIGNED_COMPRESSED_FILE` | 23 | v1.1 | Publish / announce a zlib-compressed signed APX definition |
| `RMF_CMD_STREAM_OPEN` | 24 | v1.1 | Open stream file with buffer & window negotiation |
| `RMF_CMD_STREAM_OPEN_RSP` | 25 | v1.1 | Stream open response with negotiated parameters |
| `RMF_CMD_STREAM_WINDOW_UPDATE` | 26 | v1.1 | Cumulative credit window update for stream flow control |
| `RMF_CMD_STREAM_ABORT` | 27 | v1.1 | Abort stream file session |

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
| `32` | `APX_FILE_TOO_LARGE_ERROR` | File exceeds an implementation-defined size limit |
| `44` | `APX_INVALID_MSG_ERROR` | Malformed or incomplete command structure |
| `49` | `APX_FILE_NOT_FOUND_ERROR` | Referenced file not found |
| `65` | `APX_INVALID_HEADER_ERROR` | Malformed or unsupported protocol greeting |
| `79` | `APX_SIGNATURE_MISSING_ERROR` | Node definition requires signature but none provided |
| `80` | `APX_SIGNATURE_VERIFICATION_ERROR` | Cryptographic signature verification failed |

---

### File Management Commands

**FileInfo Command (`RMF_CMD_FILE_INFO`):**
Announces that an unauthenticated, uncompressed file is available and mapped at a specific start address in the sender's local memory map. This is the legacy unsigned `PUBLISH_FILE` command.

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
Announces a cryptographically signed, uncompressed file. This command is typically used to publish `.apx` node definition files accompanied by an asymmetric digital signature for definition-content authentication.

| Offset | Field | Type | Value Range | Description |
|:---:|:---|:---:|:---|:---|
| 0 | `CmdType` | `U32LE` | `21` (`RMF_CMD_PUBLISH_SIGNED_FILE`) | Command Identifier |
| 4 | `StartAddress` | `U32LE` | `0` – `0x3FFFFBFF` | Start address of the file |
| 8 | `FileSize` | `U32LE` | `0` – `0x3FFFFC00` | Maximum size of the file in bytes |
| 12 | `FileType` | `U16LE` | `0` – `5` | File type descriptor (see below) |
| 14 | `SignatureType` | `U16LE` | `0` – `1` | Cryptographic signature type (see below) |
| 16 | `SignatureData` | `UINT8[64]` | Bytes | 64-byte cryptographic signature payload |
| 80 | `FileName` | String | ASCII | Null-terminated file name string |

The fixed header size of `PublishSignedFile` is **80 bytes**. The total structure size is $80 + 	ext{strlen(FileName)} + 1$ bytes. The maximum file name length is **943 bytes** (excluding the null terminator).

#### Compressed Definition Transfer

Compression is independent of signing. The following commands announce immutable, fixed-size `.apx` definition files with compressed wire payloads, using separate unsigned and signed publication forms. Ordinary uncompressed publication remains unchanged.

**PublishCompressedFile Command (`RMF_CMD_PUBLISH_COMPRESSED_FILE`):**
Announces an unsigned compressed definition, optionally accompanied by a SHA-256 digest of the uncompressed bytes.

| Offset | Field | Type | Value Range | Description |
|:---:|:---|:---:|:---|:---|
| 0 | `CmdType` | `U32LE` | `22` (`RMF_CMD_PUBLISH_COMPRESSED_FILE`) | Command Identifier |
| 4 | `StartAddress` | `U32LE` | `0` - `0x3FFFFBFF` | Start address of the encoded file |
| 8 | `UncompressedSize` | `U32LE` | `1` - `0x3FFFFC00` | Exact decoded definition size |
| 12 | `CompressedSize` | `U32LE` | `1` - `0x3FFFFC00` | Exact encoded payload size |
| 16 | `FileType` | `U16LE` | `0` | `FixedFile` only |
| 18 | `CompressionType` | `U16LE` | `1` | `ZlibDeflate` |
| 20 | `DigestType` | `U16LE` | `0` or `2` | `NoDigest` or `SHA-256` over decoded bytes |
| 22 | `Reserved` | `U16LE` | `0` | MUST be zero |
| 24 | `DigestData` | `UINT8[32]` | Bytes | SHA-256 digest; all zero when `DigestType = 0` |
| 56 | `FileName` | String | ASCII | Null-terminated original `.apx` file name |

The fixed header size is **56 bytes**. The total command size is `56 + strlen(FileName) + 1`; the maximum file name length is **967 bytes**, excluding the terminator.

**PublishSignedCompressedFile Command (`RMF_CMD_PUBLISH_SIGNED_COMPRESSED_FILE`):**
Announces a signed compressed definition. As for uncompressed signed publication, the signature uses ECDSA-P256 with SHA-256 over the exact uncompressed definition bytes, not the compressed stream.

| Offset | Field | Type | Value Range | Description |
|:---:|:---|:---:|:---|:---|
| 0 | `CmdType` | `U32LE` | `23` (`RMF_CMD_PUBLISH_SIGNED_COMPRESSED_FILE`) | Command Identifier |
| 4 | `StartAddress` | `U32LE` | `0` - `0x3FFFFBFF` | Start address of the encoded file |
| 8 | `UncompressedSize` | `U32LE` | `1` - `0x3FFFFC00` | Exact decoded definition size |
| 12 | `CompressedSize` | `U32LE` | `1` - `0x3FFFFC00` | Exact encoded payload size |
| 16 | `FileType` | `U16LE` | `0` | `FixedFile` only |
| 18 | `CompressionType` | `U16LE` | `1` | `ZlibDeflate` |
| 20 | `SignatureType` | `U16LE` | `1` | `ECDSA_P256` |
| 22 | `Reserved` | `U16LE` | `0` | MUST be zero |
| 24 | `SignatureData` | `UINT8[64]` | Bytes | 64-byte signature over uncompressed data |
| 88 | `FileName` | String | ASCII | Null-terminated file name string |

The fixed header size is **88 bytes**. The total command size is `88 + strlen(FileName) + 1`; the maximum file name length is **935 bytes**, excluding the terminator. All integer fields are encoded explicitly in little-endian order; native struct padding is not part of either command.

**CompressionType Values:**

| Value | Identifier | Description |
|:---:|:---|:---|
| `0` | `NoCompression` | Not valid in the compressed commands; use existing uncompressed publication |
| `1` | `ZlibDeflate` | One zlib stream (RFC 1950) containing DEFLATE data (RFC 1951) |

`ZlibDeflate` requires compression method 8, a window no larger than 32 KiB, and no preset dictionary (`FDICT = 0`). The receiver MUST validate the zlib header and Adler-32 trailer. Raw DEFLATE, gzip, concatenated streams, and trailing bytes are not valid for this identifier.

**Addressing and Transfer Rules:**

* The mapped RemoteFile range is `[StartAddress, StartAddress + CompressedSize)`. Validate `CompressedSize <= 0x3FFFFC00 - StartAddress` before mapping or allocating; `UncompressedSize` does not determine the wire address range.
* Use the original `.apx` name. The encoded bytes represent the transfer, while the decoded bytes represent the logical APX definition.
* When a transfer is required, open the encoded file with the ordinary `RMF_CMD_FILE_OPEN`. An unsigned cache hit may avoid opening the file, as specified below. Each open starts at offset zero and transfers the full immutable stream using sequential, non-overlapping data writes. Writes with gaps, overlap, or bytes outside the declared range are invalid.
* Intermediate writes set `MORE_BIT = 1`; the final write sets `MORE_BIT = 0` and MUST end at exactly `CompressedSize`. Reject an early final write, an oversized write, or further data after completion unless a new open has started a fresh transfer.
* Successful decoding MUST consume exactly `CompressedSize` bytes, reach the end of one valid zlib stream, and produce exactly `UncompressedSize` bytes. Bound output during decoding, not only after it finishes.
* Sizes, digests, and signatures exclude any C-string terminator added by an implementation. No line-ending normalization or other text transformation is permitted between decoding and integrity verification.
* Apply implementation-defined per-definition and aggregate in-flight resource limits before allocation, including overflow-safe space for any local text terminator. On failure, revoke, timeout, reopen, or disconnect, discard partial state and release resources. A reopened transfer starts with a fresh decoder.

**Integrity, Errors, and Compatibility:**

* When an unsigned definition with `DigestType = 2` is transferred, it MUST pass SHA-256 verification over the decoded bytes before acceptance. A validated cache entry may instead supply the definition without transfer, as specified below. A digest or Adler-32 checksum is not authentication.
* A signed publication MUST pass ECDSA-P256/SHA-256 verification over the decoded bytes against trusted keys before acceptance. A receiver requiring signed nodes MUST reject unsigned compressed publication with `APX_SIGNATURE_MISSING_ERROR`, just as it rejects unsigned uncompressed publication.
* Do not parse, register, or route a node until the applicable transfer-validation or cache-hit requirements below are satisfied. Cache identities refer to uncompressed content; compression does not introduce a signed-transfer verification bypass.
* Preserve the distinction between an unsupported algorithm, an invalid
  publication, and corrupt transferred data. Use the error categories defined
  below rather than reporting every decoding failure as a malformed message.
* Encoding and signing choices are independent of codec library and compression level. Generated embedded clients may contain only the selected representation and require no runtime codec.
* Compression-capable peers must be selected by deployment configuration or generation-time knowledge. An RMFP 1.1 greeting alone does not prove that an older development implementation supports these additions. No capability negotiation or automatic fallback is specified here.
* For v1.0/v0.2.8 compatibility, use the legacy greeting, unsigned `RMF_CMD_FILE_INFO` publication (also named `RMF_CMD_PUBLISH_FILE_MSG` in c-apx), and plain definition bytes. Do not assume legacy peers return a structured NACK for unknown commands, and never send compressed data under an uncompressed announcement.

#### Compressed Definition Error Reporting

| Failure | Error Code |
|:---|:---|
| Unsupported compression, digest, or signature algorithm in an otherwise valid publication | `APX_UNSUPPORTED_ERROR` (`10`) |
| Malformed or truncated publication command structure, such as a missing file-name terminator | `APX_INVALID_MSG_ERROR` (`44`) |
| Invalid command fields, such as a nonzero reserved field, invalid address range, or zero or protocol-out-of-range size | `APX_INVALID_ARGUMENT_ERROR` (`1`) |
| Otherwise valid `CompressedSize` or `UncompressedSize` exceeds an implementation-defined per-definition size limit | `APX_FILE_TOO_LARGE_ERROR` (`32`) |
| Malformed compressed stream, transfer-length error, or digest mismatch | `APX_PARSE_ERROR` (`3`) |
| Missing signature when a signature is required | `APX_SIGNATURE_MISSING_ERROR` (`79`) |
| Signature verification fails | `APX_SIGNATURE_VERIFICATION_ERROR` (`80`) |

The distinction between invalid sizes and implementation limits is deliberate:
a zero size or a range outside the protocol's address space is an invalid
argument; a size that is valid on the wire but exceeds the receiver's configured
per-definition limit is a file-too-large error.

When command boundaries remain intact and the connection remains usable, the
receiver MUST report a rejection with `RMF_CMD_NACK` and the applicable error
code. In particular, a structurally valid publication using an unsupported
algorithm MUST receive `APX_UNSUPPORTED_ERROR`; the receiver MUST NOT close
the connection solely because that algorithm is unsupported. Reject that
publication without requesting its payload or accepting its node, and allow
subsequent commands to be processed normally.

If framing is lost or the connection is otherwise unusable, report the error
through normal local diagnostics and close the connection as necessary instead
of attempting to continue. Rejecting a publication does not introduce automatic
algorithm negotiation or fallback.

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

#### Definition Cache Interaction

Caching is optional and does not change the publication layouts. All four publication variants can reuse compatible compiled definitions. SHA-256 cache identities, optional advertised digests, and signatures refer to the exact **uncompressed definition bytes**, excluding any local C-string terminator.

| Publication | Skip definition transfer on a cache hit? | Reuse a compatible compiled definition? |
|:---|:---|:---|
| `RMF_CMD_FILE_INFO` / `PUBLISH_FILE` (3) | Yes, with an advertised SHA-256 matching a valid local cache entry | Yes |
| `RMF_CMD_PUBLISH_SIGNED_FILE` (21) | No; request the definition and verify its signature | Yes, after verification |
| `RMF_CMD_PUBLISH_COMPRESSED_FILE` (22) | Yes, with an advertised SHA-256 matching a valid local cache entry | Yes |
| `RMF_CMD_PUBLISH_SIGNED_COMPRESSED_FILE` (23) | No; request, decompress, and verify the definition | Yes, after verification |

For either unsigned form, check signed-node policy before consulting the cache. If unsigned definitions are permitted and `DigestType = 2`, a receiver MAY use a valid cached text or compiled definition matching the advertised SHA-256, node identity, and logical definition size instead of sending `RMF_CMD_FILE_OPEN`. Validate cached content and compiled-format/compiler/VM compatibility as applicable. A text-only hit still requires parsing and compilation, but neither a text nor compiled hit requires definition transfer or decompression. No definition-transfer buffers or decoder state are needed for this fast path.

If caching is disabled, no usable digest is advertised, or no valid matching entry exists, request the file and validate the transferred definition normally. After transfer, the receiver may compute SHA-256 and reuse a compatible compiled entry even when no digest was advertised.

For either signed form, the receiver MUST request the full definition on every connection and verify the signature against the received uncompressed bytes before using a compiled cache entry. For the compressed form, bounded decompression and stream validation precede signature verification. The resulting SHA-256 can then identify compatible precompiled content and bypass parsing/compilation; a cache hit MUST NOT bypass transfer or verification under this policy.

An unsigned digest, a matching cached definition, or the zlib checksum does not authenticate a client and cannot satisfy a signed-node requirement. A definition signature authenticates content, not client identity, freshness, or possession of a signing key. Invalid transferred content MUST be rejected rather than replaced by a cached success.

Precompression and signing may both happen during embedded code generation or a build step. An APX-ES node may store only the compressed byte array, its lengths, and the signature; it requires neither a runtime codec nor an on-device signing key to publish that definition.

#### Signed File Verification Flow

When a server is configured with `require-signed-nodes = true`:

1. **Publication**: The client sends `RMF_CMD_PUBLISH_SIGNED_FILE`, or `RMF_CMD_PUBLISH_SIGNED_COMPRESSED_FILE` for a compressed definition, with `SignatureType = 1` (`ECDSA_P256`) and the 64-byte signature over the exact definition bytes.
2. **Open Request**: The server maps the remote file and sends `RMF_CMD_FILE_OPEN`.
3. **Data Transmission**: The client writes the complete plain or compressed definition payload to the remote address, according to its announcement.
4. **Signature Verification**: Upon receiving the full file (`MORE_BIT = 0`), the server first performs bounded decompression if applicable, then computes SHA-256 over the exact uncompressed definition bytes and verifies the ECDSA signature against its configured trusted public keys.
5. **Acceptance / Rejection**:
   - If verified: The server loads a compatible compiled cache entry identified by the verified definition's SHA-256, or parses and compiles the received definition if no usable compiled entry exists, then publishes corresponding `.in` / `.out` / `.cout` / `.cin` files.
   - If verification fails: The server transmits `RMF_CMD_NACK` with `ErrorCode = 80` (`APX_SIGNATURE_VERIFICATION_ERROR`) and the node's name, discarding the untrusted node.
   - If an unsigned announcement (`RMF_CMD_FILE_INFO` or `RMF_CMD_PUBLISH_COMPRESSED_FILE`) is received for a node definition: The server rejects the node with `ErrorCode = 79` (`APX_SIGNATURE_MISSING_ERROR`).

**FileRevoke Command (`RMF_CMD_REVOKE_FILE`):**
Unmaps a previously announced file. If the remote peer currently has the file open, it is automatically closed.

| Offset | Field | Type | Value | Description |
|:---:|:---|:---:|:---|:---|
| 0 | `CmdType` | `U32LE` | `4` (`RMF_CMD_REVOKE_FILE`) | Command Identifier |
| 4 | `StartAddress` | `U32LE` | `0` – `0x3FFFFBFF` | Start address of the file to revoke |

Total size: **8 bytes**.

---

### Monitoring and Application Events

Monitoring and logging use application-defined event records carried in `FileStream` payloads. Connection-create/close, file, and other event identifiers belong to that independent event namespace, not to the RemoteFile control-command namespace.

RemoteFile provides publication, stream transport, and flow control for those records. It does not allocate control commands for individual application events; the previous draft's connection-lifecycle and monitor file-publication commands are obsolete.

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
Requests to open a remote file announced via any of the four publication commands. For compressed definitions, the requested data is the encoded stream described by `CompressedSize`. An accepted unsigned definition cache hit can make this request unnecessary.

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

## Stream Files (FileStream)

RemoteFile v1.1 formalizes streaming communication through the `FileStream` descriptor (`FileType = 5`). While standard fixed files (`FileType = 0`) synchronize memory regions where successive writes overwrite bytes at specific offsets, stream files model sequential, discrete message queues.

### Reserved Address Range and Block-Size Limits

A published stream reserves the virtual address range
`[StartAddress, StartAddress + FileSize)`, with `FileSize > 0`. The range MUST
fit below the Control Area and MUST NOT overlap another mapped file. Validate
`FileSize <= 0x3FFFFC00 - StartAddress` after checking
`StartAddress < 0x3FFFFC00`, rather than relying on an addition that could
overflow.

The range is reused for every logical block. It is not persistent storage for
the stream's history, and its size does not limit the total number of bytes
that may be sent over the lifetime of the stream.

`FileSize` limits the size of one **complete application block**, not merely
the size of an individual transport fragment. The open handshake negotiates
`BlockSize`, which may impose a smaller limit:

```text
1 <= CompleteBlockLength <= BlockSize <= FileSize
```

These lengths count application payload bytes only, excluding NumHeader and
AddressHeader bytes. Fragmentation MUST NOT be used to bypass the complete
block limit. The receive window may hold several blocks, but `WindowBlocks`
does not enlarge the stream's reserved address range.

### Logical Blocks and Transport Fragments

1. **Block preservation:** One logical stream write carries one complete
   application block. The receiver MUST preserve its boundary and deliver the
   block only after the complete write has been reassembled.
2. **Block start:** Every logical write MUST start at the stream's advertised
   `StartAddress` (offset zero). An unfragmented block uses this address with
   `MORE_BIT = 0`.
3. **Fragment addresses:** A logical write MAY be split into several transport
   messages. If `O` payload bytes of the current block precede a fragment, that
   fragment's AddressHeader MUST target `StartAddress + O`. Intermediate
   fragments set `MORE_BIT = 1`; the final fragment clears `MORE_BIT = 0`.
4. **Bounds:** For a fragment containing `L` payload bytes, the receiver MUST
   check `O <= BlockSize` and `L <= BlockSize - O` before accepting its data.
   Together with `BlockSize <= FileSize`, this keeps all payload bytes inside
   the reserved file range. A non-consecutive or oversized continuation MUST
   be rejected as an invalid block, not dispatched as a write into a
   neighbouring file.
5. **Application delivery:** After the final fragment, the receiver delivers
   the reassembled block with application offset zero. Fragment offsets are
   not independent random-access writes to the stream file.
6. **Range reuse:** The next logical block starts again at `StartAddress`.
   Fragment offsets accumulate only within the current block; they MUST NOT
   continue accumulating across blocks.

NumHeader delimits each transport message, while `MORE_BIT` identifies the end
of a logical block. Applications such as diagnostics and binary logging can
therefore use one block per message without adding another message-length
field. An application may concatenate completed block payloads if it wants a
byte stream, but RemoteFile itself preserves the block boundaries.

### Address-Range Example

Suppose a stream is published at `StartAddress = 0x10000` with
`FileSize = 2048 = 0x800`, and the negotiated `BlockSize` is also 2048.
Its reserved range is `[0x10000, 0x10800)`.

A 1536-byte block (`0x600` bytes) may be sent as:

| Block | Fragment | Address | Payload bytes | `MORE_BIT` |
|:---|:---|:---|:---|:---|
| A | 1 | `0x10000` | 512 (`0x200`) | 1 |
| A | 2 | `0x10200` | 512 (`0x200`) | 1 |
| A | 3 | `0x10400` | 512 (`0x200`) | 0 |
| B | 1, unfragmented | `0x10000` | 512 (`0x200`) | 0 |

Block A uses payload addresses `0x10000` through `0x105FF`, then is delivered
once as 1536 bytes. No padding is transmitted for the unused part of the range.
Block B reuses the start address; it does not begin at `0x10600` or `0x10800`.
A neighbouring file may start at `0x10800` without being written by either
block.

Block A requires both `FileSize` and negotiated `BlockSize` to be at least
`0x600`. A stream with `FileSize = 512` cannot carry that block as three
512-byte fragments: the limit applies to their combined payload size.

---

### Stream Lifecycle & Commands

Because standard `RMF_CMD_FILE_OPEN` provides no mechanism to negotiate maximum frame buffers or buffer capacities, stream files utilize a specialized open handshake and flow-control mechanism:

#### StreamOpen Command (`RMF_CMD_STREAM_OPEN`)

Sent by the file receiver to the file publisher to request opening a published `FileStream`.

| Offset | Field | Type | Value Range | Description |
|:---:|:---|:---|:---|:---|
| 0 | `CmdType` | `U32LE` | `24` (`RMF_CMD_STREAM_OPEN`) | Command Identifier |
| 4 | `StartAddress` | `U32LE` | `0` – `0x3FFFFBFF` | Start address of published `FileStream` |
| 8 | `MaxBlockSize` | `U32LE` | $1$ – $2^{32}-1$ | Largest complete block payload (bytes) accepted by receiver |
| 12 | `WindowBlocks` | `U16LE` | $1$ – $65535$ | Maximum unconsumed complete blocks receiver can buffer |
| 14 | `Flags` | `U16LE` | `0` | Reserved; MUST be zero |

Total size: **16 bytes**.

#### StreamOpenResponse Command (`RMF_CMD_STREAM_OPEN_RSP`)

Sent by the stream publisher to the receiver in response to `RMF_CMD_STREAM_OPEN`.

| Offset | Field | Type | Value Range | Description |
|:---:|:---|:---|:---|:---|
| 0 | `CmdType` | `U32LE` | `25` (`RMF_CMD_STREAM_OPEN_RSP`) | Command Identifier |
| 4 | `StartAddress` | `U32LE` | `0` – `0x3FFFFBFF` | Start address of the stream |
| 8 | `Status` | `U32LE` | `0` (Success) or Error | APX Error Code (`0` indicates success) |
| 12 | `BlockSize` | `U32LE` | $1$ – $2^{32}-1$ | Negotiated maximum complete block payload size |
| 16 | `WindowBlocks` | `U16LE` | $1$ – $65535$ | Accepted receive window (blocks) |
| 18 | `Flags` | `U16LE` | `0` | Reserved; MUST be zero |

Total size: **20 bytes**.

On success:
- `BlockSize <= min(published FileSize, requested MaxBlockSize)`
- `WindowBlocks <= requested WindowBlocks`
- Both `BlockSize` and `WindowBlocks` MUST be greater than zero.

```text
Receiver                                           Publisher
   |                                                   |
   |<-- RMF_CMD_FILE_INFO(FileStream, FileSize) -------|
   |                                                   |
   |--- RMF_CMD_STREAM_OPEN -------------------------->|
   |    MaxBlockSize, WindowBlocks                     |
   |                                                   |
   |<-- RMF_CMD_STREAM_OPEN_RSP -----------------------|
   |    Status=0, BlockSize, WindowBlocks              |
   |                                                   |
   |<== Stream blocks (subject to credit window) ======|
```

The publisher MUST NOT transmit stream data blocks before emitting a successful `RMF_CMD_STREAM_OPEN_RSP`.

---

### Credit-Based Flow Control

To protect resource-constrained nodes from buffer exhaustion and isolate streams from general socket traffic, `FileStream` implements cumulative credit-based flow control:

#### StreamWindowUpdate Command (`RMF_CMD_STREAM_WINDOW_UPDATE`)

Sent by the stream receiver to the publisher to report consumed blocks and grant transmission credit.

| Offset | Field | Type | Value Range | Description |
|:---:|:---|:---|:---|:---|
| 0 | `CmdType` | `U32LE` | `26` (`RMF_CMD_STREAM_WINDOW_UPDATE`) | Command Identifier |
| 4 | `StartAddress` | `U32LE` | `0` – `0x3FFFFBFF` | Start address of open stream |
| 8 | `ConsumedBlockCount` | `U64LE` | $0$ – $2^{64}-1$ | Cumulative count of consumed complete blocks |

Total size: **16 bytes**.

#### Flow Control Rules

1. **Credit Invariant**: At any moment, the publisher MUST satisfy:
   $$\text{TransmittedBlockCount} - \text{ConsumedBlockCount} \le \text{WindowBlocks}$$
2. **Block Consumption**: A block is considered consumed only after the receiver application layer has processed and released it from the receive buffer.
3. **Update Batching**: The receiver SHOULD batch window updates to avoid control traffic congestion. An update SHOULD be transmitted whenever at least $50\%$ of `WindowBlocks` has been consumed since the prior update, or when the consumed count reaches the current window limit.
4. **Blocks, not fragments**: Transmission and consumption counters count
   complete logical blocks, not individual transport fragments. These counters
   accumulate for the open stream session and are independent of fragment
   offsets, which restart at zero for every block. Neither the counters nor
   the receive window cause stream addresses to advance beyond the reserved
   file range.

---

### Stream Abort

Either peer may terminate an active stream without tearing down the underlying physical connection:

#### StreamAbort Command (`RMF_CMD_STREAM_ABORT`)

| Offset | Field | Type | Value Range | Description |
|:---:|:---|:---|:---|:---|
| 0 | `CmdType` | `U32LE` | `27` (`RMF_CMD_STREAM_ABORT`) | Command Identifier |
| 4 | `StartAddress` | `U32LE` | `0` – `0x3FFFFBFF` | Start address of stream |
| 8 | `Status` | `U32LE` | Error Code | Non-zero APX Error Code describing the reason |

Total size: **12 bytes**.

Upon sending or receiving `RMF_CMD_STREAM_ABORT`:
- Any partially received or incomplete block is discarded.
- In-flight queued blocks are released.
- Flow control state and window allocations are reset.
- The stream transitions back to the announced/closed state, and may subsequently be re-opened with `RMF_CMD_STREAM_OPEN`.

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
| **Compressed Definitions** | Not supported; publish plain text | Unsigned or signed zlib-wrapped DEFLATE publication |
| **Monitoring / Logging Events** | No dedicated event commands | Independent application event records carried in `FileStream` payloads |
| **Virtual File Types** | Fixed (`0`), Dynamic (`1`), Stream (`2`) | Fixed (`0`), Dynamic8 (`1`), Dynamic16 (`2`), Dynamic32 (`3`), Device (`4`), Stream (`5`) |
| **Stream Files** | Reserved type (`2`), undefined semantics | Fully specified `FileStream` (`5`), discrete block writes, negotiated buffer size, cumulative credit flow control (`RMF_CMD_STREAM_*`), and stream abort |
| **Backward Compatibility** | Client baseline | Server supports both v1.0 and v1.1 clients simultaneously |
