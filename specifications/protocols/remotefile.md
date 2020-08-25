---
layout: default
title: RemoteFile
permalink: /specification/protocol/remotefile
parent: Protocols
grand_parent: Specifications
nav_order: 2
---

# RemoteFile v1.0

RemoteFile is a message-based data protocol used by two sides in a point-to-point communication link (e.g. in a socket connection). It’s primary use case is to act as the application layer of an active APX session.

After connection setup, the protocol is fully bidirectional (This is not a traditional request-response protocol) which means that data can be written at any time by both sides.

Each side of the connection maintains a 1GB block of virtual memory. This is called the local address space. Each byte in this memory can be addressed as 0-1073741823 and is of unsigned type (value 0-255).

In addition to the local 1GB address space, each side also maintains another 1GB block of virtual memory. This is called the *remote memory*.
The last 1KB (1024 bytes) of this address space is reserved and is called the *control area*.

![Empty Memory Map](/apx/images/RemoteFile_Empty.png)

The basic principle behind RemoteFile is about continous data synchronization (or data mirroring). When a byte is updated in local memory at end-point A, the change is reflected into the remote memory at end-point B (transmitted as a write operation from A to B). Likewise, any change in B's local memory is reflected to A's remote memory (transmitted as write operation from B to A).

Each side of the connection can only perform a single operation on the opened socket (or other point-to-point communication link).

| Operation | First Operand           | Second Operand | Third Operand       |
|:----------|:------------------------|:---------------|:--------------------|
| Write     | Start Address (integer) | Size (integer) | Buffer (byte-array) |

---
**Example:**

`Write(0x10,2,[5,6])`

Writes two bytes at start address 0x10. After operation is complete the byte at address 16 contains value `5` and the next byte contains value `6`.

---

## Files

**Rule #1:**
> A memory write to an address outside the control area is illegal, unless:
>
>  1. A file exists in that address range.
>  2. The file mapped in that range has been previousy opened by remote connection end-point.

Directly after connection is established, the remote memory is empty except for the 1KB control area. Before write operations can take place a file must be mapped into the remote memory address space.

A file in RemoteFile is simply a byte-array that is mapped to a start-address somewhere in the 1GB memory range.

Each file has:

- A (file) name
- A start-address (where it is mapped)
- A size in bytes

Creating a new file is done by sending a special command to the control area. The remote side (of the connection) processes the command and can at that point take a decision to either:

- Open the file
- Not open the file.

In case the file is opened, the remote side sends a *File Open* command back to the local side of the connection containing the start-address of the file (The start-address is the unique identifier of a file).
Local side then responds by sending the complete content of the file (done using a single write operation).
After initial file write, only the deltas (or data changes) are transmitted (updating individual byte or bytes).

## RemoteFile Messages

All communication is message-based, each message has two components:

1. A message header, containing the length of the message.
2. A message body, containing the message data (also known as message payload).

Since RemoteFile is designed to be used on any communication link it does not officially define a message header since there usually exists protocols for this already.

In case you are communicating over a socket (or other stream-based communication) you can use [NumHeader](/apx/specification/protocol/numheader) as the message header protocol.
If you plan to use RemoteFile on TCP then NumHeader32 is the recommended choice.

## Data Write Message

The only allowed operation is writing data into remote memory.

Each write message contains two parts:

1. Address Header (integer)
2. Data Buffer (byte-array)

The length of the data buffer is determined by subtracting the length of the address header from the total message length (extracted from the message header).

When combined with the NumHeader protocol there are four different scenarios that can occur.

| Scenario     | NumHeader Format | Address Format | When to Use                                          |
|:-------------|:-----------------|:---------------|:-----------------------------------------------------|
| Short & Low  | Short            | Low            | Writing 0-127 bytes to address 0-16383               |
| Long & Low   | Long             | Low            | Writing 128 bytes or more to address 0-16383         |
| Short & High | Short            | High           | Writing 0-127 bytes to address 16384 or higher       |
| Long & High  | Long             | High           | Writing 128 bytes or more to address 16384 or higher |

## The Address Header

The address header can have two forms:

1. Low — Uses 2 bytes
2. High — USes 4 bytes

**AddressHeader - Low address form (0-16383)**:

<table>
  <thead>
    <tr>
      <th colspan="3">Byte 0</th>
      <th colspan="1">Byte 1</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>BIT 7</td>
      <td>BIT 6</td>
      <td>BITS 5-0</td>
      <td>BITS 7-0</td>
    </tr>
    <tr>
      <td>HIGH_BIT</td>
      <td>MORE_BIT</td>
      <td colspan="2">ADDRESS</td>
    </tr>
    <tr>
      <td>0</td>
      <td>0-1</td>
      <td colspan="2">0-16383</td>
    </tr>
  </tbody>
</table>

**AddressHeader - High address form (0-0x3FFFFFFF)**:

<table>
  <thead>
    <tr>
      <th colspan="3">Byte 0</th>
      <th>Byte 1</th>
      <th>Byte 2</th>
      <th>Byte 3</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>BIT 7</td>
      <td>BIT 6</td>
      <td>BITS 5-0</td>
      <td>BITS 7-0</td>
      <td>BITS 7-0</td>
      <td>BITS 7-0</td>
    </tr>
    <tr>
      <td>HIGH_BIT</td>
      <td>MORE_BIT</td>
      <td colspan="4">ADDRESS</td>
    </tr>
    <tr>
      <td>1</td>
      <td>0-1</td>
      <td colspan="2">16384-1073741823</td>
    </tr>
  </tbody>
</table>

## AddressHeader Flags

**HIGH_BIT**

When set to 0, the AddressHeader occupies 2 bytes and uses a 14-bit address range (0-16383).

When set to 1, the AddressHeader occupies 4 bytes and uses a 30-bit address range (16384-1073741823).

In both cases the address value is encoded as big endian.

---
**NOTE**

Files whose data change frequently should be mapped to the first 16KB range.
Files that change rarely (or not at all) can be mapped anywhere else.

---

**MORE_BIT**

This is used for message fragmentation. The bit is set to 1 as long as there is more data to send (from the same write operation).
The very last packet in the write operation should have its more bit set to zero to mark end of operation.

Upper application layers should not be notified until an entire write operation has been received (MORE_BIT=0).

## RemoteFile Header Examples

### Short Length & Low Address

| Byte | Protocol       | Meaning              |
|:-----|:---------------|:---------------------|
| 0    | NumHeader16/32 | Message Header       |
| 1    | RemoteFile     | Address Header (MSB) |
| 2    | RemoteFile     | Address Header (LSB) |

### Long Length & Low Address

**NumHeader16**

| Byte | Protocol       | Meaning              |
|:-----|:---------------|:---------------------|
| 0    | NumHeader16    | Message Header (MSB) |
| 1    | NumHeader16    | Message Header (LSB) |
| 2    | RemoteFile     | Address Header (MSB) |
| 3    | RemoteFile     | Address Header (LSB) |

**NumHeader32**

| Byte | Protocol       | Meaning              |
|:-----|:---------------|:---------------------|
| 0    | NumHeader32    | Message Header (MSB) |
| 1    | NumHeader32    | Message Header       |
| 2    | NumHeader32    | Message Header       |
| 3    | NumHeader32    | Message Header (LSB) |
| 4    | RemoteFile     | Address Header (MSB) |
| 5    | RemoteFile     | Address Header (LSB) |

### Short Length & High Address

| Byte | Protocol       | Meaning              |
|:-----|:---------------|:---------------------|
| 0    | NumHeader16/32 | Message Header       |
| 1    | RemoteFile     | Address Header (MSB) |
| 2    | RemoteFile     | Address Header       |
| 3    | RemoteFile     | Address Header       |
| 4    | RemoteFile     | Address Header (LSB) |

### Long Length & High Address

**NumHeader16**

| Byte | Protocol       | Meaning              |
|:-----|:---------------|:---------------------|
| 0    | NumHeader16    | Message Header (MSB) |
| 1    | NumHeader16    | Message Header (LSB) |
| 2    | RemoteFile     | Address Header (MSB) |
| 3    | RemoteFile     | Address Header       |
| 4    | RemoteFile     | Address Header       |
| 5    | RemoteFile     | Address Header (LSB) |


**NumHeader32**

| Byte | Protocol       | Meaning              |
|:-----|:---------------|:---------------------|
| 0    | NumHeader32    | Message Header (MSB) |
| 1    | NumHeader32    | Message Header       |
| 2    | NumHeader32    | Message Header       |
| 3    | NumHeader32    | Message Header (LSB) |
| 4    | RemoteFile     | Address Header (MSB) |
| 5    | RemoteFile     | Address Header       |
| 6    | RemoteFile     | Address Header       |
| 7    | RemoteFile     | Address Header (LSB) |