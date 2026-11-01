"""Desktop-owned event loop; preserve Proactor and finalize accepted loopback sockets.

CPython's Proactor callback can skip close/detach when socket.shutdown raises.
This compatibility boundary is restricted to this loop's accepted loopback TCP
transports. It does not patch asyncio, global policies, TLS or subprocess pipes.
See docs/workbench-experience/SERVER-TRANSPORT.md for upstream references.
"""
import asyncio
import inspect
import logging
import socket
import sys

_log = logging.getLogger(__name__)


def _finalize_loopback_connection(transport, exc):
    if transport._called_connection_lost:
        return
    errors = []
    peer_disconnect = None
    if not getattr(transport, '_loopback_protocol_notified', False):
        transport._loopback_protocol_notified = True
        try:
            transport._protocol.connection_lost(exc)
        except BaseException as error:
            errors.append(error)
    sock = transport._sock
    closed = sock is None
    if sock is not None:
        try:
            if sock.fileno() != -1:
                sock.shutdown(socket.SHUT_RDWR)
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError) as error:
            peer_disconnect = type(error).__name__
        except OSError as error:
            if getattr(error, 'winerror', None) == 10057:
                peer_disconnect = 'not-connected'
            else:
                errors.append(error)
        except BaseException as error:
            errors.append(error)
        try:
            sock.close()
        except BaseException as error:
            errors.append(error)
        try:
            closed = sock.fileno() == -1
        except BaseException as error:
            errors.append(error)
    if closed:
        transport._sock = None
        server = transport._server
        if server is not None:
            try:
                # CPython 3.12 counts transports; 3.13+ tracks transport objects.
                detach = server._detach
                if len(inspect.signature(detach).parameters) == 0:
                    detach()
                else:
                    detach(transport)
                transport._server = None
            except BaseException as error:
                errors.append(error)
        transport._called_connection_lost = transport._server is None
    elif not errors:
        errors.append(RuntimeError('Loopback socket close did not release its handle'))
    if closed and peer_disconnect is not None:
        try:
            _log.debug('Released loopback transport after peer disconnect (%s)', peer_disconnect)
        except BaseException as error:
            errors.append(error)
    if len(errors) == 1:
        raise errors[0]
    if errors:
        raise BaseExceptionGroup('Loopback transport finalization failed', errors)


def new_event_loop():
    """Uvicorn loop factory, scoped to this server; no global policy changes."""
    if sys.platform != 'win32':
        return asyncio.new_event_loop()
    from asyncio.proactor_events import _ProactorSocketTransport

    class LoopbackSocketTransport(_ProactorSocketTransport):
        _call_connection_lost = _finalize_loopback_connection

    class DesktopProactorLoop(asyncio.ProactorEventLoop):
        def _make_socket_transport(self, sock, protocol, waiter=None, extra=None, server=None):
            if server is not None and sock.getsockname()[0] in ('127.0.0.1', '::1'):
                return LoopbackSocketTransport(self, sock, protocol, waiter, extra, server)
            return super()._make_socket_transport(sock, protocol, waiter, extra, server)

    return DesktopProactorLoop()
