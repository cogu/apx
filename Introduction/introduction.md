# Introduction

```{toctree}
:maxdepth: 1
:hidden:

components
```

## What is APX?

APX (**AUTOSAR Port eXchange**) lets AUTOSAR software components exchange
signal data with software outside AUTOSAR, such as Linux HMIs, Python test
tools, and embedded devices.

An APX node declares the signals it **publishes** and the signals it
**subscribes to**. APX carries two kinds of information:

- **Port definitions** describe the names, data types, and initial values that
  form a component's interface.
- **Port values** contain the live signal data produced and consumed while the
  system is running.

The publish/subscribe relationship is implicit in the node definition. There
is no separate subscription API or topic configuration. Because the definition
travels with each participant, teams can develop and test components
independently. If two definitions are compatible, the components can
communicate without first updating a shared system configuration.

## The node is the unit of integration

An APX application exposes one or more **nodes**. Each node represents a
component that publishes and subscribes to a defined set of signals.

This model deliberately resembles an AUTOSAR software component. An APX node
can therefore represent an AUTOSAR SWC outside the ECU without copying the
SWC's internal implementation. APX calls a published signal a **provide port**
and a subscription a **require port**.

[Learn about components and ports](components.md){.sd-btn .sd-btn-outline-primary}

## The APX virtual bus

APX uses a client-server topology. Nodes connect to an APX server and send
their definitions. The server matches publishers with subscribers by signal
name and data type, then creates the corresponding routes.

:::{admonition} APX virtual bus diagram
:class: landing-diagram-placeholder

Future illustration: several APX nodes surrounding a central virtual bus. A
provided `VehicleSpeed` value from an AUTOSAR node is routed to matching require
ports in a Python test tool and a desktop HMI.
:::

After matching is complete, each published value is sent to the nodes that
subscribe to it. Although the physical topology is a star, the result behaves
like a signal bus from the application's point of view.

## Designed to cross system boundaries

The APX protocols do not depend on a programming language, operating system,
or processor architecture. Nodes can be implemented for environments ranging
from small embedded targets to desktop applications.

APX communication is message-based. A connection can therefore use any
point-to-point transport that can carry APX messages. Gateways can forward the
same messages between transports, allowing one virtual bus to span process,
device, and network boundaries.

Typical uses include:

- connecting an AUTOSAR ECU to an HMI running on Linux;
- exposing ECU signals to test automation written in Python;
- joining embedded devices and desktop tools in a development network; and
- integrating independently developed components during continuous testing.

## APX Text describes the interface

APX represents a node interface in a compact interface definition language
known as **APX Text**. Only the information needed to exchange port data is
included.

```text
APX/1.2
N"VehicleStatus"
P"VehicleSpeed"S:=0
R"AmbientTemperature"c:=0
```

The example declares a node named `VehicleStatus`. The `P` line publishes
`VehicleSpeed`; the `R` line subscribes to `AmbientTemperature`. The type codes
and value ranges give both peers enough information to agree on the binary
representation of each value.

APX Text can be generated from an AUTOSAR model, produced by a tool, or written
directly. During connection setup, the definition is transferred as text. Live
port values are then exchanged using compact binary data.

## From connection to live data

An APX session has a short setup phase followed by continuous value exchange:

1. A client connects to the APX server over a supported transport.
2. The client sends the definitions and current values for its nodes.
3. The server matches published signals with compatible subscriptions.
4. The server creates routes between the matching ports.
5. For the remainder of the session, new values flow over those routes as
  compact binary updates while the clients remain connected.

The specifications define the formats and protocols involved in this process.
Individual implementation repositories document how to build applications with
their respective APIs and tools.

## Continue reading

- [Components and Ports](components.md) explains the component model and port
  compatibility.
- [APX Specifications](../specifications/specifications.md) contains the formal
  IDL, protocol, and virtual-machine specifications.
- [User Guides](../guides/guides.md) contains task-oriented documentation.
