# APX

APX is a software technology that enables [AUTOSAR](https://www.autosar.org/) software to communicate with non-AUTOSAR software.
It is a collection of free and open source projects intended for automotive software developers.

```{toctree}
:maxdepth: 4
:caption: Table of Contents

Introduction/introduction
specifications/specifications
guides/guides
implementations/implementations
internals/internals
```

## Learn More

- [Introduction to APX](Introduction/introduction.md)

## Subprojects

* [c-apx](https://github.com/cogu/c-apx) — APX for the C programming language. [Documentation](implementations/c/c.md)
  * [adt](https://github.com/cogu/adt) — Abstract data structures library.
  * [bstr](https://github.com/cogu/bstr) — Text parsing library.
  * [cutil](https://github.com/cogu/cutil) — Shared utilities library.
  * [dtl_type](https://github.com/cogu/dtl_type) — Dynamic type system library.
  * [dtl_json](https://github.com/cogu/dtl_json) — A [JSON](https://www.json.org) parser/writer library based on [dtl_type](https://github.com/cogu/dtl_type).
  * [msocket](https://github.com/cogu/msocket) — Message-based socket wrapper library.
* [cpp-apx](https://github.com/cogu/cpp-apx) — APX for C++. [Documentation](implementations/cpp.md)
* [py-apx](https://github.com/cogu/py-apx) — APX for [Python 3](https://www.python.org/). [Documentation](implementations/python/python.md)
  * [autosar](https://github.com/cogu/autosar) — Unofficial AUTOSAR Python 3 library. [Documentation](https://autosar.readthedocs.io)
  * [cfile](https://github.com/cogu/cfile) — A C code generator written in Python 3.
* [qt-apx](https://github.com/cogu/qt-apx) — APX for [Qt 5](https://www.qt.io/). *(No longer Maintained)*
* [cs-apx](https://github.com/fousk/cs-apx) — APX for C#. *(No longer Maintained)*
* [xl-apx](https://github.com/cogu/xl-apx) — APX for Excel. *(No longer Maintained)*
