"""Scoped transport cleanup: explicit injected errors, real TCP and local stdio.

These tests are not native GUI, remote Codex or natural WinError reproduction.
"""
import asyncio
import socket
import struct
import sys
from types import SimpleNamespace
import pytest
from app.server_loop import _finalize_loopback_connection, new_event_loop


class Sock:
    def __init__(self, events, shutdown_error=None, close_error=None):
        self.events, self.shutdown_error, self.close_error = events, shutdown_error, close_error
        self.closed = False
    def fileno(self): return -1 if self.closed else 1
    def shutdown(self, how):
        self.events.append('shutdown')
        if self.shutdown_error: raise self.shutdown_error
    def close(self):
        self.events.append('close')
        if self.close_error: raise self.close_error
        self.closed = True


def owned_transport(shutdown_error=None, protocol_error=None, close_error=None, object_tracking=False):
    events = []
    def lost(exc):
        events.append('protocol')
        if protocol_error: raise protocol_error
    if object_tracking:
        class Server:
            def _detach(self, transport):
                assert transport._sock is None
                events.append('detach')
    else:
        class Server:
            def _detach(self): events.append('detach')
    return SimpleNamespace(_called_connection_lost=False, _protocol=SimpleNamespace(connection_lost=lost),
                           _sock=Sock(events, shutdown_error, close_error), _server=Server()), events


@pytest.mark.parametrize('object_tracking', [False, True])
def test_finalization_is_idempotent_for_both_cpython_server_contracts(object_tracking):
    t, events = owned_transport(object_tracking=object_tracking)
    _finalize_loopback_connection(t, None)
    _finalize_loopback_connection(t, None)
    assert events == ['protocol', 'shutdown', 'close', 'detach']
    assert t._sock is None and t._server is None and t._called_connection_lost


@pytest.mark.parametrize('kind', [ConnectionResetError, ConnectionAbortedError, BrokenPipeError])
def test_peer_disconnect_during_shutdown_still_closes_socket_and_detaches(kind):
    t, events = owned_transport(shutdown_error=kind('CONTROLLED_PEER_DISCONNECT'))
    _finalize_loopback_connection(t, None)
    assert events == ['protocol', 'shutdown', 'close', 'detach']
    assert t._sock is None and t._server is None


def test_already_disconnected_windows_socket_is_released():
    error = OSError('CONTROLLED_NOT_CONNECTED'); error.winerror = 10057
    t, events = owned_transport(shutdown_error=error)
    _finalize_loopback_connection(t, None)
    assert events[-2:] == ['close', 'detach']


@pytest.mark.parametrize('kind', [OSError, RuntimeError, KeyboardInterrupt])
def test_unexpected_shutdown_errors_are_not_hidden(kind):
    error = kind('CONTROLLED_UNEXPECTED_SHUTDOWN')
    t, events = owned_transport(shutdown_error=error)
    with pytest.raises(kind) as caught: _finalize_loopback_connection(t, None)
    assert caught.value is error
    assert events[-2:] == ['close', 'detach']


def test_protocol_errors_including_connection_reset_are_not_silenced():
    error = ConnectionResetError('CONTROLLED_PROTOCOL_FAILURE')
    t, events = owned_transport(protocol_error=error)
    with pytest.raises(ConnectionResetError) as caught: _finalize_loopback_connection(t, None)
    assert caught.value is error and events[-2:] == ['close', 'detach']


def test_protocol_shutdown_and_close_failures_are_all_retained():
    errors = [ValueError('CONTROLLED_PROTOCOL'), OSError('CONTROLLED_SHUTDOWN'), RuntimeError('CONTROLLED_CLOSE')]
    t, events = owned_transport(shutdown_error=errors[1], protocol_error=errors[0], close_error=errors[2])
    with pytest.raises(BaseExceptionGroup) as caught: _finalize_loopback_connection(t, None)
    assert list(caught.value.exceptions) == errors
    assert events == ['protocol', 'shutdown', 'close']
    assert t._sock is not None and t._server is not None and not t._called_connection_lost


@pytest.mark.skipif(sys.platform != 'win32', reason='Windows Proactor transport boundary')
@pytest.mark.parametrize('injected_fault', [False, True])
def test_actual_accepted_socket_does_not_strand_server_after_close(injected_fault):
    async def run():
        loop = asyncio.get_running_loop(); errors = []; protocols = []
        loop.set_exception_handler(lambda loop, context: errors.append(context.get('exception')))
        class FaultSocket:
            def __init__(self, sock): self.raw = sock
            def __getattr__(self, name): return getattr(self.raw, name)
            def shutdown(self, how):
                error = ConnectionResetError(10054, 'CONTROLLED_SHUTDOWN_RESET'); error.winerror = 10054
                raise error
        class Protocol(asyncio.Protocol):
            def connection_made(self, transport): self.t = transport; self.calls = 0; protocols.append(self)
            def data_received(self, data):
                self.t.pause_reading()
                if injected_fault: self.t._sock = FaultSocket(self.t._sock)
                self.t.close()
            def connection_lost(self, exc): self.calls += 1
        server = await loop.create_server(Protocol, '127.0.0.1', 0)
        reader, writer = await asyncio.open_connection('127.0.0.1', server.sockets[0].getsockname()[1])
        try:
            # Outgoing transports keep the original implementation.
            assert type(writer.transport).__name__ == '_ProactorSocketTransport'
            writer.write(b'LOCAL_TRANSPORT_PROBE'); await writer.drain()
            assert await asyncio.wait_for(reader.read(1), 3) == b''
            writer.close(); await asyncio.wait_for(writer.wait_closed(), 3)
            server.close(); await asyncio.wait_for(server.wait_closed(), 3)
            assert server._active_count == 0 and len(protocols) == 1
            assert protocols[0].calls == 1 and protocols[0].t._sock is None and not errors
        finally:
            writer.close(); server.close()
            for protocol in protocols:
                if protocol.t._sock is not None: protocol.t._sock.close(); protocol.t.abort()
            await asyncio.sleep(.05)
    with asyncio.Runner(loop_factory=new_event_loop) as runner: runner.run(run())


def test_factory_keeps_global_policy_and_actual_subprocess_pipes():
    policy = asyncio.get_event_loop_policy()
    async def run():
        if sys.platform == 'win32': assert isinstance(asyncio.get_running_loop(), asyncio.ProactorEventLoop)
        process = await asyncio.create_subprocess_exec(sys.executable, '-u', '-c',
            'import sys;sys.stdout.buffer.write(sys.stdin.buffer.readline());sys.stdout.buffer.flush()',
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        try:
            payload = '本地标准输入输出验证\n'.encode('utf8')
            out, err = await asyncio.wait_for(process.communicate(payload), 8)
            assert out == payload and err == b'' and process.returncode == 0
        finally:
            if process.returncode is None: process.terminate(); await process.wait()
    with asyncio.Runner(loop_factory=new_event_loop) as runner: runner.run(run())
    assert asyncio.get_event_loop_policy() is policy


def test_official_mcp_stdio_roundtrip_on_scoped_loop(tmp_path):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    script = tmp_path / 'local_mcp_echo.py'
    script.write_text("""import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types
schema={'type':'object','properties':{'text':{'type':'string'}},'required':['text']}
async def listing(ctx,params):return types.ListToolsResult(tools=[types.Tool(name='echo',description='Local protocol fixture',inputSchema=schema)])
async def calling(ctx,params):return types.CallToolResult(content=[types.TextContent(type='text',text=params.arguments['text'])])
server=Server('LocalProtocolFixture',version='0',on_list_tools=listing,on_call_tool=calling,get_tool_input_schema=lambda name:schema if name=='echo' else None)
async def main():
 async with stdio_server() as (r,w):await server.run(r,w,server.create_initialization_options())
asyncio.run(main())
""", encoding='utf8')
    async def run():
        async with asyncio.timeout(15):
            with (tmp_path / 'mcp-stderr.txt').open('w', encoding='utf8') as log:
                async with stdio_client(StdioServerParameters(command=sys.executable, args=['-u', str(script)], cwd=tmp_path), errlog=log) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        tools = await session.list_tools()
                        assert [tool.name for tool in tools.tools] == ['echo']
                        result = await session.call_tool('echo', {'text': 'LOCAL_MCP_PROTOCOL_OK'})
                        assert not result.is_error and result.content[0].text == 'LOCAL_MCP_PROTOCOL_OK'
    with asyncio.Runner(loop_factory=new_event_loop) as runner: runner.run(run())


def test_logging_failure_cannot_prevent_socket_close_or_detach(monkeypatch):
    from app import server_loop
    error = OSError('CONTROLLED_LOG_WRITE_FAILURE')
    def broken_log(*args): raise error
    monkeypatch.setattr(server_loop._log, 'debug', broken_log)
    t, events = owned_transport(shutdown_error=ConnectionResetError('CONTROLLED_PEER_RESET'))
    with pytest.raises(OSError) as caught: _finalize_loopback_connection(t, None)
    assert caught.value is error
    assert events[-2:] == ['close', 'detach'] and t._called_connection_lost


def test_close_failure_keeps_the_actual_unreleased_owner_until_explicit_retry():
    events = []
    class RefusingSocket:
        closed = False
        refused = True
        def fileno(self): return -1 if self.closed else 12
        def shutdown(self, how): events.append('shutdown')
        def close(self):
            events.append('close')
            if self.refused: raise OSError('CONTROLLED_CLOSE_REFUSED')
            self.closed = True
    class Server:
        active = 1
        def _detach(self): self.active -= 1; events.append('detach')
    sock, server = RefusingSocket(), Server()
    t = SimpleNamespace(_called_connection_lost=False, _protocol=SimpleNamespace(connection_lost=lambda exc: events.append('protocol')), _sock=sock, _server=server)
    with pytest.raises(OSError): _finalize_loopback_connection(t, None)
    assert server.active == 1 and t._sock is sock and t._server is server
    assert not t._called_connection_lost and events == ['protocol', 'shutdown', 'close']
    sock.refused = False
    _finalize_loopback_connection(t, None)
    assert sock.closed and server.active == 0 and t._sock is None and t._server is None
    assert t._called_connection_lost and events.count('protocol') == 1
