#!/usr/bin/env python3
"""
Simple MAC Vendor Lookup Tool

Reads your computer's ARP table (arp -a) to find devices on your local
network, then looks up each MAC address's manufacturer using a small
offline list of common vendor prefixes (OUIs).

This is a SAMPLE list, not the full IEEE registry (which has 30,000+
entries) -- unrecognized vendors will show up as "Unknown vendor".
"""

import re
import subprocess

# OUI = the first 3 bytes of a MAC address, assigned by IEEE to a
# manufacturer. Keys are uppercase, no separators (e.g. "001E14").
OUI_VENDORS = {
    "001E14": "Cisco Systems",
    "001517": "Intel Corporation",
    "001B21": "Intel Corporation",
    "00224D": "Intel Corporation",
    "001B63": "Apple, Inc.",
    "3C0754": "Apple, Inc.",
    "ACBC32": "Apple, Inc.",
    "001422": "Dell Inc.",
    "001EC9": "Dell Inc.",
    "B82A72": "Dell Inc.",
    "001F29": "Hewlett Packard",
    "002481": "Hewlett Packard",
    "70106F": "Hewlett Packard",
    "001018": "Broadcom",
    "00904C": "Broadcom",
    "B499BA": "Broadcom",
    "005056": "VMware (virtual machine)",
    "00155D": "Microsoft Hyper-V (virtual machine)",
    "080027": "Oracle VirtualBox (virtual machine)",
    "00163E": "Xen Hypervisor (virtual machine)",
    "0012FB": "Samsung Electronics",
    "E8508B": "Samsung Electronics",
    "B827EB": "Raspberry Pi Foundation",
}


def normalize_mac(mac):
    """Turn 'AA-BB-CC-11-22-33' into 'AABBCC112233', uppercase, no separators."""
    return mac.upper().replace("-", "").replace(":", "")


def get_vendor(mac):
    """Look up the vendor for a MAC address using its OUI (first 3 bytes)."""
    oui = normalize_mac(mac)[:6]
    return OUI_VENDORS.get(oui, "Unknown vendor")


def get_arp_table():
    """Run 'arp -a' and return a list of (ip, mac) pairs found on this network."""
    result = subprocess.run(["arp", "-a"], capture_output=True, text=True)

    pattern = re.compile(r"(\d{1,3}(?:\.\d{1,3}){3})\s+([0-9a-fA-F]{2}(?:-[0-9a-fA-F]{2}){5})")

    entries = []
    for line in result.stdout.splitlines():
        match = pattern.search(line)
        if match:
            ip = match.group(1)
            mac = match.group(2)
            entries.append((ip, mac))

    return entries


def main():
    entries = get_arp_table()

    if not entries:
        print("No ARP entries found. Try pinging a few devices first, then run this again.")
        return

    print(f"{'IP Address':<16}{'MAC Address':<20}{'Vendor'}")
    print("-" * 60)
    for ip, mac in entries:
        vendor = get_vendor(mac)
        print(f"{ip:<16}{mac:<20}{vendor}")


if __name__ == "__main__":
    main()