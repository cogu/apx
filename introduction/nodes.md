# APX Nodes

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

This model deliberately resembles an AUTOSAR Classic software component. An APX node
can therefore represent an AUTOSAR SWC outside the ECU without copying the
SWC's internal implementation. APX calls a published signal a **provide port**
and a subscription a **require port**.

[Learn about components and ports](components.md){.sd-btn .sd-btn-outline-primary}

## The APX virtual bus

APX uses a client-server topology. Nodes connect to an APX server and send
their definitions. The server matches publishers with subscribers by signal
name and data type, then creates the corresponding routes.

:::{image} ../images/apx_signal_bus_light.svg
:alt: APX signal bus
:class: only-light
:align: center
:::

:::{image} ../images/apx_signal_bus_dark.svg
:alt: APX signal bus
:class: only-dark
:align: center
:::

After matching is complete, each published value is sent to the nodes that
subscribe to it. Although the physical topology is a star, the result behaves
like a signal bus from the application's point of view.

## APX definition files describe interfaces

Each node is described by an **APX definition file** with the `.apx` file
extension. The file is written in **APX IDL**, a compact interface definition
language that includes only the information needed to exchange port data.

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

An APX definition file can be generated from an AUTOSAR model, produced by a
tool, or written directly. During connection setup, the definition file is
transferred as text. Live port values are then exchanged using compact binary
data.

## Next steps

- [Components and Ports](components.md) explains provide and require ports, port signatures, and type matching in detail.
- [Return to Introduction](index.md) for the high-level architecture and principles.
- [APX IDL Specifications](../specifications/idl/idl.md) describes the formal syntax for `.apx` definition files.

