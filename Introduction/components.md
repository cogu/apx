# Components and Ports

## Software Components

In the automotive industry it's common practice to use some form of *component-based development* approach.

A software component encapsulates a related set of functions and/or data. The component commmunicates with the outside world exclusively using *ports*.
The ports are a part of the component and represents its interface. In AUTOSAR, this is called the *Port Interface*.

```{mermaid} ../diagrams/SoftwareComponent.mmd
```

## Types of Ports

In general, there are two types of ports:

- Require Ports (input)
- Provide Ports (output)

The two most common types of port interfaces are:

- **SenderReceiver** Interface — Data-driven communication.
- **ClientServer** Interface — Service-based communication.

Currently, APX only supports **SenderReceiver** type communication which fits well with AUTOSAR classic integration.