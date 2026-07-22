#!/usr/bin/env python3

"""
Interactive Ping Sweep Tool (Windows)

Pings every host in a subnet and reports which ones responded, with
their response time (latency). Can be run two ways:

  1. Non-interactively, like before:
         python ping_sweep.py 192.168.1.0/24
  2. Interactively, with no arguments:
         python ping_sweep.py
     -> it will prompt you for the subnet and settings.

After a scan, it shows a menu to rescan a specific host or re-run the sweep.
"""

import argparse
import ipaddress
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Matches "time=23ms" or "time<1ms" inside Windows ping.exe output.
# Group 1 is the comparison symbol ("=" or "<"), group 2 is the number.
TIME_PATTERN = re.compile(r"time([=<])(\d+)ms")

# If a subnet has more hosts than this, ask for confirmation before
# blasting out that many threads at once.
LARGE_SUBNET_THRESHOLD = 1024


def ping_host(ip, timeout_ms):
    """
    Ping one host once.

    Returns a dict: {"ip": ip, "up": True/False, "latency_ms": float or None}

    latency_ms is None if the host didn't reply, or if it replied but we
    couldn't parse a time out of ping's output (e.g. unexpected format).
    """
    result = subprocess.run(
        ["ping", "-n", "1", "-w", str(timeout_ms), ip],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )

    is_up = result.returncode == 0
    latency_ms = None

    if is_up:
        match = TIME_PATTERN.search(result.stdout)
        if match:
            comparison, value = match.groups()
            latency_ms = float(value)
            # Windows reports "time<1ms" for very fast replies (e.g. localhost).
            # Treat that as 0 rather than leaving it unparsed.
            if comparison == "<":
                latency_ms = 0.0

    return {"ip": ip, "up": is_up, "latency_ms": latency_ms}


def ping_available():
    """
    Check once, up front, whether the `ping` command actually exists on
    this machine (e.g. wrong OS, or PATH is misconfigured).

    Without this check, ping_host() would raise FileNotFoundError the
    first time it's called -- and since we run hundreds of these in
    parallel, that means hundreds of identical crashes instead of one
    clear error message.
    """
    try:
        subprocess.run(
            ["ping", "-n", "1", "-w", "100", "127.0.0.1"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        return True
    except FileNotFoundError:
        return False


def get_hosts(subnet):
    """Turn a CIDR subnet string into a list of individual IP strings."""
    network = ipaddress.ip_network(subnet, strict=False)
    return [str(ip) for ip in network.hosts()]


def sort_key(result):
    """Sort by numeric IP value, not text order (so .2 sorts before .10)."""
    return ipaddress.ip_address(result["ip"])


def format_latency(result):
    """Turn a result's latency_ms into a display string."""
    if result["latency_ms"] is None:
        return "? ms"
    return f"{result['latency_ms']:.0f} ms"


def sweep(subnet, workers, timeout_ms):
    """
    Ping every host in the subnet concurrently, printing live progress.
    Returns a list of result dicts (sorted by IP) for hosts that responded.
    Returns an empty list if the subnet was invalid or the user cancelled.
    """
    try:
        hosts = get_hosts(subnet)
    except ValueError as error:
        print(f"'{subnet}' isn't a valid subnet: {error}")
        return []

    total = len(hosts)

    if total > LARGE_SUBNET_THRESHOLD:
        answer = input(
            f"That subnet has {total} hosts — this will start a lot of pings "
            f"at once. Continue? [y/N]: "
        ).strip().lower()
        if answer != "y":
            print("Cancelled.\n")
            return []

    print(f"\nPinging {total} hosts in {subnet} using {workers} workers...\n")

    start_time = time.time()
    checked = 0
    live_hosts = []

    try:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            pending_tasks = [
                executor.submit(ping_host, ip, timeout_ms) for ip in hosts
            ]

            for task in as_completed(pending_tasks):
                result = task.result()
                checked += 1

                if result["up"]:
                    live_hosts.append(result)

                # "\r" moves the cursor to the start of the line, so this
                # print overwrites the previous one instead of stacking up.
                print(
                    f"\r  Checked {checked}/{total}  |  {len(live_hosts)} up so far   ",
                    end="",
                    flush=True,
                )
    except KeyboardInterrupt:
        print("\n\nStopped early (Ctrl+C). Showing results collected so far.\n")

    print()  # move the cursor past the progress line

    live_hosts.sort(key=sort_key)
    elapsed_time = time.time() - start_time

    print(f"Done in {elapsed_time:.1f} seconds.")
    print(f"{len(live_hosts)} out of {total} hosts responded.\n")

    for result in live_hosts:
        print(f"  UP: {result['ip']:<15}  {format_latency(result)}")

    return live_hosts


def prompt_int(question, default, minimum=1):
    """
    Ask the user for a whole number, with a default if they just hit Enter.

    Keeps re-asking instead of crashing if they type something that isn't
    a number, or a number that's too small to make sense (e.g. 0 workers).
    """
    while True:
        raw = input(f"{question} [default {default}]: ").strip()

        if raw == "":
            return default

        try:
            value = int(raw)
        except ValueError:
            print(f"  '{raw}' isn't a whole number. Try again (e.g. {default}).")
            continue

        if value < minimum:
            print(f"  Enter a number of at least {minimum}.")
            continue

        return value


def prompt_for_settings():
    """Ask the user for sweep settings interactively, with sensible defaults."""
    subnet = input("Subnet to scan (e.g. 192.168.1.0/24): ").strip()
    workers = prompt_int("Concurrent pings", default=50)
    timeout_ms = prompt_int("Timeout per ping in ms", default=1000)

    return subnet, workers, timeout_ms


def rescan_host():
    """Ping a single host a few times and show each reply's latency."""
    ip = input("IP address to rescan: ").strip()
    attempts = 4

    print(f"\nPinging {ip} {attempts} times...\n")
    for attempt in range(1, attempts + 1):
        result = ping_host(ip, timeout_ms=1000)
        if result["up"]:
            print(f"  Reply {attempt}: {format_latency(result)}")
        else:
            print(f"  Reply {attempt}: no response (timeout)")
    print()


def show_menu(live_hosts):
    """
    Show a post-scan menu and act on the user's choice.
    Returns "rerun" to sweep again, or "exit" to quit.
    """
    while True:
        print("What next?")
        print("  1) Rescan a specific host")
        print("  2) Re-run the sweep")
        print("  3) Exit")
        choice = input("Choose 1-3: ").strip()

        if choice == "1":
            rescan_host()
        elif choice == "2":
            return "rerun"
        elif choice == "3":
            return "exit"
        else:
            print("Please enter 1, 2, or 3.\n")


def main():
    parser = argparse.ArgumentParser(
        description="Interactive ping sweep tool (Windows)."
    )
    parser.add_argument(
        "subnet", nargs="?",
        help="Subnet in CIDR format, e.g. 192.168.1.0/24. "
             "Omit this to be prompted interactively instead.",
    )
    parser.add_argument("--workers", type=int, default=50,
                         help="Number of pings to run at the same time (default: 50)")
    parser.add_argument("--timeout", type=int, default=1000,
                         help="Timeout per ping in milliseconds (default: 1000)")
    args = parser.parse_args()

    if not ping_available():
        print("Couldn't find the 'ping' command on this system.")
        print("Make sure it's installed and available on your PATH, then try again.")
        sys.exit(1)

    if args.subnet:
        subnet, workers, timeout_ms = args.subnet, args.workers, args.timeout
    else:
        subnet, workers, timeout_ms = prompt_for_settings()

    while True:
        live_hosts = sweep(subnet, workers, timeout_ms)
        action = show_menu(live_hosts)
        if action == "exit":
            break
        # "rerun" falls through and loops back to sweep() again


if __name__ == "__main__":
    main()