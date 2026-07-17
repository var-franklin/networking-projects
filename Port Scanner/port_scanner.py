#!/usr/bin/env python3
"""
Simple TCP Port Scanner

Checks which TCP ports are open on a single host, using a normal
connect() attempt on each port (a "TCP connect scan").
"""

import argparse
import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# A short list of common ports and what they're usually used for.
COMMON_PORTS = {
    21: "FTP",
    22: "SSH",
    23: "Telnet",
    25: "SMTP",
    53: "DNS",
    80: "HTTP",
    110: "POP3",
    135: "MS RPC",
    139: "NetBIOS",
    143: "IMAP",
    443: "HTTPS",
    445: "SMB",
    587: "SMTP (submission)",
    993: "IMAPS",
    995: "POP3S",
    1433: "MSSQL",
    3306: "MySQL",
    3389: "RDP",
    5432: "PostgreSQL",
    5900: "VNC",
    8080: "HTTP (alt)",
}


def scan_port(host, port, timeout):
    """Try to connect to one port. Returns (port, True) if open, (port, False) if not."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    result = sock.connect_ex((host, port))  # 0 means the connection succeeded
    sock.close()
    return port, result == 0


def scan_ports(host, ports, workers, timeout):
    """Scan a list of ports on one host at the same time and return the open ones."""
    print(f"Scanning {len(ports)} ports on {host}...\n")
    start_time = time.time()

    open_ports = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        pending_tasks = []
        for port in ports:
            task = executor.submit(scan_port, host, port, timeout)
            pending_tasks.append(task)

        for task in as_completed(pending_tasks):
            port, is_open = task.result()
            if is_open:
                open_ports.append(port)
                service = COMMON_PORTS.get(port, "unknown")
                print(f"  OPEN: {port} ({service})")

    elapsed_time = time.time() - start_time
    open_ports.sort()

    print(f"\nDone in {elapsed_time:.1f} seconds.")
    print(f"{len(open_ports)} open port(s) out of {len(ports)} checked.")

    return open_ports


def main():
    parser = argparse.ArgumentParser(description="Simple TCP port scanner.")
    parser.add_argument("host", help="Target host, e.g. 192.168.1.1 or example.com")
    parser.add_argument("--start", type=int, help="Start of a custom port range")
    parser.add_argument("--end", type=int, help="End of a custom port range")
    parser.add_argument("--workers", type=int, default=50, help="Ports to check at once (default: 50)")
    parser.add_argument("--timeout", type=float, default=1.0, help="Timeout per port in seconds (default: 1.0)")
    args = parser.parse_args()

    if (args.start is None) != (args.end is None):
        print("Error: --start and --end must be used together.")
        return

    if args.start is not None and args.end is not None:
        ports = list(range(args.start, args.end + 1))
    else:
        ports = list(COMMON_PORTS.keys())

    scan_ports(args.host, ports, args.workers, args.timeout)


if __name__ == "__main__":
    main()