#!/usr/bin/env python3
"""
Simple DNS Lookup Tool

Looks up the IP address(es) for a hostname, or the hostname for an IP address.
Uses Python's built-in socket module only.
"""

import argparse
import ipaddress
import socket


def is_ip_address(value):
    """Return True if the given string is a valid IP address."""
    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return False


def forward_lookup(hostname):
    """Look up the IP address(es) for a hostname."""
    try:
        _, _, ip_list = socket.gethostbyname_ex(hostname)
        return ip_list
    except socket.gaierror as e:
        print(f"Could not resolve {hostname}: {e}")
        return []


def reverse_lookup(ip):
    """Look up the hostname for an IP address."""
    try:
        hostname, _, _ = socket.gethostbyaddr(ip)
        return hostname
    except socket.herror as e:
        print(f"Could not resolve {ip}: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Simple DNS lookup tool.")
    parser.add_argument("target", help="A hostname (e.g. google.com) or an IP address")
    args = parser.parse_args()

    if is_ip_address(args.target):
        print(f"Looking up hostname for {args.target}...")
        hostname = reverse_lookup(args.target)
        if hostname:
            print(f"  {args.target} -> {hostname}")
    else:
        print(f"Looking up IP addresses for {args.target}...")
        ip_list = forward_lookup(args.target)
        for ip in ip_list:
            print(f"  {args.target} -> {ip}")


if __name__ == "__main__":
    main()