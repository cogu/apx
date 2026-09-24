# Internal Design

Articles in this section examine the internal protocol architecture and runtime
mechanisms of APX.

While the high-level APX model presents nodes and typed signal ports, communication
relies on a memory-mapped synchronization layer and structured session lifecycles.
These articles explain how the RemoteFile layer mirrors data and how sessions manage
node definitions and live port values.

```{toctree}
:maxdepth: 1
:hidden:

remotefile
session
files
```

## Detailed design articles

- [The RemoteFile Protocol](remotefile.md) explores memory-mapped synchronization,
  virtual addressing, and binary wire framing.
- [APX Session](session.md) explains connection lifecycles, file ownership,
  and how `.apx`, `.in`, and `.out` files coordinate between peers.
- [Node Virtual Files](files.md) defines the memory-mapped file types (`.apx`,
  `.out`, `.in`, `.cout`, `.cin`), authoritative ownership, and binary layouts.
