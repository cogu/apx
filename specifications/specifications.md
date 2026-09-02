# Specifications

The APX specifications define the normative formats, protocols, and execution models required to implement interoperable APX nodes, servers, routers, and tooling.

```{toctree}
:maxdepth: 1
:hidden:

idl/idl
vm/vm
protocols/protocols
```

The specification suite is divided into three distinct layers:

::::{grid} 1 1 3 3
:gutter: 3

:::{grid-item-card} APX IDL
:link: idl/idl
:link-type: doc

The text-based Interface Definition Language used to describe nodes, data types, provide/require ports, and attributes in `.apx` files.
:::

:::{grid-item-card} Virtual Machine
:link: vm/vm
:link-type: doc

The bytecode instruction set and binary serialization engine responsible for packing and unpacking port data with deterministic memory offsets.
:::

:::{grid-item-card} Protocols
:link: protocols/protocols
:link-type: doc

Low-level wire and transport protocols, including message length framing (NumHeader) and virtual memory synchronization (RemoteFile).
:::

::::

## Specification Areas

### Interface Definition Language (IDL)

APX IDL defines the syntax and grammar used to declare node interfaces. A definition file specifies provide ports, require ports, primitive and complex types, value ranges, and initial values.

- [**APX IDL Overview**](idl/idl.md): Terminology, version history, and compatibility.
- [**APX IDL v1.2**](idl/apx_idl_12.md) *(Stable)*: Baseline IDL version supported across all APX implementations.
- [**APX IDL v1.3**](idl/apx_idl_13.md) *(Draft)*: Extended IDL with 64-bit integer types, explicit character encodings (UTF-8), dynamic arrays, rational scaling (`RS`), and advanced value tables (`VT`).

### Virtual Machine & Binary Serialization

The APX Virtual Machine provides a lightweight execution model for serializing high-level data structures into packed binary byte streams and deserializing them back.

- [**APX VM Overview**](vm/vm.md): VM architecture and version index.
- [**APX VM 2.0**](vm/vm2_0.md): Baseline instruction set for packed binary data serialization.
- [**APX VM 2.1 (Draft)**](vm/vm2_1.md): Streamlined program headers and support for dynamic arrays and queued ports.
- [**Data Serialization Rules**](vm/serialization_rules.md): Precise binary layouts, little-endian encoding, and deterministic slot padding (`padded_next`) for memory-mapped environments.

### Wire & Transport Protocols

APX uses lightweight, message-oriented protocols to exchange signal data and synchronize memory maps over arbitrary point-to-point transports (such as TCP sockets, UNIX domain sockets, or shared memory).

- [**Transport Protocols Overview**](protocols/protocols.md): Protocol architecture and transport integration.
- [**NumHeader**](protocols/numheader.md): Compact variable-length integer encoding for message length framing (NumHeader16 and NumHeader32).
- [**RemoteFile v1.0**](protocols/remotefile.md): Virtual memory-mapped synchronization protocol managing 1GB address spaces, control areas, and asynchronous data updates.