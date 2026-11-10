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
[RemoteFile protocol specifications](../specifications/protocols/remotefile1_0.md) ([v1.0](../specifications/protocols/remotefile1_0.md) and [v1.1](../specifications/protocols/remotefile1_1.md)).
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
   greeting is `RMFP/1.1\nMessage-Size: 32\n\n`.
3. The server validates the greeting and replies with a binary `RMF_CMD_ACCEPT_HEADER`
   in the RemoteFile control area.
4. After accepting the acknowledgement, the client enables file publication
   and normal RemoteFile command processing.

The greeting selects the RemoteFile protocol version and message framing. It
does not negotiate APX ports or transfer a node definition. Those operations
happen through ordinary RemoteFile file-management commands after the greeting
has been accepted.

## Bringing a node online

A node does not become usable through one monolithic handshake. Its definition,
provide data, require data, and companion connection-count files have separate
synchronization states, but their readiness has dependencies. The server first
needs the definition and the initial provide values before it can populate the
files it owns for that node.

```{uml} ../diagrams/session-node-bootstrap.puml
```

The client may announce `.apx` and `.out` independently, in either order. The
server must not depend on them arriving together. The lifecycle below describes
the readiness contract: a node with provide ports waits for its initial `.out`
snapshot before server-file publication. A require-only node has no `.out`
dependency.

### Definition synchronization

The client already has the definition because it builds its local node from
APX IDL before attaching the node to a connection. It publishes the definition
as `<Node>.apx`, optionally with a digest.

When the server receives the `FileInfo` command, it creates a provisional node
instance and opens the remote file. The server does not yet know the ports or
their byte layout. It first receives and validates the complete definition, parses it, and
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

The initial transfer of each file is a full snapshot:

- opening `.out` causes the client to send its initialized provide buffer;
- before publishing its files, the server resolves port connections, copies
  current provider values into the require buffer, and calculates connection
  counts;
- opening `.cout`, `.cin`, or `.in` causes the server to send the already
  populated buffer. Opening `.in` is not the event that initiates routing.

A bulk snapshot is one logical write, not necessarily one transport message.
RemoteFile may fragment a large snapshot into several messages without changing
the initialization dependency.

After that snapshot, a write may cover one port, several adjacent ports, or a
portion allowed by the underlying file API. The server uses its byte-to-port
map to determine which provide ports are affected.

### Deferred server-file publication

The server separates creating a local buffer from publishing it to the client.
Publishing a file means that the client may immediately request to open it, so
the server prepares its initial contents before making that announcement.

The initialization phases are:

1. **Definition ingestion:** Validate and parse `.apx`, compile serialization
   programs, and create port instances and local buffers.
2. **Initial provide data:** If the node has provide ports, wait for `.out` to
   be announced, open it, and receive the complete initial provide snapshot.
3. **Routing and pre-population:** Connect the node's require ports to available
   providers and its provide ports to waiting requesters. Populate its `.in`,
   `.cin`, and `.cout` buffers in memory. Updates to existing peers are handled
   through the batching mechanism described below.
4. **Server-file publication:** Announce the prepared files in this order,
   omitting files that do not exist:
   1. `<Node>.cout`
   2. `<Node>.cin`
   3. `<Node>.in`
5. **Initial delivery:** When the client opens each file, send its populated
   snapshot.

This order deliberately opens `.out` **before** announcing the server-owned
count and input files. There is no requirement to establish count mirrors before
the initial provide snapshot. The server updates the joining node's closed
buffers locally rather than sending per-port initialization deltas.

The result is one logical snapshot per opened server-owned file instead of a
snapshot followed by a large number of per-port catch-up writes. Later changes
to files that have been opened still generate normal updates.

### Client open ordering

When the server publishes companion count files, the client prepares their
mirrors and requests to open them before requesting `.in`:

1. `<Node>.cout`, if published.
2. `<Node>.cin`, if published.
3. `<Node>.in`, if published.

This lets the client receive connection-count snapshots before the input-data
snapshot. It does not trigger server-side matching: routing and initial buffer
pre-population have already occurred before these files are announced.

### FIFO ordering within a connection

In c-apx, the file-manager worker dispatches queued commands in First-In,
First-Out (FIFO) order. This preserves the announcement and open-request order
within a connection. It does not replace readiness checks or establish a
global ordering across different client connections.

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
5. RemoteFile sends those destination ranges to consumers whose files are open,
   coalescing ranges when a routing batch is active. A client updates its mirror
   and can notify the application about the affected require ports.

No APX port name is carried with the runtime value write. Names and types were
resolved during definition processing; runtime traffic needs only an address
and bytes.

## Batched routing updates to existing peers

Connecting or disconnecting a node can change many signals and connection
counts on nodes that are already online. Sending one write for every affected
port would create many small packets, each with its own address and length
headers. The server therefore treats such routing operations as batches.

For each affected node, c-apx records dirty byte ranges separately for:

- `.cin`: require-port connection counts;
- `.cout`: provide-port connection counts; and
- `.in`: require-port values.

While a batch is active, changes update the local buffers and accumulate dirty
ranges instead of immediately enqueuing individual writes. Overlapping or
adjacent ranges are merged. Nearby ranges may also be combined when sending a
small unchanged gap is cheaper than an additional write and its framing.
The current c-apx implementation allows gaps of up to six bytes; this threshold
is an implementation choice, not a wire-protocol requirement.

When the outermost batch ends, the server sends current buffer contents for
the coalesced ranges of open files in this order:

1. **`.cin`**
2. **`.cout`**
3. **`.in`**

Connection-count changes therefore precede the associated input-data changes
on that connection. This **flush order differs from publication order**:
publication is `.cout`, `.cin`, `.in`; batch flushing is `.cin`, `.cout`, `.in`.
There is no cross-connection atomic transaction.

Closed files need no delta writes: their next open receives a full snapshot of
the updated buffer. This is how the joining node avoids initialization deltas
while already-open peers receive coalesced updates.

Batching is bounded by the routing operation, not a timer-based delay applied
to every signal update. Ordinary sampled port data represents current memory
state; intermediate values overwritten within a batch need not become separate
notifications. This does not permit coalescing or dropping queued signal events
or RemoteFile `FileStream` blocks.

## Per-file state

The c-apx implementation records synchronization state separately for the
definition, provide data, and require data. A useful conceptual state machine
for any one direction is:

```{uml} ../diagrams/session-file-state.puml
```

The exact transition that marks a locally owned file synchronized is an
implementation detail, but the distinction between waiting for local readiness,
waiting for publication, waiting for an open request, and waiting for initial
data is useful when diagnosing a stalled session.

## Disconnect and reconnect

When a connection closes, the server removes that connection's nodes from its
signature map and disconnects their port connectors. Remaining nodes stay
attached to the server, but they no longer receive values from the departed
providers or send values to departed requesters.

The server batches the resulting changes on surviving nodes: it updates
connection counts and any replacement-provider or fallback values in memory,
then flushes the affected open files in `.cin`, `.cout`, `.in` order. Disconnect
handling therefore avoids a separate network write for every affected port.

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
- [RemoteFile v1.0](../specifications/protocols/remotefile1_0.md) and [RemoteFile v1.1](../specifications/protocols/remotefile1_1.md) define the wire
  protocol and control commands.
- [Components and Ports](../introduction/components.md) introduces provide and
  require ports.
- [APX IDL](../specifications/idl/idl.md) defines node interface text.
- [Serialization Rules](../specifications/vm/serialization_rules.md) explains
  how typed values become bytes in port-data files.
