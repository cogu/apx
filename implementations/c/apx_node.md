---
layout: default
title: apx_node
permalink: /implementations/c/apx_node
parent: APX for C
grand_parent: Implementations
has_children: false
has_toc: false
nav_order: 2
---

# apx_node

## Synopsis

```text
apx_node   [-b --bind bind_path] [-p --bind-port port] [--no-bind]
           [-c --connect connect_path] [-r --connect-port connect_port]
           [--version] [--help]
           file
```

## Example Usage

```bash
apx_node -b /tmp/vehicle.socket -c /tmp/apx_server.socket vehicle.apx
apx_node -b /tmp/vehicle.socket -c 192.168.1.19:5000 vehicle.apx
apx_node -c localhost:5000 -b localhost:5100 vehicle.apx
```

## Description

Quickly create instances of APX nodes from a definition file and connect it to an APX server.

When the app is launched it both connects to the APX server while at the same time it creates a socket server (TCP or UNIX depending on arguments).
The socket server is used as a connection point for the application [apx_control](/implementations/c/apx_control) in order to control the values
of any provide ports found in the node.
Current values of Require-ports are printed to stdout when they are updated from the [APX server](/implementations/c/apx_server).

In case you have a node with only Require-ports or you are not interested in controlling provide-ports you can give the special option --no-bind which
prevents a socket server to be created.

## Mandatory Arguments

```text
file     path to an APX definition file (.apx)
```

## Options

```text
--no-bind       No socket server will be created.

-b --bind address_or_path
                Either TCP address or UNIX socket to bind to for receiving
                provide-port data updates.

-p --bind-port port
                Port number for server socket (not applicable when path is
                UNIX socket).

-c --connect address_or_path
                Either TCP address or path to UNIX socket to connect to for receiving
                require-port data updates.

-r --connect-port connect_port
                Port number for APX client socket (not applicable when path is
                UNIX socket).

```

If you prefer, you can skip both -p and -r options and instead use the `address:port` syntax directly in the -b and -c options.
It also understands the special word *localhost* to mean `127.0.0.1`.

Examples:

```text
-c 192.168.1.19:5000
-c localhost:5000
-b 127.0.0.1:5001
-b localhost:5001
```


## Option Default Values

### Linux Defaults

```text
--bind-path     /tmp/apx_node.socket
--connect-path  /tmp/apx_server.socket
--bind-port     5100
--connect-port  5000
```

### Windows Defaults

```text
--bind-path     127.0.0.1
--connect-path  127.0.0.1
--bind-port     5100
--connect-port  5000
```

