---
layout: default
title: Components and Ports
permalink: /introduction/components
parent: Introduction
nav_order: 1
has_children: false
---

# Components and Ports
{: .no_toc }

## Table of contents
{: .no_toc .toc-text }

1. TOC
{:toc}

## Software Components

In the automotive industry it's common practice to use some form of *component-based development* approach.

A software component encapsulates a related set of functions and/or data. The component commmunicates with the outside world exclusively using *ports*.
The ports are a part of the component and represents its interface. In AUTOSAR, this is called the *Port Interface*.

![Software Component](/images/SoftwareComponent.png)

## Types of Ports

In general, there are two types of ports:

- Require Ports (input)
- Provide Ports (output)

The two most common types of port interfaces are:

- **SenderReceiver** Interface — Data-driven communication.
- **ClientServer** Interface — Service-based communication.

Currently, APX only supports **SenderReceiver** type communication which fits well with AUTOSAR classic integration.