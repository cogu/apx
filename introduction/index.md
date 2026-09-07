# Introduction

APX (**AUTOSAR Port eXchange**) lets AUTOSAR software components exchange
signal data with software outside AUTOSAR, such as Linux HMIs, Python test
tools, and embedded devices.

```{toctree}
:maxdepth: 1
:hidden:

nodes
components
```

## A bridge between paradigms

APX bridges two software paradigms. It retains the component-and-port model
used in automotive software while applying integration principles associated
with microservices.

This combination is the reason APX can seem unfamiliar from either direction.
To an automotive developer, APX removes much of the central configuration
normally associated with signal integration. To a general software developer,
it looks similar to publish/subscribe but uses typed component ports instead of
topics and explicit subscription calls.

From component-based automotive software, APX takes:

- components with explicit interfaces;
- provide and require ports; and
- signal-based sender-receiver communication.

From microservice design, APX takes:

- decentralized ownership rather than central organization;
- incremental integration rather than a large up-front system design;
- asynchronous communication between loosely coupled participants;
- smart endpoints connected by simple transports; and
- the expectation that connections and remote participants can fail.

APX does not turn automotive components into web services, nor does it require
a microservice platform. It applies these principles to the exchange of typed,
real-time signal data.

## Components own their interfaces

An APX node carries its own definition. The definition states which signals the
node publishes, which signals it subscribes to, and how their values are
represented.

When the node connects, it sends this definition to the server. The server
derives the routes from the definitions currently present on the network. A
separate routing configuration does not need to be changed each time a
compatible node is added.

This is APX's bottom-up approach to integration: the network is assembled from
the interfaces of its participants instead of being fully described in advance
by one central model.

## No big up-front integration design

APX does not require the complete signal network to be known before development
starts. A team can define and test one node, then connect it when compatible
publishers or subscribers become available.

The server derives the current network from the nodes that are connected. This
allows integration to happen continuously without redefining a central routing
model for every new participant.

## Loose coupling and high cohesion

A node knows its own purpose and interface, but it does not need to know which
other nodes use its data. Publishers and subscribers depend on compatible port
definitions rather than on each other's source code, programming language, or
deployment environment.

This encourages small, cohesive components. Each component can focus on one
area of behavior while APX handles the exchange of data at its boundary.

## Asynchronous message passing

Nodes do not communicate through direct function calls. They exchange port
updates as messages through the APX server. A publisher writes a new value
without calling, or even knowing about, its subscribers.

The server and gateways react to incoming messages and forward the resulting
updates. This event-driven flow keeps components independent and allows data to
cross process, device, and transport boundaries.

```{mermaid} ../diagrams/message-flow.mmd
:align: center
:caption: Asynchronous message passing and fan-out routing
```

## Smart endpoints and simple transports

APX places knowledge of node interfaces and signal data at the endpoints. The
underlying transport only needs to carry APX messages over a point-to-point
connection.

This follows the "smart endpoints and simple pipes" principle. TCP sockets,
local sockets, shared memory, or an embedded communication link can be used
without changing the node's interface. Gateways can forward messages between
different transports without understanding the application that produced the
signals.

## Design for unavailable peers

An APX connection is a session, not a permanent relationship. A node cannot
assume that its publishers or subscribers are connected, and the routes
available in one session may differ from those in another.

When a client establishes a session, it presents its node definitions and
current values. The server creates routes from the participants available at
that time. This repeatable setup allows routes to be reconstructed when clients
connect again instead of relying on connection state from an earlier session.

## Designed to cross system boundaries

The APX protocol defines the information exchanged across the network, not the
internal structure of an implementation. An APX node may be written in C, C++,
Python, or another language, and run in environments ranging from small embedded
targets to desktop operating systems.

Implementations isolate transport-specific code behind a small connection
boundary. A connection can use any point-to-point transport that carries APX
messages—such as TCP sockets, local sockets, or serial links. Gateways can forward
the same messages between transports without understanding the application that
produced the signals, allowing one virtual bus to span process, device, and network
boundaries.

Typical uses include:

- connecting an AUTOSAR ECU to an HMI running on Linux;
- exposing ECU signals to test automation written in Python;
- joining embedded devices and desktop tools in a development network; and
- integrating independently developed components during continuous testing.

## Designed for independent testing

Explicit interfaces and message-based communication make nodes practical to
test in isolation. A test program can provide the signals a node subscribes to
and observe the signals it publishes without running the complete target
system.

The same node can later join an integration network without changing its
interface. Teams can integrate on their own schedule, from occasional system
tests to continuous integration.

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

- [APX Nodes](nodes.md) An introduction to the APX node.
- [Components and Ports](components.md) explains the component model and port
  compatibility.
- [APX Specifications](../specifications/specifications.md) contains the formal
  IDL, protocol, and virtual-machine specifications.
- [User Guides](../guides/index.md) contains task-oriented documentation.
