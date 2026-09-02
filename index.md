# APX

## Automotive signals, everywhere

APX connects AUTOSAR software components with applications and devices outside
the AUTOSAR environment. It provides a small, language-independent way to
describe ports and exchange their values in real time.

[Get an introduction](Introduction/introduction.md){.sd-btn .sd-btn-primary}
[Read the specifications](specifications/specifications.md){.sd-btn .sd-btn-outline-primary}

::::{grid} 1 1 3 3
:gutter: 3
:class-container: landing-highlights

:::{grid-item-card} Integrate independently
Teams own their interfaces and can connect their software when it is ready,
without a central signal database or a large up-front integration step.
:::

:::{grid-item-card} Language and platform independent
APX nodes can communicate through the same server regardless of their
implementation language, operating system, or processor architecture.
:::

:::{grid-item-card} Keep the wire format small
APX definitions are concise text. Port values travel in compact binary data
that is suitable for local networks and resource-constrained links.
:::

::::

## One virtual signal bus

APX nodes publish the definitions of the ports they provide and require. An APX
server matches compatible ports and routes value updates between nodes. Each
node can use the programming language, operating system, and physical transport
that best suits its job.

:::{admonition} Architecture diagram
:class: landing-diagram-placeholder

Future illustration: AUTOSAR software, a Python tool, an embedded device, and a
desktop HMI connected as APX nodes through the APX virtual bus. The diagram will
also show a gateway bridging different physical transports.
:::

This makes the server behave like a virtual bus: nodes exchange automotive
signals without depending on each other's implementation details.

## Choose a path

::::{grid} 1 2 2 2
:gutter: 3

:::{grid-item-card} Understand APX
:link: Introduction/introduction
:link-type: doc

Learn the core model: nodes, ports, the virtual signal bus, and how APX relates
to AUTOSAR.
:::

:::{grid-item-card} Explore the design
:link: design/design
:link-type: doc

See how interface ownership, asynchronous messaging, and loose coupling shape
APX.
:::

:::{grid-item-card} Use APX
:link: guides/guides
:link-type: doc

Follow practical guides for working with APX definitions, nodes, and tools.
:::

:::{grid-item-card} Implement APX
:link: specifications/specifications
:link-type: doc

Read the normative IDL, protocol, and virtual-machine specifications.
:::

::::

## Implementations

APX implementations maintain their user and API documentation alongside their
source code:

- [c-apx](https://github.com/cogu/c-apx) provides the C client and APX server,
  including support for embedded targets.
- [cpp-apx](https://github.com/cogu/cpp-apx) provides the C++ implementation.
- [py-apx](https://github.com/cogu/py-apx) provides the Python API, development
  tools, parsers, and code generators.

```{toctree}
:hidden:
:maxdepth: 4

Introduction/introduction
specifications/specifications
guides/guides
design/design
```
