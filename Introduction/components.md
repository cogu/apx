# Components and Ports

Component-based systems divide software into units with explicit interfaces.
Each component owns its internal behavior and communicates with the rest of the
system through ports.

## From AUTOSAR SWCs to APX nodes

In AUTOSAR, the unit of composition is the **software component**, commonly
abbreviated to **SWC**. Its ports form the boundary between the component and
the rest of the system.

The equivalent unit in APX is the **node**. An APX node describes the part of a
component interface needed for signal exchange; it does not prescribe how the
component itself is implemented.

:::{admonition} Component and port diagram
:class: landing-diagram-placeholder

Future illustration: an APX node with require ports entering on the left and
provide ports leaving on the right, followed by the equivalent AUTOSAR SWC.
:::

This separation lets the same APX interface be implemented by an AUTOSAR SWC,
an embedded C application, or a program running on a desktop operating system.

## Three vocabularies for the same data flow

APX terminology comes from AUTOSAR, where interfaces are described in terms of
components and ports. The same data flow is described differently in other
software domains:

| General software | Sender-receiver | AUTOSAR and APX |
| --- | --- | --- |
| Publisher | Sender | Provide port |
| Subscriber | Receiver | Require port |

The terms describe roles, not three different communication mechanisms. This
documentation uses *publish* and *subscribe* when explaining the overall data
flow, and *provide port* and *require port* when discussing node definitions or
the APX specifications.

APX is not a conventional topic-based message broker. A node does not call a
subscribe function at runtime. Instead, its APX Text declares provide and
require ports. The server uses those declarations to create routes between
ports with matching names and compatible types.

## Provide and require ports

Port direction is described from the node's point of view:

- A **provide port** is an output and makes the node a publisher of that
  signal.
- A **require port** is an input and makes the node a subscriber to that
  signal.

One provided value can be routed to several require ports. This allows multiple
consumers, such as an HMI, a logger, and a test tool, to observe the same signal
without the producer knowing about them.

## Port definitions

Every APX port definition contains the information required to interpret its
value. This includes:

- the port name;
- whether the port is provided or required;
- its data type and value range;
- an optional initial value.

APX supports scalar values, strings, arrays, and records. These definitions are
encoded in APX Text and determine how values are serialized into the node's
binary data area.

## Port matching

The APX server connects ports by comparing their **port signatures**. A provide
port and a require port must describe compatible data before the server can
route values between them.

Matching protects a consumer from interpreting bytes using the wrong data
type. It also keeps integration local: adding a compatible consumer does not
require a change to the producer.

## Communication model

AUTOSAR defines several kinds of port interfaces. APX currently models
data-oriented sender-receiver communication. One provide port supplies a value
to one or more matching require ports.

Client-server operation calls and other service-oriented AUTOSAR interfaces are
outside the current APX communication model.

## Next

- Return to the [Introduction](introduction.md).
- Continue with the [APX IDL specifications](../specifications/idl/idl.md).
