# Getting Started

This guide builds the [c-apx reference implementation](https://github.com/cogu/c-apx),
starts an APX server, connects two example nodes, and sends a signal between
them. Keep each process running while you complete the following steps.

## Prerequisites

::::{tab-set}
:sync-group: platform

:::{tab-item} Linux
:sync: linux

Install Git, CMake, and GCC using your distribution's package manager.

:::

:::{tab-item} Windows
:sync: windows

Install Git and Visual Studio with the **Desktop development with C++**
workload. In the Visual Studio Installer, make sure the CMake tools for Windows
component is selected.

Run the commands in this guide from an **x64 Native Tools Command Prompt for
Visual Studio**.

:::

::::

## Clone and build c-apx

Clone the repository, then initialize its Git submodules before building it.

```console
git clone https://github.com/cogu/c-apx.git
cd c-apx
git submodule update --init --recursive
cmake -S . -B build
cmake --build build
```

## Start the APX server

From the `c-apx` directory, start the server with the example configuration:

::::{tab-set}
:sync-group: platform

:::{tab-item} Linux
:sync: linux

```bash
build/app/apx_server/apx_server example/config
```

:::

:::{tab-item} Windows
:sync: windows

```batch
build\app\apx_server\Debug\apx_server.exe example\config
```

:::

::::

Leave the server running.

## Connect the example nodes

Open a second terminal in the `c-apx` directory and start the listener node:

::::{tab-set}
:sync-group: platform

:::{tab-item} Linux
:sync: linux

```bash
build/app/apx_node/apx_node --no-bind example/nodes/unsigned_listener.apx
```

:::

:::{tab-item} Windows
:sync: windows

```batch
build\app\apx_node\Debug\apx_node.exe --no-bind example\nodes\unsigned_listener.apx
```

:::

::::

Open a third terminal in the `c-apx` directory and start the sender node:

::::{tab-set}
:sync-group: platform

:::{tab-item} Linux
:sync: linux

```bash
build/app/apx_node/apx_node example/nodes/unsigned_sender.apx
```

:::

:::{tab-item} Windows
:sync: windows

```batch
build\app\apx_node\Debug\apx_node.exe example\nodes\unsigned_sender.apx
```

:::

::::

## Send a value

Open a fourth terminal in the `c-apx` directory and set `VehicleSpeed` to
`100`:

::::{tab-set}
:sync-group: platform

:::{tab-item} Linux
:sync: linux

```bash
build/app/apx_control/apx_control VehicleSpeed 100
```

:::

:::{tab-item} Windows
:sync: windows

```batch
build\app\apx_control\Debug\apx_control.exe VehicleSpeed 100
```

:::

::::

The value travels from `apx_control` to `unsigned_sender`, then through the APX
server to `unsigned_listener`. The terminal running the listener prints:

```text
"VehicleSpeed": 100
```
