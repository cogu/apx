---
layout: default
title: RemoteFile v1.0
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

## RemoteFile Greeting Header

The very first message a client sends to server is the greeting. It's similar in concept to the HTTP header.
It consists of a single message (see above) where the payload is a multi-line text string. (This is the only text message defined in the protocol.)

The first line of the message is:

`RMFP/1.0\n`

After the first line, a set of key-value attributes can be set by the client (Similar to MIME-headers)
Each line of the message ends with a single newline character (unlike TCP which uses `\r\n`).
In addition, the message must end with a single new-line character.

**Example:**

`RMFP/1.0\n\n`

The total length of the header message must not be longer than 127 bytes. This is because the short-form of both NumHeader16 and NumHeader32 are
identical. This means the the message header (message size) can be a single byte in both cases.
What NumHeader format is actually used by the client is specified in the greeting header.

### Greeting attributes

#### NumHeader Attribute

The NumHeader attribute specifies if 16-bit or 32-bit header is being used on consecutive messages from the client.

**Example:**

`RMFP/1.0\nNumHeader: 32\n\n`

## Binary Messages

After the greeting header is sent/received, the only allowed operation is writing data into remote memory using binary messages.

Each write message contains two parts (of the message payload):

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

## The Control Area

The last 1KB (1024 bytes) of the 1GB address range is a special control area. Writing data here means you are sending control commands
to the remote side (the owner of that memory area). The memory range of this area is `0x3FFFFC00 - 0x3FFFFFFF`.

This special control area is used for:

* Creating and revoking files.
* Opening and closing files.

## Control Commands

The start address is always `0x3FFFFC00` which is the first byte of the area. The format and length of each control command is found below.
Note that the length of any command must never exceed 1024 bytes.

In this version of the protocol most integers are encoded as little endian (will be more generic in a future version).
When an integer is encoded as little endian the type ends with the letters "LE".
As an example, the designation `U32LE` means unsigned 32-bit integer encoded as little endian.

### CmdType

The command type is a 32-bit unsigned integer which uniquely identifes what type of command has been encoded.

| CmdType                | Value |
|:-----------------------|:------|
| RMF_CMD_ACK            | 0     |
| RMF_CMD_NACK           | 1     |
| *Reserved*             | 2     |
| RMF_CMD_FILE_INFO      | 3     |
| RMF_CMD_REVOKE_FILE    | 4     |
| RMF_CMD_HEARTBEAT_RQST | 5     |
| RMF_CMD_HEARTBEAT_RSP  | 6     |
| RMF_CMD_PING_RQST      | 7     |
| RMF_CMD_PING_RSP       | 8     |
| *Reserved*             | 9     |
| RMF_CMD_FILE_OPEN      | 10    |
| RMF_CMD_FILE_CLOSE     | 11    |

### Acknowledge Command

The acknowledge command can be used as a response to previously received command.

| Offset | Name     | Encoding | Value        | Description  |
|:-------|:---------|:---------|:-------------|:-------------|
| 0      | CmdType  | U32LE    | RMF_CMD_ACK  | Command Type |

### Negative Acknowledge Command

The negative acknowledge command can be used as a response to previously received command.

| Offset | Name     | Encoding | Value         | Description  |
|:-------|:---------|:---------|:--------------|:-------------|
| 0      | CmdType  | U32LE    | RMF_CMD_NACK  | Command Type |

### FileInfo Command

Both sides of the communication link sends zero or more FileInfo commands (one per file) informing the other side which files it currently has available (mapped into memory). The length of the struct is 48 bytes + the length of the file name which is the last part of the struct.

Since the longest message that can be sent to the special file area is 1024 bytes, the longest possible file name is 975 bytes (1 byte reserved for the null terminator).

| Offset | Name         | Encoding | Value              | Description                           |
|:-------|:-------------|:---------|:-------------------|:--------------------------------------|
| 0      | CmdType      | U32LE    | RMF_CMD_FILE_INFO  | Command Type                          |
| 4      | StartAddress | U32LE    | 0..(2^30)-1025     | Start Address of file                 |
| 8      | FileSize     | U32LE    | 0-2^30-1024        | Maximum size of file                  |
| 12     | FileType     | U16LE    | 0-2                | Type of file, see below               |
| 14     | DigestType   | U16LE    | 0-2                | Type of checksum, see below           |
| 16     | DigestData   | U8[32]   | 0-255              | Placeholder array for checksum        |
| 48     | FileName     | String   | `[0-9a-zA-Z_]+`    | File name as a null-terminated string |

#### FileType

| Value | Meaning                     |
|:------|:----------------------------|
| 0     | FixedFile (default)         |
| 1     | DynamicFile                 |
| 2     | FileStream                  |

#### DigestType

| Value | Meaning                              |
|:------|:-------------------------------------|
| 0     | NoDigest                             |
| 1     | SHA-1 (as generated by sha1sum)      |
| 2     | SHA-256 (as generated by sha256sum)  |

**Example:**

| Offset | Name         | Value             | Serialized Data      |
|:-------|:-------------|:------------------|:---------------------|
| 0      | CmdType      | RMF_CMD_FILE_INFO | `"\x03\x00\x00\x00"` |
| 4      | StartAddress | 0x10000           | `"\x00\x00\x01\x00"` |
| 8      | FileSize     | 1000              | `"\xe8\x03\x00\x00"` |
| 12     | FileType     | FixedFile         | `"\x00\x00"`         |
| 14     | DigestType   | NoDigest          | `"\x00\x00"`         |
| 16     | DigestData   | [0, 0, ..., 0]    | `"\x00\x00..\x00"`   |
| 48     | FileName     | "File1.txt"       | `"File1.txt\0"`      |


#### Multiple FileInfo structs

It's allowed to send multiple FileInfo structs in a single control command (as long as the 1024 limit is not exceeded).
In this case, only the first struct holds the CmdType field meaning that StartAddress of the next file is found right after the null-terminator of the file name of previous file.

Note that support for multiple FileInfos is not yet implemented in [c-apx](https://github.com/cogu/c-apx) as of v0.3.0.

### FileRevoke Command

The file revoke command is the opposite of FileInfo. It unmaps the file from the memory map. If remote side had the file open it's automatically closed.

| Offset | Name          | Encoding | Value           | Description                                         |
|:-------|:--------------|:---------|:----------------|:----------------------------------------------------|
| 0      | CmdType       | U32LE    | RMF_CMD_NACK    | Command Type                                        |
| 4      | StartAddress  | U32LE    | 0..(2^30)-1025  | File Address (from previously sent FileInfo struct) |

### Heartbeat Commands

A client can check if the underlying connection (e.g. socket) is alive by sending a heartbeat request to server.
The server then replies back with a heartbeat response.

**Request:**

| Offset | Name     | Encoding | Value                   | Description  |
|:-------|:---------|:---------|:------------------------|:-------------|
| 0      | CmdType  | U32LE    | RMF_CMD_HEARTBEAT_RQST  | Command Type |


**Response:**

| Offset | Name     | Encoding | Value                  | Description  |
|:-------|:---------|:---------|:-----------------------|:-------------|
| 0      | CmdType  | U32LE    | RMF_CMD_HEARTBEAT_RSP  | Command Type |


### Ping Commands

A ping command is a more sophisticated form of heartbeat. The initator takes a timestamp which is sent in request.
The same timestamp is echoed back in the response. In addition, a specific (memory mapped) file can be picked
as the target of the ping. This can be used in a future implementation to relay pings from client to client.
Use the special file address 0xFFFFFFFF if you don't want to target a specific file.

**Request:**

| Offset | Name              | Encoding | Value             | Description            |
|:-------|:------------------|:---------|:------------------|:-----------------------|
| 0      | CmdType           | U32LE    | RMF_CMD_PING_RQST | Command Type           |
| 4      | StartAddress      | U32LE    | 0..(2^30)-1025    | File Address           |
| 8      | TimeStampSec      | U32LE    | 0..2^32-1         | Timestamp seconds      |
| 12     | TimeStampMilliSec | U32LE    | 0..2^32-1         | Timestamp milliseconds |

**Response:**

| Offset | Name              | Encoding | Value             | Description            |
|:-------|:------------------|:---------|:------------------|:-----------------------|
| 0      | CmdType           | U32LE    | RMF_CMD_PING_RSP  | Command Type           |
| 4      | StartAddress      | U32LE    | 0..(2^30)-1025    | File Address           |
| 8      | TimeStampSec      | U32LE    | 0..2^32-1         | Timestamp seconds      |
| 12     | TimeStampMilliSec | U32LE    | 0..2^32-1         | Timestamp milliseconds |

### File Open/Close Commands

After a FileInfo struct has been received you can choose to open the file by sending back a file open command.
The file to open is identified by the start address from previously received FileInfo.

**FileOpen:**

| Offset | Name          | Encoding | Value             | Description       |
|:-------|:--------------|:---------|:------------------|:------------------|
| 0      | CmdType       | U32LE    | RMF_CMD_FILE_OPEN | Command Type      |
| 4      | StartAddress  | U32LE    | 0..(2^30)-1025    | File Address      |

**FileClose:**

| Offset | Name          | Encoding | Value              | Description       |
|:-------|:--------------|:---------|:-------------------|:------------------|
| 0      | CmdType       | U32LE    | RMF_CMD_FILE_CLOSE | Command Type      |
| 4      | StartAddress  | U32LE    | 0..(2^30)-1025     | File Address      |

It's an illegal operation to open/close a file before corresponding FileInfo struct has been received.
