#!/usr/bin/env python3
"""
Simple DHCP Parser (Windows, requires Administrator)

Captures live DHCP traffic (the DORA exchange: Discover, Offer, Request,
Acknowledge) and prints the important fields from each message.

Must be run from an Administrator Command Prompt or PowerShell.
Tip: run "ipconfig /release" then "ipconfig /renew" in another window
while this is running, to trigger some real DHCP traffic to see.
"""

import socket
import struct

MESSAGE_TYPES = {
    1: "DHCPDISCOVER",
    2: "DHCPOFFER",
    3: "DHCPREQUEST",
    4: "DHCPDECLINE",
    5: "DHCPACK",
    6: "DHCPNAK",
    7: "DHCPRELEASE",
    8: "DHCPINFORM",
}

DHCP_MAGIC_COOKIE = bytes([99, 130, 83, 99])


def parse_ip_header(data):
    """Pull header length and protocol number out of an IP header."""
    ihl = (data[0] & 0x0F) * 4
    protocol = data[9]
    return ihl, protocol


def parse_udp_header(data, offset):
    """Pull source and destination ports out of a UDP header."""
    src_port, dst_port, length, checksum = struct.unpack("!HHHH", data[offset:offset + 8])
    return src_port, dst_port


def parse_dhcp_options(data):
    """Walk the DHCP options section (type, length, value) and pull out the useful ones."""
    options = {}
    i = 0
    while i < len(data):
        code = data[i]
        if code == 255:  # End option, stop here
            break
        if code == 0:  # Pad option, has no length byte
            i += 1
            continue

        length = data[i + 1]
        value = data[i + 2:i + 2 + length]

        if code == 53 and length == 1:
            options["message_type"] = MESSAGE_TYPES.get(value[0], f"unknown ({value[0]})")
        elif code == 1 and length == 4:
            options["subnet_mask"] = socket.inet_ntoa(value)
        elif code == 3 and length >= 4:
            options["router"] = socket.inet_ntoa(value[:4])
        elif code == 6:
            options["dns_servers"] = [socket.inet_ntoa(value[j:j + 4]) for j in range(0, len(value), 4)]
        elif code == 50 and length == 4:
            options["requested_ip"] = socket.inet_ntoa(value)
        elif code == 51 and length == 4:
            options["lease_time_secs"] = struct.unpack("!I", value)[0]
        elif code == 54 and length == 4:
            options["server_id"] = socket.inet_ntoa(value)

        i += 2 + length

    return options


def parse_dhcp_packet(data):
    """Parse a full DHCP payload: fixed header + magic cookie + options."""
    if len(data) < 240:
        return None

    fixed = struct.unpack("!BBBBIHH4s4s4s4s16s64s128s", data[:236])
    op, htype, hlen, hops, xid, secs, flags, ciaddr, yiaddr, siaddr, giaddr, chaddr, sname, file_ = fixed

    if data[236:240] != DHCP_MAGIC_COOKIE:
        return None  # not actually a DHCP packet

    mac = chaddr[:hlen].hex(":") if hlen else chaddr.hex(":")
    options = parse_dhcp_options(data[240:])

    return {
        "xid": xid,
        "client_ip": socket.inet_ntoa(ciaddr),
        "your_ip": socket.inet_ntoa(yiaddr),
        "client_mac": mac,
        "options": options,
    }


def start_capture():
    """Set up the raw socket and capture DHCP traffic until Ctrl+C."""
    host = socket.gethostbyname(socket.gethostname())

    try:
        sniffer = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_IP)
        sniffer.bind((host, 0))
        sniffer.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        sniffer.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)
    except OSError as e:
        print(f"Could not start capturing: {e}")
        print("This needs to be run from an Administrator Command Prompt or PowerShell.")
        return

    print(f"Watching for DHCP traffic on {host}. Press Ctrl+C to stop.")
    print("Tip: run 'ipconfig /release' then 'ipconfig /renew' elsewhere to trigger some.\n")

    try:
        while True:
            packet, _ = sniffer.recvfrom(65535)
            ihl, protocol = parse_ip_header(packet)

            if protocol != 17:  # not UDP, DHCP always rides on UDP
                continue

            src_port, dst_port = parse_udp_header(packet, ihl)
            if src_port not in (67, 68) and dst_port not in (67, 68):
                continue  # not DHCP traffic

            parsed = parse_dhcp_packet(packet[ihl + 8:])
            if not parsed:
                continue

            msg_type = parsed["options"].get("message_type", "unknown")
            print(f"--- {msg_type} (xid={parsed['xid']}) ---")
            print(f"  Client MAC:  {parsed['client_mac']}")
            print(f"  Client IP:   {parsed['client_ip']}")
            print(f"  Offered IP:  {parsed['your_ip']}")
            for key, value in parsed["options"].items():
                if key != "message_type":
                    print(f"  {key}: {value}")
            print()
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        sniffer.ioctl(socket.SIO_RCVALL, socket.RCVALL_OFF)
        sniffer.close()


if __name__ == "__main__":
    start_capture()