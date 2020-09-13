---
layout: default
title: APX VM 2.0 (draft)
permalink: /specification/vm/vm2
parent: APX VM
grand_parent: Specifications
has_toc: false
nav_order: 1
---

# APX VM 2.0 (draft)

This is the instruction set for APX Virtual Machine v2.0. It's a special kind of VM which sole purpose is used for data serialization.

The VM can execute in two different modes:

- Pack &#8212;  Serialize an in-memory data structure (variant type) into a byte-array.
- Unpack &#8212; Deserialize a byte-array back into an in-memory data structure.

The data structure is assumed to be compatible with how most scripting language already represent variables in-memory.

- Scalar (int, string, boolean)
- Array (each value can be scalar, array, or record).
- Record/Struct (each value can be a scalar, array or record).

In many programming languages, this way of storing data is called *variant* or *variant type*. Its representation is compatible with JSON.

Different APX implementations use different methods of data representation.

Examples:

| Language  | Data Representation                          |
|-----------|----------------------------------------------|
| C         | [dtl_type](https://github.com/cogu/dtl_type) |
| C++       | dtl (for C++)                                |
| Python    | Python native types (int, list, dict etc.)   |
| VBA       | Variant, Scripting.Dictionary                |

## APX Programs

An APX program is a simple byte array containing serialized (binary) instructions how to pack or unpack a data element in a port. The programs are compiled once and then  executed many times by the APX Virtual Machine (APX VM) when needed.

## Program encoding

APX uses a variant length program encoding where each instruction always starts with a 1 byte instruction header. Depending on the instruction header, additional data (usually array lengths) are encoded directly after instuction header. The next instruction starts immediately after the end of the previous instruction (with zero padding, zero alignment).

Before the list of instructions starts, there is a small program header which tells whether this is a pack or unpack program
(with some additional information).

## Program header

All programs starts with an 10 byte program header. Instructions for the program directly follows the program header.

| Byte                     | Description                          | Value       |
|--------------------------|--------------------------------------|-------------|
| Byte 0                   | Magic Number 0 (letter 'A')          | 0x41        |
| Byte 1                   | Magic Number 1 (letter 'P')          | 0x50        |
| Byte 2                   | Magic Number 2 (letter 'X')          | 0x58        |
| Byte 3                   | APX VM major version number          | 2           |
| Byte 4                   | APX VM minor version number          | 0           |
| Byte 5 (high nibble)     | Program Flags                        | 0..15       |
| Byte 5 (low nibble)      | Program Type (PACK or UNPACK)        | 0..1        |
| Byte 6-9 (little endian) | Maximum expected data size           | 0..(2^32)-1 |

### Program Flags

| Flag    | Name           | Description                                                |
|---------|----------------|------------------------------------------------------------|
| 0x10    | DYNAMIC_DATA   | Active if there are dynamic arrays anywhere in the program |
| 0x20    | QUEUED_DATA    | Active if this is a queued port                            |
| 0x40    | RESERVED       |                                                            |
| 0x80    | RESERVED       |                                                            |

## Instruction set

Each instruction starts with a one-byte header which is also the length of most instructions.
Some instructions have additional data after the header.
There are currently 6 kinds of instructions (called *opcodes*). Each opcode comes with up to 16 different variants.
Finally, there is a context-dependant flag bit which can be set.
In total, this gives us up to 6&ast;16&ast;2 or 192 different instruction choices.

**Instruction Header Format:**

| bit 7       |  bits 3-6       | bits 0-2         |
|-------------|-----------------|------------------|
| 1 flag bit  | 4 variant bits  | 3 opcode bits    |

### Opcode 0 &#8212; UNPACK

Unpack data from input buffer. If flag bit is set is an indication that data is of array type and next instruction must be an *ARRAY* instruction.

| Variant ID | Data Type | Data Size (bytes) | Description                               |
|------------|-----------|----------------------|----------------------------------------|
| 0          | UINT8     | 1                    | 8-bit unsigned integer                 |
| 1          | UINT16    | 2                    | 16-bit unsigned integer                |
| 2          | UINT32    | 4                    | 32-bit unsigned integer                |
| 3          | UINT64    | 8                    | 64-bit unsigned integer                |
| 4          | SINT8     | 1                    | 8-bit signed integer                   |
| 5          | SINT16    | 2                    | 16-bit signed integer                  |
| 6          | SINT32    | 4                    | 32-bit signed integer                  |
| 7          | SINT64    | 8                    | 64-bit signed integer                  |
| 8          | ARRAY     | N/A                  | Array value (usually array of records) |
| 9          | RECORD    | N/A                  | Record value                           |
| 10         | BOOL      | 1                    | Boolean value                          |
| 11         | BYTES     | 1                    | A Bytes object (blob)                  |
| 12         | STR       | 1                    | String                                 |
| 13         | RESERVED  | 1                    | Null-terminated string                 |
| 14         | RESERVED  |                      |                                        |
| 15         | RESERVED  |                      |                                        |

### Opcode 1 &#8212; PACK

Pack data to output buffer. Variants and use of flag bit is identical to *UNPACK* instruction.

### Opcode 2 &#8212; DATA_SIZE

Used to describe a data size (array or element). Array sizes are used to describe length of arrays while
elements sizes are used only together with queued ports.
This instruction is used to encode an actual integer into the program. The type and size of the integer is
described by this instruction header (see variant). This information is used by the VM to decode the integer which is stored as the next
byte (or bytes) directly following this header.

**ARRAY_SIZE:**
If flag bit is 0 the array is of fixed length.
If the flag bit is 1, this indicates a dynamic array. In that case the current array length is read from the data buffer while
(at the same time) the maximum array length is read from next program byte (or bytes).

**ELEMENT_SIZE:**
Flag is not yet in use.

| Variant ID | Data Type         | Integer Size (bytes) | Description                                       |
|------------|-------------------|----------------------|---------------------------------------------------|
| 0          | ARRAY_SIZE_U8     | 1                    | Used when array length is 0-255                   |
| 1          | ARRAY_SIZE_U16    | 2                    | Used when array length is 256-65535               |
| 2          | ARRAY_SIZE_U32    | 4                    | Used when array length is bigger than 65535       |
| 3          | ELEMENT_SIZE_U8   | 1                    | Used when element size is 0-255 bytes             |
| 4          | ELEMENT_SIZE_U16  | 2                    | Used when element size is 256-65535 bytes         |
| 5          | ELEMENT_SIZE_U32  | 4                    | Used when element size is bigger than 65535 bytes |

### Opcode 3 &#8212; DATA_CTRL

Controls how data is read/written.

| Variant ID | Data Type        | Bytes after header |
|------------|------------------|--------------------|
| 0          | RECORD_SELECT    | Variable           |
| 1          | LIMIT_CHECK_U8   | 2                  |
| 2          | LIMIT_CHECK_U16  | 4                  |
| 3          | LIMIT_CHECK_U32  | 8                  |
| 4          | LIMIT_CHECK_U64  | 16                 |
| 5          | LIMIT_CHECK_S8   | 2                  |
| 6          | LIMIT_CHECK_S16  | 4                  |
| 7          | LIMIT_CHECK_S32  | 8                  |
| 8          | LIMIT_CHECK_S64  | 16                 |

#### Variant 0 &#8212; RECORD_SELECT

Selects the name of next record member. The name is a null-terminated string encoded into the program starting at the next byte
(and ends when null-terminator is encountered).

When flag is 1 it means that this is going to be the last field of the record.

#### Variants 1-8 &#8212; LIMIT_CHECK

A limit check encodes two integers directly after the instruction header. The first integer is the lower limit while the second
integer is the upper limit. The instruction variant determines both signedness and size of the integers (same encoding applies to both).

When flag is 1 it means that the data where the limit check applies is an array and the limit check shall be applied to all elements.

In pack-programs the limit check is encoded just before the actual pack instruction (to prevend illegal data to be serialized) while
in unpack-programs the limit check is encoded after the unpack instruction (data needs to be unpacked before it can be checked).

### Opcode 4 &#8212; FLOW_CTRL

Controls program flow.

| Variant ID | Data Type        |
|------------|------------------|
| 0          | ARRAY_NEXT       |

#### Variant 0 &#8212; ARRAY_NEXT

Move to the next array element. This is primarily used when data type is array of records (array of structs).

### Opcode 5 &#8212; UNPACK2

Reserved for 16 future data types.

### Opcode 6 &#8212; PACK2

Reserved for 16 future data types.

### OpCode 7 &#8212; RESERVED

Reserved for future use.
