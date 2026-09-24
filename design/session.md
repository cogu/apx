# The APX Session

An **APX session** is the lifetime of one active connection between an APX
client and an APX server. The session uses [RemoteFile](remotefile.md) to make
three kinds of node data available across that connection:

- the node definition (`.apx`);
- values produced by the node (`.out`); and
- values consumed by the node (`.in`).

The connection is stateful, but it is not a request-response conversation.
After setup, both peers retain mirrored byte arrays and exchange writes only
for the ranges that change. The APX server interprets those ranges as port
values and routes them between compatible nodes.

```{note}
This page explains how the pieces cooperate. The normative wire format,
command encodings, and addressing rules are defined by the
[RemoteFile protocol specification](../specifications/protocols/remotefile.md).
```

## The three files of a node

The easiest way to understand a session is to begin with ownership. A file is
published by the peer that owns its authoritative contents; the other peer
opens it and maintains a mirror.

```{uml} ../diagrams/session-file-ownership.puml
```

| File | Authoritative owner | Contents | Normal write direction |
| :--- | :--- | :--- | :--- |
| `<Node>.apx` | Client | APX IDL definition | Client to server |
| `<Node>.out` | Client | Packed provide-port values | Client to server |
| `<Node>.in` | Server | Packed require-port values | Server to client |

The suffixes are from the node's point of view: `.out` carries data out of the
node and `.in` carries data into it. They do not describe the direction of a
socket or a server API.

Nodes may also use companion connection-count files (`<Node>.cout` and `<Node>.cin`)
to monitor active peer connections per port. For a complete specification of all five
files, their binary memory layouts, and addressing, see [Node Virtual Files](files.md).

Each file occupies an address range in its owner's **local** RemoteFile map and
the peer's **remote** map. Therefore, equal numeric addresses on opposite peers
do not refer to the same storage. Frequently updated port-data files are
allocated in the low-address area when possible so that their writes can use
the compact two-byte address header. Definition files are normally placed in a
higher address range because they are transferred infrequently.

## Establishing the connection

Before files can be synchronized, the peers agree on RemoteFile framing.

1. The transport connection is established. TCP and UNIX domain sockets are
   examples; RemoteFile itself is transport-independent.
2. The client sends the text greeting as its first framed message. A typical
   greeting is `RMFP/1.0\nNumHeader: 32\n\n`.
3. The server validates the greeting and replies with a binary `RMF_CMD_ACK`
   in the RemoteFile control area.
4. After accepting the acknowledgement, the client enables file publication
   and normal RemoteFile command processing.

The greeting selects the RemoteFile protocol version and message framing. It
does not negotiate APX ports or transfer a node definition. Those operations
happen through ordinary RemoteFile file-management commands after the greeting
has been accepted.

## Bringing a node online

A node does not become usable through one monolithic handshake. Its definition,
provide data, require data, and companion connection-count files progress
independently as files are published, opened, and initialized. The definition is
the dependency that lets the server construct the other data models.

```{uml} ../diagrams/session-node-bootstrap.puml
```

This diagram intentionally shows parallel branches. Network scheduling and
file availability allow readiness to be tracked on a per-file basis rather than
a single monolithic phase. However, as explained below, the relative ordering of
file announcements and file open requests between companion connection-count files
and port-data files is strictly constrained.

### Definition synchronization

The client already has the definition because it builds its local node from
APX IDL before attaching the node to a connection. It publishes the definition
as `<Node>.apx`, optionally with a digest.

When the server receives the `FileInfo` command, it creates a provisional node
instance and opens the remote file. The server does not yet know the ports or
their byte layout. It first receives the complete definition, parses it, and
then creates:

- provide- and require-port instances;
- pack and unpack programs;
- a byte offset and encoded size for every port;
- initial provide and require data; and
- server-side connector and byte-to-port lookup tables.

In the c-apx reference implementation, parsing is triggered only when a write
starts at offset zero and covers the complete definition file. This is an
implementation readiness condition, not an additional RemoteFile command.

### Port-data synchronization

Once the definition has been parsed, each non-empty port direction gets a
fixed-size byte array. Ports appear consecutively in definition order. If
provide ports have encoded sizes $s_0, s_1, \ldots, s_{n-1}$, the offset of
provide port $i$ is

$$
o_i = \sum_{k=0}^{i-1} s_k.
$$

Require ports are laid out independently using the same rule. An offset in
`.out` therefore has no implied relationship to the same offset in `.in`.

The initial transfer is a full snapshot:

- opening `.out` causes the client to send its initialized provide buffer;
- opening `.in` causes the server to connect available providers, update the
  require buffer with their current values, and send the resulting snapshot.

After that snapshot, a write may cover one port, several adjacent ports, or a
portion allowed by the underlying file API. The server uses its byte-to-port
map to determine which provide ports are affected.

### Ordering of file announcement and opening

When nodes utilize companion connection-count files (`<Node>.cout` and `<Node>.cin`),
the relative order of file announcements and file opening requests is critical for
deterministic routing and race-free state transitions.

Opening the `<Node>.in` file causes the server to connect matching ports and compute
initial signal routing. During this step, the server calculates connection counts for
both provide and require ports and immediately emits count updates across the wire.
If the connection-count files have not been established and opened prior to this event,
these count updates could arrive before the client's mirrors are prepared, leading to
missed notifications or out-of-order state transitions.

To guarantee determinism, implementations must adhere to the following ordering rules:

#### APX Server requirements

The APX server must announce both companion connection-count files before announcing
or opening the port-data files:

1. **Announce `<Node>.cout`** (if provide-port counts are enabled).
2. **Announce `<Node>.cin`** (if require-port counts are enabled).
3. **Announce `<Node>.in`** (if require ports exist).
4. **Request to open `<Node>.out`** (if provide ports exist).

Announcing `.cout` and `.cin` first ensures the client learns about the count files
and can initiate their open requests before the server signals that require-port
data is available.

#### APX Client requirements

The APX client must request to open both companion connection-count files (if they
exist) before requesting to open the port-data files:

1. **Request to open `<Node>.cout`** (if published by the server).
2. **Request to open `<Node>.cin`** (if published by the server).
3. **Request to open `<Node>.in`** (after requesting both count files).

By requesting to open `.cout` and `.cin` first, the client guarantees that its local
count mirrors and buffers are ready to receive initial count snapshots and routing deltas
the moment the server completes port connection upon opening `.in`.

#### Deterministic FIFO ordering via worker queues

In the reference implementation (`c-apx`), deterministic event handling is enforced by
`apx_file_manager_worker_t`. The worker uses an internal ringbuffer queue that processes
events and transmits commands in strict First-In, First-Out (FIFO) sequence.

As long as the server enqueues `.cout` and `.cin` announcements before `.in`/`.out` events,
and the client enqueues `.cout` and `.cin` open requests before `.in`/`.out` requests,
the FIFO queue guarantees that all commands and events are dispatched across the wire
in this exact sequence.

## How ports are matched

The server does not route by byte offset and does not require a central signal
database. It derives a **port signature** from every parsed port and indexes
provide and require ports by that signature.

For the c-apx reference implementation, the signature contains the port name
and its resolved data signature, including relevant array and range
information. Matching therefore requires equal generated signatures. A name
match alone is insufficient.

When a compatible provider and requester meet, the server creates a connector
from the provide-port instance to the require-port instance. A provide port
can have several connectors, which gives APX its one-to-many fan-out. The
provider's current value is copied into a newly connected require port so that
the consumer does not have to wait for the next application update.

```{important}
Port initializers are fallback data, not a competing source of truth. A
require buffer begins with its declared initial values, but a connected
provider's current value replaces the corresponding bytes.
```

## A value update from producer to consumers

The following view follows data rather than protocol messages. Its purpose is
to show why offsets can change while the encoded value remains unchanged.

```{uml} ../diagrams/session-value-update.puml
```

The update follows these steps:

1. The producer serializes the new value into its local `.out` buffer.
2. RemoteFile sends the changed range after confirming that the server has
   opened the file.
3. The server updates its mirror and maps the written source bytes to one or
   more provide ports.
4. For every connector, the server writes the encoded value into that require
   port's offset in the consumer's `.in` buffer.
5. RemoteFile sends those destination ranges to the consumers. A client updates
   its mirror and can notify the application about the affected require port.

No APX port name is carried with the runtime value write. Names and types were
resolved during definition processing; runtime traffic needs only an address
and bytes.

## Per-file state

The c-apx implementation records synchronization state separately for the
definition, provide data, and require data. A useful conceptual state machine
for any one direction is:

```{uml} ../diagrams/session-file-state.puml
```

The exact transition that marks a locally owned file synchronized is an
implementation detail, but the distinction between waiting for publication,
waiting for an open request, and waiting for initial data is useful when
diagnosing a stalled session.

## Disconnect and reconnect

When a connection closes, the server removes that connection's nodes from its
signature map and disconnects their port connectors. Remaining nodes stay
attached to the server, but they no longer receive values from the departed
providers or send values to departed requesters.

RemoteFile also defines `FileClose` and `FileRevoke` commands for changing file
availability while a connection exists. Support for every teardown path can
vary by implementation; in particular, the c-apx node-level file-close
callback is not fully implemented. A transport reconnect should therefore be
understood as a new synchronization cycle: greeting acceptance, file
publication, initial snapshots, and port reconnection are established again.

## What belongs to which layer?

| Concern | RemoteFile | APX session logic |
| :--- | :---: | :---: |
| Stream framing and greeting | Yes | No |
| Virtual addresses and control area | Yes | No |
| Publish, open, close, and revoke files | Yes | No |
| Meaning of `.apx`, `.out`, `.in`, `.cout`, and `.cin` | No | Yes |
| Deterministic announcement and open ordering | No | Yes |
| Parsing node and port definitions | No | Yes |
| Port signature matching | No | Yes |
| Routing one provide value to require ports | No | Yes |

Keeping this boundary in mind makes the system easier to reason about:
RemoteFile synchronizes named byte arrays; APX gives those byte arrays a node,
port, and routing meaning.

## Related reading

- [RemoteFile design](remotefile.md) explains the virtual-memory model.
- [Node Virtual Files](files.md) defines the binary layout, addressing, and connection-count files (`.cout` and `.cin`).
- [RemoteFile v1.0](../specifications/protocols/remotefile.md) defines the wire
  protocol and control commands.
- [Components and Ports](../introduction/components.md) introduces provide and
  require ports.
- [APX IDL](../specifications/idl/idl.md) defines node interface text.
- [Serialization Rules](../specifications/vm/serialization_rules.md) explains
  how typed values become bytes in port-data files.
