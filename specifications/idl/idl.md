# APX IDL

APX IDL is an Interface Definition Language (IDL) created and maintained by [Conny Gustafsson](https://github.com/cogu/).

Previously, this language was known as *APX Text*, but it has since been renamed to APX IDL.

## Terminology

**APX IDL** is the language used to describe APX node interfaces. A document
written in APX IDL is called an **APX definition file** and uses the `.apx` file
extension.

Each definition file describes one APX node. The `N` statement is the **node
declaration**; the remaining statements declare the node's types and ports.

The former name *APX Text* refers to the language, not to a separate file format.
It is retained here only for historical context.

```{toctree}
:maxdepth: 1
:hidden:

apx_idl_12
apx_idl_13
```

## Versions

- [APX IDL v1.2](apx_idl_12.md) (Stable)
- [APX IDL v1.3](apx_idl_13.md) (Draft)

## History

### APX v1.0

- Developed in early 2014 with a toolchain implemented in Node.js.
- Specification was never released in electronic form.

### APX v1.1

- Research project in 2015 with a toolchain implemented in Qt5.
- Experimental only and was eventually replaced by APX IDL v1.2.
- Specification was never released in electronic form.

### APX v1.2

- Developed in 2016-2017 with a toolchain implemented in Python 3.
- Stable version used by all implementations.
- Backward-compatible with APX IDL v1.0.

### APX v1.3

- In active development.
- Full implementations in C and Python 3.
- Backward-compatible with APX IDL v1.2 (with redefined 64-bit integers and explicit char encodings).
