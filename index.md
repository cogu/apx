---
layout: default
title: Home
permalink: /
nav_order: 1
---

# APX

APX is a software technology that enables [AUTOSAR](https://www.autosar.org/) software to communicate with non-AUTOSAR software.
It is a collection of free and open source projects intended for automotive software developers.

## Learn More

- [Introduction to APX](/apx/introduction)

## Subprojects


[APX C Docs][90]{: .btn .btn-purple }
[APX Qt 5 Docs][91]{: .btn .btn-green }
[APX Python Docs][92]{: .btn .btn-blue }

* [c-apx][0] - APX for the C programming language. [Documentation][90]{:.label .label-blue .ml-3 .fw-700}
  * [adt][1] - Abstract data structures library.
  * [bstr][2] - Text parsing library.
  * [cutil][3] - Shared utilities library.
  * [dtl_type][4] - Dynamic type system library.
  * [dtl_json][5] - A [JSON][6] parser/writer library based on [dtl_type][4].
  * [msocket][7] - Message-based socket wrapper library.
* [qt-apx][10] - APX for [Qt 5 framework][11]. [Documentation][91]{:.label .label-blue .ml-3 .fw-700}
* [py-apx][20] - APX for [Python 3][21]. [Documentation][92]{:.label .label-blue .ml-3 .fw-700}
  * [autosar][22] - Unoffical AUTOSAR Python 3 library. [Documentation][93]{:.label .label-blue .ml-3 .fw-700}
  * [cfile][23] - A C code generator written in Python 3.
* [cs-apx][30] - APX for C#. **No longer Maintained**{:.label .label-red .ml-3}
* [xl-apx][40] - APX for Excel. **No longer Maintained**{:.label .label-red .ml-3}

[0]: https://github.com/cogu/c-apx
[1]: https://github.com/cogu/adt
[2]: https://github.com/cogu/bstr
[3]: https://github.com/cogu/cutil
[4]: https://github.com/cogu/dtl_type
[5]: https://github.com/cogu/dtl_json
[6]: https://www.json.org
[7]: https://github.com/cogu/msocket
[10]: https://github.com/cogu/qt-apx
[11]: https://www.qt.io/
[20]: https://github.com/cogu/py-apx
[21]: https://www.python.org/
[22]: https://github.com/cogu/autosar
[23]: https://github.com/cogu/cfile
[30]: https://github.com/fousk/cs-apx
[40]: https://github.com/cogu/xl-apx
[90]: /implementations/c
[91]: /implementations/qt5
[92]: /implementations/python
[93]: https://autosar.readthedocs.io

## Implementation Matrix

| Feature                 | [c-apx](https://github.com/cogu/c-apx)                                             | [qt-apx](https://github.com/cogu/qt-apx)     | [py-apx](https://github.com/cogu/py-apx)                                           |
|:------------------------|:----------------------------------------------------------------------------------:|:--------------------------------------------:|:----------------------------------------------------------------------------------:|
| Dynamic Client          | **&#x2714;**{:.text-green-200 .fs-5} v0.3                                          | **&#x2714;**{:.text-green-200 .fs-5}         | **&#x2714;**{:.text-green-200 .fs-5}                                               |
| Static Client           | **&#x2714;**{:.text-green-200 .fs-5} v0.2, **&#x1F528;**{:.fs-5} v0.3              |                                              |                                                                                    |
| Static Code Generator   |                                                                                    |                                              | **&#x2714;**{:.text-green-200 .fs-5} c-apx v0.2, **&#x1F528;**{:.fs-5}  c-apx v0.3 |
| Embedded client (APX-ES)| **&#x2714;**{:.text-green-200 .fs-5} v0.2, **&#x1F528;**{:.fs-5}  v0.3             |                                              |                                                                                    |
| Server                  | **&#x2714;**{:.text-green-200 .fs-5}                                               |                                              |                                                                                    |
| APX IDL Version support | **&#x2714;**{:.text-green-200 .fs-5} v1.2, **&#x1F528;**{:.fs-5}  v1.3             | **&#x2714;**{:.text-green-200 .fs-5} v1.2    | **&#x2714;**{:.text-green-200 .fs-5} v1.2, **&#x1F528;**{:.fs-5}  v1.3             |
| APX VM Version support  | **&#x2714;**{:.text-green-200 .fs-5} v2.0                                          | Early prototype of v1.0                      | **&#x2714;**{:.text-green-200 .fs-5} v1.0                                          |
