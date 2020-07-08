---
layout: default
title: Introduction
permalink: /introduction
nav_order: 2
has_children: true
has_toc: false
---

# Introduction
{: .no_toc }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

## What is APX?

APX (or AUTOSAR Port eXchange) is a software technology that enables [AUTOSAR](https://www.autosar.org/) software to communicate with non-AUTOSAR software.

In AUTOSAR, Software Components (SWCs) use ports to communicate with the outside world. There are two kinds of ports:

- Require-ports &#8212; used to receive data.
- Provide-ports &#8212; used to send data.

![Software Component](/apx/images/SoftwareComponent.png)

APX allows you to distribute not only the port values but also the port definitions (names, datatypes, init value etc.) very efficiently over a network or serial bus. It works best over short distances (SPI buses, shared memory, local area networks, localhost etc.).

It was originally designed for real-time streaming of HMI signals from AUTOSAR ECU to Linux system but it can have other use cases.

## The APX Signal Network

APX uses a client-server setup where you first start the APX server. APX clients then connect to the server over a communication link that both the client and server supports (TCP/IP, UNIX socket, SPI Bus, Shared Memory etc.). Sometimes gateways are used between client and server, this is fine since APX is
completley message based.

Each connecting client begins its session with sending its port definitions (text) followed by port values (binary) to the server. The server then tries to create connectors (data routes) between Require and Provide ports with matching names and data types (formally known as *port signature matching*).

Once port connectors (routing tables) have been been created, new port values now flow freely from one client to another using a fast binary data protocol.

Even though the network topology is a traditional star network (one server, many clients), the server routes the data so fast that in practice you can regard
the network as a signal bus. This is called the *APX signal network*.

![APX signal network](/apx/images/APX_Signal_Network_Small.png)

## One specification &#8212; Many Implementations

APX has been designed from the ground up to work well; from the smallest embedded devices to full-scale Linux or Windows systems.

**APX is:**

- Language Independent &#8212; Possible to implement in any programming language.
- Platform Independent &#8212; Run on x86, x64, ARM, Renesas RH850 derivates etc.
- OS Independent &#8212; Run on Linux, Windows, AUTOSAR OS or without an OS.

Any APX client that can connect to the server is part of the *APX signal network* no matter their underlying OS, programming language or method of communication.

There is already a small number of native implementations available. The primary implementation is [c-apx](https://github.com/cogu/c-apx) (APX for C).
This is the only one that contains an implementation of the server (and client). All other language ports just implements the client.

## System Requirements

APX requires a point-to-point communication link on which it can send and receive messages.

Supported technologies (so far):

- TCP/IP (Linux, Windows)
- UNIX domain sockets (Linux)
- Serial Peripheral Bus (SPI) (*source code not yet public*)
- Shared memory bus (*source code not yet public*)

The design of c-apx relies heavily on the concept of *dependency injection*. This means you can implement the low-level send/receive interface
yourself and plug it into the runtime without modifying existing code base, thus adding new connection options.

## Next
{: .no_toc }

[Components and Ports](/apx/introduction/components)
