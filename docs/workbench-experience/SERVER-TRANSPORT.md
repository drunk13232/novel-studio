# Accepted loopback transport cleanup

The production launcher and isolated HTTP fixture use `app.server_loop.new_event_loop` through the installed Uvicorn loop-factory API. On Windows, it changes only accepted TCP transports whose local endpoint is loopback. Outgoing sockets/TLS, subprocess pipes and the global event-loop policy retain their existing behavior. Other platforms use the standard loop.

The observed CPython 3.12.14 cleanup path can skip socket close/server detach if its optional shutdown raises. The adapter notifies the protocol once, attempts shutdown and close independently, and detaches only after the actual socket handle is closed. Unexpected errors, protocol exceptions and multiple failures remain visible. A failed close retains ownership for an explicit retry; it does not fake a closed transport or zero server counters.

## Evidence boundary

- Actual accepted loopback TCP and a controlled socket-shutdown failure exercise cleanup. Actual outgoing TCP and UTF-8 subprocess I/O exercise unchanged transport paths.
- Official MCP Python SDK 2.3.0 initializes a real local stdio server, discovers its tool and calls it. This is not a real Codex inference or a remote-AI test.
- The prior natural WinError 10054 episode was not deterministically reproduced by ordinary TCP reset probes. The controlled failure reproduces the cleanup mechanism, not the original network timing.
- Installed Windows CPython 3.12.14 / Uvicorn 0.54.0 are tested. The compatibility test for the later `_detach(transport)` signature is not an actual Python 3.13 runtime test. CPython private transport APIs require rechecking when the bundled runtime changes.

No stdlib files, user Codex configuration, credentials or global event-loop policy are modified.
