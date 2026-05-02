"""
WSL2 DNS Relay — forwards UDP + TCP DNS queries from Windows LAN → AdGuard Home in WSL2.
Run via Task Scheduler (see wsl-dns-proxy.ps1). Requires Python 3.8+ on Windows.
"""
import socket
import threading
import subprocess
import sys
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger(__name__)

LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 53
UPSTREAM_PORT = 53
BUFFER_SIZE = 4096
TCP_TIMEOUT = 5


def get_wsl_ip():
    """Detect the WSL2 IP from Windows side."""
    try:
        result = subprocess.run(
            ["wsl", "hostname", "-I"],
            capture_output=True, text=True, timeout=10
        )
        ip = result.stdout.strip().split()[0]
        if ip:
            return ip
    except Exception as e:
        log.error(f"Failed to get WSL2 IP: {e}")
    return None


def handle_udp(sock, data, addr, upstream_ip):
    """Forward a single UDP DNS query and send the response back."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as upstream:
            upstream.settimeout(3)
            upstream.sendto(data, (upstream_ip, UPSTREAM_PORT))
            response, _ = upstream.recvfrom(BUFFER_SIZE)
        sock.sendto(response, addr)
    except Exception as e:
        log.debug(f"UDP relay error from {addr}: {e}")


def handle_tcp_client(conn, addr, upstream_ip):
    """Forward a single TCP DNS connection to upstream (AdGuard)."""
    try:
        conn.settimeout(TCP_TIMEOUT)
        data = b""
        # DNS over TCP: first 2 bytes = message length
        header = conn.recv(2)
        if len(header) < 2:
            return
        msg_len = int.from_bytes(header, "big")
        while len(data) < msg_len:
            chunk = conn.recv(msg_len - len(data))
            if not chunk:
                break
            data += chunk

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as upstream:
            upstream.settimeout(TCP_TIMEOUT)
            upstream.connect((upstream_ip, UPSTREAM_PORT))
            upstream.sendall(header + data)
            response = b""
            resp_header = upstream.recv(2)
            if len(resp_header) == 2:
                resp_len = int.from_bytes(resp_header, "big")
                while len(response) < resp_len:
                    chunk = upstream.recv(resp_len - len(response))
                    if not chunk:
                        break
                    response += chunk
            conn.sendall(resp_header + response)
    except Exception as e:
        log.debug(f"TCP relay error from {addr}: {e}")
    finally:
        conn.close()


def run_udp_server(upstream_ip):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((LISTEN_HOST, LISTEN_PORT))
    log.info(f"UDP DNS relay listening on {LISTEN_HOST}:{LISTEN_PORT} → {upstream_ip}:{UPSTREAM_PORT}")
    while True:
        try:
            data, addr = sock.recvfrom(BUFFER_SIZE)
            threading.Thread(target=handle_udp, args=(sock, data, addr, upstream_ip), daemon=True).start()
        except Exception as e:
            log.error(f"UDP server error: {e}")


def run_tcp_server(upstream_ip):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((LISTEN_HOST, LISTEN_PORT))
    sock.listen(64)
    log.info(f"TCP DNS relay listening on {LISTEN_HOST}:{LISTEN_PORT} → {upstream_ip}:{UPSTREAM_PORT}")
    while True:
        try:
            conn, addr = sock.accept()
            threading.Thread(target=handle_tcp_client, args=(conn, addr, upstream_ip), daemon=True).start()
        except Exception as e:
            log.error(f"TCP server error: {e}")


def main():
    # Retry getting WSL IP (WSL2 may still be starting up)
    upstream_ip = None
    for attempt in range(10):
        upstream_ip = get_wsl_ip()
        if upstream_ip:
            break
        log.warning(f"WSL2 IP not found, retrying ({attempt+1}/10)...")
        time.sleep(3)

    if not upstream_ip:
        log.error("Could not detect WSL2 IP. Is WSL2 running? Exiting.")
        sys.exit(1)

    log.info(f"WSL2 upstream: {upstream_ip}")

    # Start UDP and TCP servers in parallel threads
    threading.Thread(target=run_udp_server, args=(upstream_ip,), daemon=True).start()
    threading.Thread(target=run_tcp_server, args=(upstream_ip,), daemon=True).start()

    log.info("DNS relay running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        log.info("Shutting down.")


if __name__ == "__main__":
    main()
