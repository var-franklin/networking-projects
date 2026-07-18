#!/usr/bin/env python3
"""
Simple Traceroute Visualizer

Wraps Windows' tracert command and prints a clean table of each hop:
hop number, hostname, IP address, and round-trip time.
"""

import argparse
import re
import subprocess

HOP_LINE = re.compile(
    r"^\s*(?P<hop>\d+)\s+"
    r"(?P<rtt1><?\d+\s*ms|\*)\s+"
    r"(?P<rtt2><?\d+\s*ms|\*)\s+"
    r"(?P<rtt3><?\d+\s*ms|\*)\s+"
    r"(?P<rest>.+)$"
)

HOST_IP_LINE = re.compile(r"^(?P<hostname>\S+)\s+\[(?P<ip>[\d.]+)\]$")


def format_rtts(rtts):
    """Turn ['1 ms', '<1 ms', '1 ms'] into '1ms/<1ms/1ms', or 'timed out'."""
    if all(r == "*" for r in rtts):
        return "timed out"
    return "/".join(r.replace(" ", "") for r in rtts)


def parse_hop_line(line):
    """Pull hop number, hostname, IP, and RTTs out of one tracert output line."""
    match = HOP_LINE.match(line)
    if not match:
        return None

    hop = int(match.group("hop"))
    rtts = [match.group("rtt1"), match.group("rtt2"), match.group("rtt3")]
    rest = match.group("rest").strip()

    if "Request timed out" in rest:
        return hop, "*", "*", rtts

    host_ip_match = HOST_IP_LINE.match(rest)
    if host_ip_match:
        hostname = host_ip_match.group("hostname")
        ip = host_ip_match.group("ip")
    else:
        # No brackets means tracert just printed a bare IP with no hostname
        hostname = "-"
        ip = rest

    return hop, hostname, ip, rtts


def run_traceroute(target, max_hops):
    """Run tracert and return its raw text output."""
    result = subprocess.run(
        ["tracert", "-h", str(max_hops), target],
        capture_output=True,
        text=True,
    )
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description="Simple traceroute visualizer.")
    parser.add_argument("target", help="Target host, e.g. google.com or 8.8.8.8")
    parser.add_argument("--max-hops", type=int, default=30, help="Maximum hops to trace (default: 30)")
    args = parser.parse_args()

    print(f"Tracing route to {args.target} (max {args.max_hops} hops)...\n")
    output = run_traceroute(args.target, args.max_hops)

    hops = []
    for line in output.splitlines():
        parsed = parse_hop_line(line)
        if parsed:
            hops.append(parsed)

    if not hops:
        print("No hops found. Raw output was:\n")
        print(output)
        return

    print(f"{'Hop':<5}{'Hostname':<35}{'IP':<16}{'RTT'}")
    print("-" * 75)
    for hop, hostname, ip, rtts in hops:
        print(f"{hop:<5}{hostname:<35}{ip:<16}{format_rtts(rtts)}")


if __name__ == "__main__":
    main()