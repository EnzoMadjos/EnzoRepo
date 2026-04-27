"""
discovery.py — UDP-based peer discovery and auto-election for PITOGO app.

How it works:
  1. On startup, broadcast "PITOGO_DISCOVER" on the LAN for DISCOVERY_TIMEOUT_SEC.
  2. If another instance replies with "PITOGO_SERVER:<host>:<port>", connect as client.
  3. If no reply, self-elect as the server and start broadcasting "PITOGO_SERVER".
  4. Elected server sends heartbeat broadcasts every HEARTBEAT_INTERVAL seconds.
  5. Clients watching heartbeats trigger re-election after HEARTBEAT_MISSES misses.
"""
from __future__ import annotations

import socket
import threading
import time
from typing import Callable, Optional

import config
import app_logger

MAGIC_DISCOVER = b"PITOGO_DISCOVER"
MAGIC_SERVER   = b"PITOGO_SERVER"

_role: str = "unknown"          # "leader" | "client" | "unknown"
_leader_addr: Optional[tuple]   = None   # (host, port) of current leader
_stop_event   = threading.Event()


def get_role() -> str:
    return _role


def get_leader() -> Optional[tuple]:
    return _leader_addr


# ── Discovery ─────────────────────────────────────────────────────────────────

def _broadcast_discover(sock: socket.socket) -> Optional[tuple]:
    """Broadcast DISCOVER for DISCOVERY_TIMEOUT_SEC. Return (host, port) if leader found."""
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(0.5)
    deadline = time.monotonic() + config.DISCOVERY_TIMEOUT_SEC
    while time.monotonic() < deadline:
        try:
            sock.sendto(MAGIC_DISCOVER, ("<broadcast>", config.DISCOVERY_PORT))
        except OSError:
            pass
        try:
            data, addr = sock.recvfrom(256)
            if data.startswith(MAGIC_SERVER):
                parts = data.decode().split(":")
                # format: PITOGO_SERVER:<host>:<port>
                if len(parts) == 3:
                    host = parts[1]
                    port = int(parts[2])
                    return (host, port)
        except socket.timeout:
            pass
    return None


# ── Heartbeat broadcaster (leader role) ───────────────────────────────────────

def _heartbeat_sender(sock: socket.socket, app_port: int) -> None:
    """Leader broadcasts its address as a heartbeat."""
    my_ip  = _get_local_ip()
    msg    = f"PITOGO_SERVER:{my_ip}:{app_port}".encode()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    while not _stop_event.is_set():
        try:
            sock.sendto(msg, ("<broadcast>", config.DISCOVERY_PORT))
        except OSError:
            pass
        _stop_event.wait(config.HEARTBEAT_INTERVAL)


# ── Heartbeat watcher (client role) ───────────────────────────────────────────

def _heartbeat_watcher(
    sock: socket.socket,
    on_leader_lost: Callable,
    on_new_leader: Callable[[tuple], None],
) -> None:
    """Client listens for heartbeats; triggers callbacks on leader changes."""
    global _leader_addr
    sock.settimeout(config.HEARTBEAT_INTERVAL * config.HEARTBEAT_MISSES)
    while not _stop_event.is_set():
        try:
            data, _ = sock.recvfrom(256)
            if data.startswith(MAGIC_SERVER):
                parts = data.decode().split(":")
                if len(parts) == 3:
                    new_leader = (parts[1], int(parts[2]))
                    if new_leader != _leader_addr:
                        _leader_addr = new_leader
                        on_new_leader(new_leader)
        except socket.timeout:
            app_logger.warn("Leader heartbeat lost — triggering re-election")
            _leader_addr = None
            on_leader_lost()
            return


# ── Utility ───────────────────────────────────────────────────────────────────

def _get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# ── Main entrypoint ───────────────────────────────────────────────────────────

def start(
    app_port: int,
    on_elected_leader: Callable,
    on_became_client: Callable[[tuple], None],
    on_leader_lost: Callable,
) -> None:
    """
    Start peer discovery. Calls one of:
      on_elected_leader()            — this instance is the new leader
      on_became_client((host, port)) — found an existing leader
    """
    global _role, _leader_addr, _stop_event
    _stop_event = threading.Event()

    disc_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    disc_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        disc_sock.bind(("", config.DISCOVERY_PORT))
    except OSError:
        # Port already in use — another instance is likely the leader
        disc_sock.close()
        app_logger.warn("Discovery port busy — assuming a leader is already running")
        _role = "client"
        on_became_client(("127.0.0.1", app_port))
        return

    app_logger.info("Discovery: searching for existing leader…")
    leader = _broadcast_discover(disc_sock)

    if leader:
        _role        = "client"
        _leader_addr = leader
        app_logger.info("Discovery: found leader", host=leader[0], port=leader[1])
        on_became_client(leader)

        # Watch heartbeats in background
        watch_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        watch_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        watch_sock.bind(("", config.DISCOVERY_PORT))
        threading.Thread(
            target=_heartbeat_watcher,
            args=(watch_sock, on_leader_lost, on_became_client),
            daemon=True,
        ).start()
    else:
        _role = "leader"
        app_logger.info("Discovery: no leader found — self-electing as leader")
        on_elected_leader()

        # Broadcast heartbeats in background
        hb_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        threading.Thread(
            target=_heartbeat_sender,
            args=(hb_sock, app_port),
            daemon=True,
        ).start()

    disc_sock.close()


def stop() -> None:
    _stop_event.set()
