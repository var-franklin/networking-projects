#!/usr/bin/env python3
"""
Simple Packet Sniffer (Windows, requires Administrator)

Captures IP packets passing through your network interface and prints
their source/destination IP, protocol, and (for TCP/UDP) port numbers.

Must be run from an Administrator Command Prompt or PowerShell.
Only sees IP traffic (TCP/UDP/ICMP) -- not ARP or other non-IP protocols.
"""

import socket
import struct

PROTOCOLS = {1: "ICMP", 6: "TCP", 17: "UDP"}


def parse_ip_header(data):
    """Pull header length, protocol, TTL, source IP, and dest IP from an IP header."""
    version_ihl, tos, total_len, ident, flags_frag, ttl, proto, checksum, src, dst = \
        struct.unpack("!BBHHHBBH4s4s", data[:20])

    ihl = (version_ihl & 0x0F) * 4  # header length in bytes (IHL is counted in 32-bit words)
    src_ip = socket.inet_ntoa(src)
    dst_ip = socket.inet_ntoa(dst)

    return ihl, proto, ttl, src_ip, dst_ip


def parse_ports(data, ihl):
    """Pull source and destination ports out of a TCP or UDP header."""
    src_port, dst_port = struct.unpack("!HH", data[ihl:ihl + 4])
    return src_port, dst_port


def start_sniffing():
    """Set up the raw socket and capture packets until Ctrl+C."""
    host = socket.gethostbyname(socket.gethostname())

    try:
        sniffer = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_IP)
        sniffer.bind((host, 0))
        sniffer.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        sniffer.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)
    except OSError as e:
        print(f"Could not start sniffing: {e}")
        print("This needs to be run from an Administrator Command Prompt or PowerShell.")
        return

    print(f"Sniffing on {host}. Press Ctrl+C to stop.\n")

    try:
        while True:
            packet, _ = sniffer.recvfrom(65535)
            ihl, proto, ttl, src_ip, dst_ip = parse_ip_header(packet)
            proto_name = PROTOCOLS.get(proto, f"proto {proto}")

            if proto in (6, 17):  # TCP or UDP -- both have ports in the same spot
                src_port, dst_port = parse_ports(packet, ihl)
                print(f"{proto_name:<5} {src_ip}:{src_port} -> {dst_ip}:{dst_port}  (TTL={ttl})")
            else:
                print(f"{proto_name:<5} {src_ip} -> {dst_ip}  (TTL={ttl})")
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        sniffer.ioctl(socket.SIO_RCVALL, socket.RCVALL_OFF)
        sniffer.close()


if __name__ == "__main__":
    start_sniffing()