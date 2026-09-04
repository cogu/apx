# Documentation TODO

## Documentation scope

This repository is the language-independent documentation hub for APX. It owns
the introduction, terminology, specifications, general design principles, and
guides that explain APX concepts without teaching a particular programming
API.

Implementation-specific installation, API references, examples, and detailed
guides belong to the implementation repositories so they can evolve with each
implementation and release:

- [c-apx](https://github.com/cogu/c-apx) for C;
- [cpp-apx](https://github.com/cogu/cpp-apx) for C++; and
- [py-apx](https://github.com/cogu/py-apx) for Python.

This site should remain the common entry point and link readers to those
projects. The Getting Started guide may use c-apx as the reference
implementation, but should keep implementation-specific detail to a minimum.

## Language-independent guides

- [ ] **Write Your First APX Node**
  - Take inspiration from `py-apx/doc/node.rst`, but teach a hand-written APX
    IDL 1.3 definition rather than the Python API.
  - Introduce the anatomy of a node: its name, named data types, provide ports,
    and require ports.
  - Explain that a data signature describes the type and structure of a port's
    value.
  - Start with the primitive integer signatures and explain lowercase signed
    types, uppercase unsigned types, and explicit value limits such as
    `S(0,8000)`.
  - Add a short example of a fixed-size array or string, then introduce a named
    type and a `T["TypeName"]` reference.
  - Add provide and require ports with initial values and explain how the
    server uses compatible port signatures to create routes.
  - Keep records, dynamic arrays, value tables, and queued ports for the
    dedicated data-types guide.
  - Use the c-apx command-line tools only to run and inspect the definition;
    keep the focus on APX IDL rather than the C implementation.
  - Link to the existing py-apx tutorial for readers who want to construct the
    same concepts programmatically in Python.

- [ ] **Understand APX Data Types**
  - Explain signed and unsigned integers, ranges, arrays, strings, and records.
  - Show how to specify initial values.
  - Relate APX types to their binary representation.
  - Link to the normative IDL and serialization specifications.

- [ ] **Connect Nodes Across Two Machines**
  - Explain APX server, bind, and remote-server addresses conceptually.
  - Use the c-apx command-line tools as a small reference setup.
  - Document the required network and firewall configuration for Linux and
    Windows.
  - Link to implementation documentation for client-specific configuration.

- [ ] **Understand Port Matching and Compatibility**
  - Explain how the server matches provide and require ports.
  - Show compatible and incompatible names, signatures, ranges, and array
    sizes.
  - Demonstrate how to diagnose a route that was not created.
  - Link to the normative matching rules in the specifications.

- [ ] **Diagnose Common APX Problems**
  - Troubleshoot connection and address conflicts.
  - Explain incompatible port definitions and missing routes.
  - Distinguish protocol or configuration problems from implementation errors.
  - Link to implementation-specific troubleshooting for build, installation,
    and API problems.

## Implementation documentation

- [ ] Ensure c-apx owns C installation, build, API, application, and
  implementation-specific troubleshooting guides.
- [ ] Ensure cpp-apx owns C++ installation, build, API, application, and
  implementation-specific troubleshooting guides.
- [ ] Ensure py-apx owns Python installation, API, application, test-automation,
  and code-generation guides.
- [ ] Confirm that each implementation publishes versioned documentation and
  has a stable URL suitable for links from this site.
- [ ] Add concise implementation summaries and links to each project's API,
  examples, and guides.

## Documentation integration

- [ ] Make this site the discoverable front door for all APX documentation.
- [ ] Evaluate Sphinx `intersphinx` inventories for stable links to symbols and
  sections in implementation documentation.
- [ ] Align navigation, terminology, and visual styling across the central and
  implementation sites without duplicating their source content.
- [ ] Document the ownership rule for contributors: APX concepts and standards
  belong here; implementation behavior belongs with its source repository.