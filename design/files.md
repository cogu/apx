# Node Virtual Files and Layout

In APX, all runtime data exchange—including interface definitions, signal values,
and port connection states—is mapped into distinct virtual files synchronized via
the [RemoteFile Protocol](remotefile.md).

From the perspective of the network protocol, there are no special "message types"
for signal transfer or connection state updates. Instead, communicating peers announce,
open, and exchange delta writes on named virtual files mapped within a shared virtual
address space.

```{note}
For complete binary packet headers, control command opcodes, and wire framing, see
the [RemoteFile v1.0 Specification](../specifications/protocols/remotefile.md). For how
sessions are negotiated, see [The APX Session](session.md).
```

## Naming and Perspective

APX virtual filenames consist of the node's name followed by a standardized suffix.
Crucially, all file suffixes are named from the perspective of the **Node**:

- **`.apx`**: The text-based APX IDL definition describing the node's interface.
- **`.out`**: Signal values produced by the node (flowing **out** of the node).
- **`.in`**: Signal values consumed by the node (flowing **into** the node).
- **`.cout`**: Connection count feedback for provide ports (flowing into the node to report consumer demand for what flows **out**).
- **`.cin`**: Connection count feedback for require ports (flowing into the node to report provider availability for what flows **in**).

## File Roles and Ownership

Every file has a single **authoritative owner** (the writer) and a **mirror subscriber**
(the reader). RemoteFile ensures that changes made by the authoritative owner are
streamed to the subscriber's mirror.

| File | File Type | Authoritative Owner (Writer) | Subscriber (Reader) | Wire Encoding | Primary Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `<Node>.apx` | Definition (`1`) | Node (Client) | APX Server | UTF-8 / ASCII text | Interface definition (types, ports) |
| `<Node>.out` | Provide data (`2`) | Node (Client) | APX Server | Packed binary | Serialized provide port signal values |
| `<Node>.in` | Require data (`3`) | APX Server | Node (Client) | Packed binary | Serialized require port signal values |
| `<Node>.cout` | Provide port count (`4`) | APX Server | Node (Client) | Array of `uint16_t` LE | Active consumer count per provide port |
| `<Node>.cin` | Require port count (`5`) | APX Server | Node (Client) | Array of `uint16_t` LE | Active provider status per require port |

```{tip}
Notice that the APX server owns and writes both `<Node>.cout` and `<Node>.cin`. Even
though `.cout` tracks provide ports (which are produced by the client), the count of
connected consumers is determined and maintained by the server's routing engine.
```

## Virtual Memory Map & Addressing

RemoteFile allocates virtual files within a 1GB (30-bit) address space. To minimize
framing overhead, APX partitions this address space into functional regions:

```text
+------------------------------------+ 0x3FFFFFFF (1GB)
| Control Area (1 KB)                | 0x3FFFFC00
+------------------------------------+
| User / Extension Area              | 0x0C000000
+------------------------------------+
| Port Count Area (.cout, .cin)      | 0x08000000 (128 MB)
+------------------------------------+
| Definition Area (.apx)             | 0x04000000 (64 MB)
+------------------------------------+
| Port Data Area (.out, .in)         | 0x00000000
|   (Low 16 KB: 2-byte RMFP headers) |
+------------------------------------+
```

### High-Frequency Data in Low Memory

The lowest 16 KB (`0x0000`–`0x3FFF`) uses compact 2-byte RemoteFile address headers.
Placing `<Node>.out` and `<Node>.in` in this low-address range optimizes bandwidth for
frequently updated signal traffic.

### Definition and Count Areas

- **Definition Area (`0x04000000`)**: Holds `<Node>.apx`. Transferred once during session
  establishment; utilizes standard 4-byte address headers.
- **Port Count Area (`0x08000000`)**: Holds `<Node>.cout` and `<Node>.cin`. Aligned to
  1 KB boundaries (`0x400`).

---

## Signal Data Buffers (`.out` and `.in`)

The `.out` and `.in` files are packed binary arrays containing the serialized values of
all ports in definition order.

### Port Ordering and Offset Calculation

Within each file, ports appear in strictly sequential order corresponding to their
port IDs ($0, 1, \dots, N-1$):

- For provide ports, port ID $i$ corresponds to the $i$-th provide port declared in the APX IDL.
- For require ports, port ID $i$ corresponds to the $i$-th require port declared in the APX IDL.

If port $k$ has an encoded size of $s_k$ bytes (determined by its APX type definition),
the byte offset $o_i$ of port $i$ is the cumulative sum of the sizes of all preceding ports:

$$
o_i = \sum_{k=0}^{i-1} s_k
$$

The total size $S$ of the buffer is:

$$
S = \sum_{k=0}^{N-1} s_k
$$

### Binary Serialization

Port values are serialized according to the **APX VM v2.1** specification:

- Primitive integer and floating-point types use standard little-endian byte ordering.
- Record and struct members are packed contiguously without compiler padding bytes.
- Fixed-size arrays and strings occupy their exact defined byte lengths.

### Delta Writes

When a client updates an individual provide port $i$:
1. The serialized bytes for port $i$ are written to local buffer offset $o_i$.
2. RemoteFile transmits a write packet covering only $[o_i, o_i + s_i)$.
3. The APX server receives the delta, identifies port $i$ via its byte-to-port map, and
   fans out the updated bytes to all connected require ports in peer `.in` files.

---

## Port Connection Count Files (`.cout` and `.cin`)

The `.cout` and `.cin` files provide real-time connection state feedback directly into
node memory.

### Purpose and Motivation

In distributed and embedded systems, knowing whether a peer is connected enables two
key architectural capabilities:

1. **Demand-Driven Computation (via `.cout`)**:
   Sensors, cameras, or intensive calculation routines often consume significant CPU cycles
   or bus bandwidth. If no consumer is currently subscribed to a provide port (count = `0`),
   the providing node can throttle or completely suspend sampling and computation. As soon
   as a subscriber attaches (count transitions from $0 	o 1$), production resumes.

2. **Connection Health and Availability (via `.cin`)**:
   A consumer node can check its `.cin` file to determine whether a valid provider is
   currently feeding a required input signal. If the count is `0`, the node knows the signal
   is unmapped or offline, allowing it to substitute fallback defaults or trigger diagnostic
   faults.

### Binary Layout and Sizing

Both `.cout` and `.cin` are laid out as contiguous arrays of **16-bit unsigned integers**
(`uint16_t`, 2 bytes each, little-endian byte order):

```text
Provide Port Counts (.cout):
+----------------+----------------+----------------+-----+--------------------+
|  Port 0 Count  |  Port 1 Count  |  Port 2 Count  | ... | Port (N_P-1) Count |
|    (2 bytes)   |    (2 bytes)   |    (2 bytes)   |     |      (2 bytes)     |
+----------------+----------------+----------------+-----+--------------------+
Offset: 0        2                4                      (N_P - 1) * 2
```

- **Provide Port Count (`.cout`)**:
  - Contains $N_P$ elements, where $N_P$ is the total number of provide ports in the node.
  - Byte offset for provide port $i$:
    $$o_i = i 	imes 2$$
  - Total file size:
    $$S_{	ext{cout}} = N_P 	imes 2 	ext{ bytes}$$
  - **Count Values**:
    - `0`: No consumers connected.
    - `1`: Exactly one consumer connected.
    - `>1`: Multiple consumers connected (fan-out).

- **Require Port Count (`.cin`)**:
  - Contains $N_R$ elements, where $N_R$ is the total number of require ports in the node.
  - Byte offset for require port $i$:
    $$o_i = i 	imes 2$$
  - Total file size:
    $$S_{	ext{cin}} = N_R 	imes 2 	ext{ bytes}$$
  - **Count Values**:
    - `0`: No provider connected.
    - `1`: Connected to an active provider.

### Incremental Synchronization

The server updates `.cout` and `.cin` whenever the routing topology changes:

1. When a client attaches, detaches, or connects to a port, the server recalculates the
   affected connector lists.
2. If the connection count for port $i$ changes, the server writes the new 16-bit integer
   into the client's `.cout` or `.cin` file at offset $i 	imes 2$.
3. RemoteFile transmits the 2-byte delta write to the client node.
4. The client's runtime updates its local mirror and invokes optional connection change
   event callbacks registered by the application.

---

## Complete Node Lifecycle

The coordination of all five virtual files progresses through the following sequence:

```{mermaid}
sequenceDiagram
    autonumber
    participant App as Client Application
    participant Client as Client Runtime
    participant Server as APX Server

    Note over Client,Server: RemoteFile Greeting Accepted
    Client->>Server: Announce <Node>.apx & <Node>.out
    Server->>Client: Open <Node>.apx & <Node>.out
    Client->>Server: Write <Node>.apx (full IDL definition)
    Client->>Server: Write <Node>.out (initial provide snapshot)

    Note over Server: Server parses IDL & builds port maps
    Server->>Client: Announce <Node>.in & <Node>.cout
    Client->>Server: Open <Node>.in & <Node>.cout

    Note over Server: Server routes matching signals
    Server->>Client: Write <Node>.in (initial require snapshot)
    Server->>Client: Write <Node>.cout (initial subscriber counts)

    Note over App,Server: Normal Operation
    App->>Client: Provide signal updated
    Client->>Server: Delta write <Node>.out (offset o_i, len s_i)
    Server->>Client: Peer connects -> Delta write <Node>.cout (offset i*2, len 2)
```

## Summary Checklist

| Property | `.apx` | `.out` | `.in` | `.cout` | `.cin` |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Creator** | Client | Client | Server | Server | Server |
| **Writer** | Client | Client | Server | Server | Server |
| **Reader** | Server | Server | Client | Client | Client |
| **Element Type** | Text | Varied | Varied | `uint16_t` | `uint16_t` |
| **Element Size** | 1 byte | $s_i$ bytes | $r_i$ bytes | 2 bytes | 2 bytes |
| **Endianness** | ASCII/UTF-8 | Little-endian | Little-endian | Little-endian | Little-endian |
| **Default Address** | `0x04000000` | `0x00000000` | `0x00000000` | `0x08000000` | `0x08000000` |
| **Trigger** | Startup | Value change | Routed write | Route change | Route change |
