#!/usr/bin/env python3

"""
Simple Ping Sweep Tool in Windows

Pings every host in a subnet and prints which ones responded.
"""

import argparse
import ipaddress
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


def ping_host(ip, timeout_ms):
    """Ping one host. Returns (ip, True) if it replied, (ip, False) if not."""
    result = subprocess.run(
        ["ping", "-n", "1", "-w", str(timeout_ms), ip],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    is_up = result.returncode == 0
    return ip, is_up


def get_hosts(subnet):
    """Turn a CIDR subnet string into a list of individual IP addresses."""
    network = ipaddress.ip_network(subnet, strict=False)

    host_list = []
    for ip in network.hosts():
        host_list.append(str(ip))

    return host_list


def sort_key(ip):
    """Used to sort IPs in proper numeric order, not plain text order."""
    return ipaddress.ip_address(ip)


def sweep(subnet, workers, timeout_ms):
    """Ping every host in the subnet at the same time and report which are up."""
    hosts = get_hosts(subnet)
    print(f"Pinging {len(hosts)} hosts in {subnet} using {workers} workers...\n")

    start_time = time.time()
    live_hosts = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        # Start a ping for every host in the background.
        pending_tasks = []
        for ip in hosts:
            task = executor.submit(ping_host, ip, timeout_ms)
            pending_tasks.append(task)

        # Check results as each ping finishes.
        for task in as_completed(pending_tasks):
            ip, is_up = task.result()
            if is_up:
                live_hosts.append(ip)
                print(f"  UP: {ip}")

    elapsed_time = time.time() - start_time
    live_hosts.sort(key=sort_key)

    print(f"\nDone in {elapsed_time:.1f} seconds.")
    print(f"{len(live_hosts)} out of {len(hosts)} hosts responded.")

    return live_hosts


def main():
    parser = argparse.ArgumentParser(description="Simple ping sweep tool.")
    parser.add_argument("subnet", help="Subnet in CIDR format, e.g. 192.168.1.0/24")
    parser.add_argument("--workers", type=int, default=50,
                         help="Number of pings to run at the same time (default: 50)")
    parser.add_argument("--timeout", type=int, default=1000,
                         help="Timeout per ping in milliseconds (default: 1000)")
    args = parser.parse_args()

    sweep(args.subnet, args.workers, args.timeout)


if __name__ == "__main__":
    main()