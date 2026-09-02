# The APX Session

An **APX session** represents the active runtime connection between an APX client (or node) and an APX server over the [RemoteFile protocol](remotefile.md).

Unlike traditional request-response architectures (such as HTTP or REST), an APX session is a stateful, event-driven publish/subscribe system. It models communication as continuous, bidirectional memory synchronization over a streaming transport (such as TCP sockets, UNIX domain sockets, or shared memory).

```{note}
For low-level wire formats, bit layouts, and command opcodes, see the [RemoteFile v1.0 Specification](../specifications/protocols/remotefile.md).
```

## Session Overview

An APX session coordinates two categories of files within the 1GB virtual memory map:

1. **Definition Files (`<NodeName>.apx`)**: The text-based [APX IDL](../specifications/idl/idl.md) specification describing the node's name, provide ports, require ports, data types, and initial values.
2. **Port Data Buffers (`<NodeName>.out` and `<NodeName>.in`)**: The packed binary memory regions where live provide port values (signals published by the node) and require port values (signals subscribed to by the node) are synchronized.

### Session Lifecycle

The following sequence diagram illustrates the complete lifecycle of an APX session from connection setup to runtime signal updates:

```{mermaid}
sequenceDiagram
    autonumber
    participant Client as APX Client (Node)
    participant Server as APX Server

    Note over Client,Server: Phase 1: Connection & Greeting Handshake
    Client->>Server: Connect (TCP / UNIX Socket)
    Client->>Server: Greeting Header (RMFP/1.0\nNumHeader: 32\n\n)
    Server->>Client: Acknowledge (RMF_CMD_ACK to Control Area)

    Note over Client,Server: Phase 2: Definition File Exchange
    Client->>Server: FileInfo (Announce "<NodeName>.apx")
    Server->>Client: FileOpen (Request "<NodeName>.apx")
    Client->>Server: Write Data (Complete IDL text of "<NodeName>.apx")

    Note over Server: Phase 3: IDL Parsing & Port Routing
    Server->>Server: Parse IDL, allocate port buffers, match signals

    Note over Client,Server: Phase 4 & 5: Port Data Buffers & Init Data Sync
    Client->>Server: FileInfo (Announce "<NodeName>.out" for Provide Ports)
    Server->>Client: FileOpen (Request "<NodeName>.out")
    Client->>Server: Write Data (Initial Provide Port Values)
    Server->>Client: FileInfo (Announce "<NodeName>.in" for Require Ports)
    Client->>Server: FileOpen (Request "<NodeName>.in")
    Server->>Client: Write Data (Initial Require Port Values)

    Note over Client,Server: Phase 6: Runtime Signal Updates (Delta Writes)
    Client->>Server: Write Data (Delta write to modified offset in "<NodeName>.out")
    Server->>Server: Route updated signal to subscribers
    Server->>Client: Write Data (Delta write to "<NodeName>.in" of subscriber)
```

---

## Phase 1: Connection & Greeting Handshake

When an APX client establishes a physical connection (such as a TCP socket), it initiates the session with a text-based greeting message:

```text
RMFP/1.0\nNumHeader: 32\n\n
```

### Handshake Responsibilities

- **Version Negotiation**: The client declares its supported protocol version (`RMFP/1.0` or `RMFP/1.1`).
- **Framing Configuration**: The client declares its message length framing mechanism (`NumHeader: 16` or `NumHeader: 32`).
- **Server Acknowledgment**: The server processes the greeting and transmits an acknowledgment command (`RMF_CMD_ACK`) to the client's Control Area (`0x3FFFFC00`).

Once acknowledged, the connection transitions from text negotiation to pure binary RemoteFile messaging.

---

## Phase 2: Definition File Exchange

After the greeting handshake, the client presents the APX IDL definitions for all local nodes it hosts.

1. **File Announcement**: The client sends a `FileInfo` command to the server's Control Area describing `<NodeName>.apx` (e.g., `EngineNode.apx`):
   - **Start Address**: Allocated in the high address space (e.g., `0x00000004` with a 4-byte address header).
   - **File Size**: Byte length of the definition text.
   - **File Type**: `FixedFile` (`0`).
   - **Checksum**: Optional SHA-256 digest of the IDL text.
2. **File Open Request**: The server receives the announcement, registers a pending node instance (`APX_DATA_STATE_WAITING_FOR_FILE_DATA`), and issues a `FileOpen` command to the client.
3. **IDL Data Transmission**: The client writes the complete text of the `.apx` file to the announced memory address in a single write operation.

---

## Phase 3: Server Routing & Dynamic Port Matching

Upon receiving the complete `.apx` file, the server transitions the node definition state to `APX_DATA_STATE_SYNCHRONIZED` and invokes the IDL parser:

- **Provide Ports (`P`)**: Signals that this node produces.
- **Require Ports (`R`)**: Signals that this node consumes.
- **Data Signatures & Types**: Computes the exact byte sizes, offsets, and pack/unpack programs using the [APX Data Serialization Rules](../specifications/vm/serialization_rules.md).

### Dynamic Port Matching

The APX server acts as a dynamic signal router. It matches Provide ports to Require ports across all connected clients by comparing:

1. **Port Name**: Exact signal name matching (case-sensitive).
2. **Type Signature Compatibility**: Matching binary serialization sizes and compatible limits.

```text
+-------------------+                      +-------------------+
|  Publisher Node   |                      |  Subscriber Node  |
|  "EngineNode"     |                      |  "DashboardNode"  |
|                   |                      |                   |
| Provide Port:     |=====[APX SERVER]====>| Require Port:     |
| "VehicleSpeed"    |   Dynamic Matching   | "VehicleSpeed"    |
| (uint16_t, 0..300)|                      | (uint16_t, 0..300)|
+-------------------+                      +-------------------+
```

Because interface definitions travel with each node, components integrate dynamically at runtime without requiring a centralized, pre-compiled signal database.

---

## Phase 4: Port Data Buffer Allocation

To exchange signal values, the client and server create dedicated memory files:

| Buffer Name | Owner | Mapped In | Description |
|:---|:---|:---|:---|
| **`<NodeName>.out`** | Client | Client Local Map $\rightarrow$ Server Remote Map | Contains packed binary data for all **Provide ports** published by the node. |
| **`<NodeName>.in`** | Server | Server Local Map $\rightarrow$ Client Remote Map | Contains packed binary data for all **Require ports** subscribed to by the node. |

### Low Address Allocation

Both `<NodeName>.out` and `<NodeName>.in` are mapped at start address `0x00000000` in the **low address range** (`0`–`16,383`). This ensures that all live signal updates use the compact 2-byte `AddressHeader`, minimizing communication overhead.

---

## Phase 5: Initial Data Synchronization (Init Data)

Before application logic begins processing signal updates, both buffers are initialized:

1. **Provide Port Initialization**:
   - The client announces `<NodeName>.out` via `FileInfo`.
   - The server responds with `FileOpen`.
   - The client writes the initial values declared in the IDL (`:= <init_value>`) into `<NodeName>.out`.
2. **Require Port Initialization**:
   - The server aggregates initial values from connected publishers (or default initializers from the IDL) and announces `<NodeName>.in` via `FileInfo`.
   - The client responds with `FileOpen`.
   - The server writes the initial require values into `<NodeName>.in`.

Once both `.out` and `.in` files are synchronized, the node enters the active operational state.

---

## Phase 6: Runtime Signal Updates (Delta Writes)

During normal operation, data exchange occurs asynchronously whenever an application updates a signal value:

1. **Local Buffer Serialization**: The client runtime encodes the updated variable into the node's local `.out` memory buffer using the [APX Virtual Machine](../specifications/vm/vm.md).
2. **Delta Write Transmission**: Rather than transmitting the entire buffer, the client sends a compact RemoteFile write command containing only the modified byte range (start offset and length).
3. **Server Fan-Out**: The server receives the write, updates its mirrored memory copy, and routes the new value to all matching subscriber nodes.
4. **Subscriber In-Buffer Update**: The server writes the updated bytes into each subscriber's `<SubscriberNode>.in` buffer.
5. **Application Notification**: The subscriber client detects the memory update and notifies application listeners via event callbacks or polling APIs.

```text
[App: Set Speed=100]
        |
        v
[Serialize to EngineNode.out (Bytes 0..1)]
        |
        v  (RemoteFile Write: Address=0, Len=2, Data=[0x64, 0x00])
[APX Server]
        |
        +---> [DashboardNode.in (Bytes 4..5)] ---> [Dashboard App Callback]
        |
        +---> [LoggerNode.in    (Bytes 0..1)] ---> [Logger App Callback]
```

---

## Phase 7: Session Teardown & Dynamic Disconnection

An APX session gracefully adapts to node lifecycle events:

- **Clean Node Detachment**: A client can unmap a node by issuing `FileRevoke` or `FileClose` commands in the Control Area. The server unroutes the associated ports and updates remaining subscribers.
- **Connection Termination**: If a TCP socket closes or times out, the server tears down the session, cleans up the client's memory map, and flags connected require ports as disconnected.
- **Dynamic Reconnection**: If the client reconnects, the entire sequence (Greeting $\rightarrow$ Definition $\rightarrow$ Buffers $\rightarrow$ Init Data) repeats cleanly without requiring a restart of the server or other running nodes.
