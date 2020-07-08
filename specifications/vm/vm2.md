---
layout: default
title: APX VM2
permalink: /specification/vm/vm2
parent: APX VM
grand_parent: Specifications
has_toc: false
nav_order: 1
---

# APX VM2

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
| C++ (Qt5) | QVariant                                     |
| Python    | Python native types (int, list, dict etc.)   |
| VBA       | Variant, Scripting.Dictionary                |

## APX Programs

Typically in an APX node, each provide and require port gets a unique pack and unpack program compiled during node creation. The programs (which are just ordinary byte-arrays) are compiled once and then get executed many times by the APX virtual machine when needed. Provide-ports usually run their pack programs while require-ports usually run their unpack programs.

## Program encoding

The APX VM executes small byte-code encoded programs that is usually a few bytes in size. APX uses a variant length program encoding where each instruction always starts with a 1 byte instruction header. Depending on the instruction header, additional data (usually array lengths) are encoded directly after instuction header. The next instruction starts immediately after the end of the previous instruction (with zero padding, zero alignment).

Before the list of instructions starts, there is a small program header which tells whether this is a pack or unpack program
(with some additional information).

## Program header

All programs starts with an 8 byte program header. Instructions for the program directly follows the program header.

| Byte                     | Description                          | Value       |
|--------------------------|--------------------------------------|-------------|
| Byte 0                   | Magic Number 0x42 (letter 'A')       | 0x42        |
| Byte 1                   | APX VM major version number          | 2           |
| Byte 2                   | APX VM minor version number          | 0           |
| Byte 3 (high nibble)     | Reserved for flags                   | 0           |
| Byte 3 (low nibble)      | 0: UNPACK PROGRAM; 1: PACK PROGRAM   | 0..1        |
| Byte 4-7 (little endian) | Maximum expected data size           | 0..(2^32)-1 |

## Instruction set

**Instruction Format:**

| bit 7       |  bits 3-6       | bits 0-2         |
|-------------|-----------------|------------------|
| 1 flag bit  | 4 variant bits  | 3 opcode bits    |

### Opcode 0 &#8212; UNPACK

Unpack data from input buffer. If flag bit is set is an indication that data is of array type and next instruction must be an *ARRAY* instruction.

| Variant ID | Data Type | Data Size (bytes) | Description                            |
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
| 13         | ZSTR      | 1                    | Null-terminated string                 |
| 14         | RESERVED  |                      |                                        |
| 15         | RESERVED  |                      |                                        |

### Opcode 1 &#8212; PACK

Pack data to output buffer. Variants and use of flag bit is identical to *UNPACK* instruction.

### Opcode 2 &#8212; ARRAY

Defines an array length. If flag bit is 0, the array length is read from the (the next byte in the program).
If the flag bit is 1, the array length is read from the input buffer (in case of *PACK*) or written to the output buffer (in case of *UNPACK*).

| Variant ID | Data Type | Data Size (bytes)    | Description                                 |
|------------|-----------|----------------------|---------------------------------------------|
| 0          | UINT8     | 1                    | Used when array length is 0-255             |
| 1          | UINT16    | 2                    | Used when array length is 256-65535         |
| 2          | UINT32    | 4                    | Used when array length is bigger than 65535 |

### Opcode 3 &#8212; DATA_CTRL

Controls how data is read/written.

#### Variant 0 &#8212; RECORD_SELECT

Selects the name of next record member. The name is a null-terminated string encoded into the program starting at the next byte 
(and ends when null-terminator is encountered).

When flag is 1 it means that this is going to be the last field of the record.

### Opcode 4 &#8212; FLOW_CTRL

Controls program flow.

#### Variant 0 &#8212; ARRAY_NEXT

Move to the next array element. This is primarily used when data type is array of records (array of structs).

### Opcode 5 &#8212; UNPACK2

Reserved for 16 future data types.

### Opcode 6 &#8212; PACK2

Reserved for 16 future data types.

### OpCode 7 &#8212; RESERVED

Reserved for future use.
