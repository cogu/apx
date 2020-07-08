---
layout: default
title: Python API Reference
permalink: /implementations/python_api
parent: APX for Python
grand_parent: Implementations
has_children: false
has_toc: false
nav_order: 1
---

# Python API Reference

## Class Node

The APX node class.

### Attributes

| Name         | Type | Description                 |
|--------------|------|-----------------------------|
| name         | str  | Name of the APX node        |
| dataTypes    | list | List of DataType objects    |
| requirePorts | list | List of ProvidePort objects |
| providePorts | list | List of ProvidePort objects |

### Constructors

#### Node

```python
apx.Node([name = None])
```

Creates an empty APX node. Setting a name during construction is optional but a valid name must be set before the node is taken in use (as client or for code/text generation purposes).

**Parameters:**{: .fs-3}

- **name** (str) — Name of the APX node.

#### from_autosar_swc

```python
apx.Node.from_autosar_swc(swc, [name = None], [reverse = False])
```

Class method that generates an APX node based on the name and ports of an AUTOSAR SWC.

**Parameters:**{: .fs-3}

- **swc** (ApplicationSoftwareComponent) — SWC to analyze.
- **name** (str) — Sets a new name for the generated APX node. Default is to copy the name from the SWC.
- **reverse** (bool) — Setting this to true creates a mirror image of the SWC. All require ports become provide ports and vice versa.

#### from_text

```python
apx.Node.from_text(text)
```

Class method that generates an APX node based on a raw APX definition string.

**Parameters:**{: .fs-3}

- **text** (str) — APX definition string.

### Public Methods

#### append

```python
Node.append(port)
```

This is an overloded method that is used for creating new ports in the node object. It returns the port ID (type int) of the newly created port.
There are three different ways of creating ports in a node object:

1. Using the APX port API.
2. Using raw APX IDL port definitions.
3. Importing from AUTOSAR application SWC.

**Examples:**

Using the APX port API:

```python
import sys
import apx

node = apx.Node()
#create provide-port with name=TestSignal1 and type uint8
node.append(apx.ProvidePort('TestSignal1','C'))
#create require-port with name=TestSignal2 and type uint16
node.append(apx.RequirePort('TestSignal2','S'))
node.write(sys.stdout)
```

Output:

```text
N"None"
P"TestSignal1"C
R"TestSignal2"S
```

Using raw APX IDL port definitions:

```python

import sys
import apx

node = apx.Node()
#create provide-port with name=TestSignal1 and type uint8
node.append('P"TestSignal1"C')
#create require-port with name=TestSignal2 and type uint16
node.append('R"TestSignal2"S')
node.write(sys.stdout)
```

Output:

```text
N"None"
P"TestSignal1"C
R"TestSignal2"S
```

Importing from AUTOSAR application SWC:

```python
import sys
import apx
import autosar

#Set all path_to_* variables seen below and set them to valid paths in the file system.
#Set name_of_swc_to_import to the name of the SWC you are converting to an APX node.

ws=autosar.workspace()
ws.loadXML(path_to_datatypes_arxml, roles={'/DataType': 'DataType'})
ws.loadXML(path_to_constants_arxml, roles={'/Constant': 'Constant'})
ws.loadXML(path_to_portinterfaces_arxml, roles={'/PortInterface': 'PortInterface'})
ws.loadXML(path_to_swc_arxml, roles={'/ComponentType': 'ComponentType'})

swc = ws.find('/ComponentType/'+name_of_swc_to_import)
assert(swc is not None)
node = apx.Node(swc.name)
#add all provide-ports to node object
for autosar_port in swc.providePorts:
    portInterface = ws.find(autosar_port.portInterfaceRef)
    if (type(portInterface) is autosar.portinterface.SenderReceiverInterface) and (len(portInterface.dataElements)>0):
        node.append(autosar_port)
    #add all require-ports to node object
    for autosar_port in swc.requirePorts:
        portInterface = ws.find(autosar_port.portInterfaceRef)
        if (type(portInterface) is autosar.portinterface.SenderReceiverInterface) and (len(portInterface.dataElements)>0):
            node.append(autosar_port)
```

#### add_type

```python
Node.add_type(new_type)
```

Adds a data type to the node. This method is automatically called should you use the Node.append method with *new_type* as argument.

**Parameters:**{: .fs-3}

- **new_type** (apx.DataType) — datatype to add.

#### add_require_port

```python
Node.add_require_port(require_port)
```

Adds a require type to the node. This method is automatically called should you use the Node.append method with *require_port* as argument.

**Parameters:**{: .fs-3}

- **require_port** (apx.RequirePort) — port to add.

#### add_provide_port

```python
Node.add_provide_port(provide_port)
```

Adds a require type to the node. This method is automatically called should you use the Node.append method with *provide_port* as argument.

**Parameters:**{: .fs-3}

- **provide_port** (apx.ProvidePort) — port to add.

#### save_apx

```python
Node.save_apx([output_dir='.'], [output_file = None], [normalized = False] )
```

Saves the APX node in a file using the *.apx* file extension.

**Parameters:**{: .fs-3}

- **output_dir** (str) — Path to directory where to save the file. Default is current directory.
- **output_file** (str) — Name of file. Default is to generate a name based on the node name.
- **normalized** (bool) — Set to true for normalized output.

#### save_apx_normalized

```python
Node.save_apx([output_dir='.'], [output_file = None] )
```

Same as calling Node.save_apx(output_dir, output_file, True).

**Parameters:**{: .fs-3}

- **output_dir** (str) — Path to directory where to save the file. Default is current directory.
- **output_file** (str) — Name of file. Default is to generate a name based on the node name.

#### mirror

```python
Node.mirror( [name = None] )
```

Generates a new node in a version where the direction of all require/provide ports are reversed.

**Parameters:**{: .fs-3}

- **name** (str) — Name of the new node. Default is to copy the name from the original node.

#### extend

```python
Node.extend( other_node )
```

Copies all ports from *other_node* and adds them to this node.

**Parameters:**{: .fs-3}

- **other_node** (apx.Node) — Node to copy.

## Class DataType

The data type class represents an APX data type definition. Every datatype has a name and a data signature (DSG).
Optionally it can also have type attributes such as an enumeration value table (VT).

### Constructors

#### DataType

Creates a new data type object. The constructor takes either 2 or 3 string arguments.

```python
apx.DataType(name, dataSignature, [attributes = None] ):
```

**Parameters:**{: .fs-3}

- **name** (str) — Data type name.
- **data_signature** (str) — Data signature (DSG) string.
- **attributes** (str) — Type attribute string.

Use the Node.append method to add the datatype to the node.

**Example:**

```python
import apx
import sys

node = apx.Node('ExampleNode')
node.append(apx.DataType('VehicleSpeed_T', 'S'))
node.append(apx.DataType('EngineSpeed_T', 'S'))
node.write(sys.stdout)
```

Output:

```text
N"ExampleNode"
T"VehicleSpeed_T"S
T"EngineSpeed_T"S
```

## Class RequirePort

The RequirePort class is used to represent an APX require port. It's similar to an AUTOSAR port with a few restrictions:

- SenderReceiverInterface only
- Single data element only

### Constructors

#### RequirePort

```python
apx.RequirePort(name, data_signature, [attributes = None] )
```

The constructor takes 3 strings as arguments where the last string is optional.

**Parameters:**{: .fs-3}

- **name** (str) — Port name.
- **data_signature** (str) — Data signature (DSG) string.
- **attributes** (str) — Port attribute string.

**Example:**

```python
   #Name: 'Port1'; type: 'uint8'
   port1 = apx.RequirePort('Port1', 'C')

   #Name: 'Port2'; type:'uint8'; init_value:7
   port2 = apx.RequirePort('Port2', 'C', '=7')

   #Name:'Port3'; type:'uint16'; init_value: 65535
   port3 = apx.RequirePort('Port3', 'S', '=65535')

   #Name:'Port4', type:'uint32', init-value:0xFFFFFFFF
   port4 = apx.RequirePort('Port4', 'L', '=0xFFFFFFFF')

   #Name:'Port5', type:'uint8', array-len:4, init-value:{0,0,0,0}
   port5 = apx.RequirePort('Port5', 'C[4]', '={0,0,0,0}')

   #Name: 'Port6', type:'string'; str_len: 20; init_value: ""
   port6 = apx.RequirePort('Port6', 'a[20]', '=""')

   #Name: 'Port7', type:'record', record_elements: ["UserName"a[32], 'UserID'L], init_values: ["", 0xFFFFFFFF]
   Port7: apx.RequirePort('Port7', '{"UserName"a[32]"UserID"L}', '={"",0xFFFFFFFF}')
```

## Class ProvidePort

The ProvidePort class is used to represent an APX provide port. It's the same as the RequirePort except its port direction.

### Constructors

#### ProvidePort

```python
apx.ProvidePort(name, data_signature, [attributes = None] )
```

The constructor takes 3 strings as arguments where the last string is optional.

**Parameters:**{: .fs-3}

- **name** (str) — Port name.
- **data_signature** (str) — Data signature (DSG) string.
- **attributes** (str) — Port attribute string.

## Class Parser

The parser is used to parse a file containing APX IDL (file with extension *.apx*).

**Usage:**

```python
import apx

node = apx.Parser().parse(filename)
```

### Constructor

#### Parser

```python
apx.Parser()
```

Creates a new APX parser instance.

### Public Methods

#### parse

```python
Parser.parse(filename)
```

Convenience method for parsing file from filename

**Parameters:**{: .fs-3}

- **filename** (str) — Name of file to parse.

**Returns Value:**

If parse is successful it returns the parsed APX node. It raises an exception on parse error.

#### load

```python
Parser.load(fp)
```

Parses APX IDL from an open file handle.

**Parameters:**{: .fs-3}

- **fp** (file) — A previously opened file handle.

**Returns Value:**

If parse is successful it returns the parsed APX node. It raises an exception on parse error.

#### loads

```python
Parser.loads(apx_text)
```

Parses APX IDL directly from a string

**Parameters:**{: .fs-3}

- **apx_text** (apx_text) — Raw APX IDL string.

**Returns Value:**

If parse is successful it returns the parsed APX node. It raises an exception on parse error.

### Class NodeGenerator

This is the C code generator that generates static APX nodes to be used together with c-apx.
Note that right now it only supports c-apx v0.2.

### Constructor

#### NodeGenerator

```python
apx.NodeGenerator([record_elem_suffix = None])
```

**Parameters:**{: .fs-3}

- **record_elem_suffix** (str) — name suffix to be added to all record (struct) element accesses in generated code.

### Public Methods

#### generate

```python
NodeGenerator.generate(output_dir, node, [name=None], [includes=None], [callbacks = None], 
[header_dir = None],[direct_write = None], [with_inport_synced_status_flags = True], 
[compact=False] )
```

**Parameters:**{: .fs-3}

- **output_dir** (str) — directory where to generate header and source files
- **node** (apx.Node)— APX node object
- **name** (str) — Optionally override the name of the APX node in generated code.
- **includes** (list[str]) — Additional header includes (will be part of generated code).
- **callbacks** (dict[str, str]) — Dictionary where keys are names of require ports to trigger receive callback for. Dict values are names of callback functions.
- **header_dir** (str) — Force generated headers to another directory.
- **direct_write** (list[str]) — Activates direct write mode for given provide port names.
- **with_inport_synced_status_flags** (bool) — Optional bool if inport data flags are desired in generation.
- **compact** (bool) — Can be used to make the apxDefinitionData string more compact by expanding typedefs.
