# The APX Session

This chapter describes in detail what happens when APX clients connect to the server.
Each client connection follows the same pattern or *steps*.

**Session Overview:**

1. Greeting Exchange.
2. APX Definition Presentation.
3. Definition Transfer.
4. Port Connection Creation.
5. Init Data Creation and Transfer.
6. Updating Port Values.

## Greeting Exchange

Once a low-level connection has been established between the client and the server, they can send data in both directions. After the initial greeting exchange, the protocol is bidirectional, meaning that data can flow in either direction, or more commonly, in both directions simultaneously. It is important to note that RemoteFile is not a request-response protocol (such as HTTP).

