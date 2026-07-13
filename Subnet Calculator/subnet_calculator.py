"""
subnet_calculator.py — A from-scratch Subnet / VLSM calculator.
No external dependencies. Python 3.7+.
"""

import math


# ---------------------------------------------------------------------------
# Part A: IP <-> integer conversion
# ---------------------------------------------------------------------------

def ip_to_int(ip_str):
    """Convert a dotted-decimal IPv4 string to a 32-bit integer."""
    octets = ip_str.strip().split('.')
    if len(octets) != 4:
        raise ValueError(f"'{ip_str}' is not a valid IPv4 address.")
    value = 0
    for octet in octets:
        if not octet.isdigit():
            raise ValueError(f"'{ip_str}' is not a valid IPv4 address.")
        num = int(octet)
        if not (0 <= num <= 255):
            raise ValueError(f"'{ip_str}' is not a valid IPv4 address.")
        value = (value << 8) | num
    return value


def int_to_ip(value):
    """Convert a 32-bit integer back to dotted-decimal string."""
    return '.'.join(str((value >> shift) & 0xFF) for shift in (24, 16, 8, 0))


def prefix_to_mask_int(prefix):
    """Convert a CIDR prefix length (0-32) to its 32-bit mask integer."""
    if not (0 <= prefix <= 32):
        raise ValueError("Prefix must be between 0 and 32.")
    if prefix == 0:
        return 0
    return (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF


# ---------------------------------------------------------------------------
# Part B: Single-subnet calculation
# ---------------------------------------------------------------------------

def calculate_subnet(ip_str, prefix):
    """Given an IP and prefix length, return every derived fact about the subnet."""
    ip_int = ip_to_int(ip_str)
    mask_int = prefix_to_mask_int(prefix)
    network_int = ip_int & mask_int
    broadcast_int = network_int | (~mask_int & 0xFFFFFFFF)
    total_hosts = 2 ** (32 - prefix)

    if prefix == 32:                       # single host route
        first_host = last_host = network_int
        usable_hosts = 1
    elif prefix == 31:                     # RFC 3021 point-to-point
        first_host = network_int
        last_host = broadcast_int
        usable_hosts = 2
    else:                                  # normal case
        first_host = network_int + 1
        last_host = broadcast_int - 1
        usable_hosts = total_hosts - 2

    return {
        'network': int_to_ip(network_int),
        'broadcast': int_to_ip(broadcast_int),
        'mask': int_to_ip(mask_int),
        'prefix': prefix,
        'first_host': int_to_ip(first_host),
        'last_host': int_to_ip(last_host),
        'total_hosts': total_hosts,
        'usable_hosts': usable_hosts,
    }


def format_subnet_report(details, title="Subnet Details"):
    """Pretty-print a subnet details dict."""
    lines = [f"\n--- {title} ---"]
    lines.append(f"Network Address:   {details['network']}/{details['prefix']}")
    lines.append(f"Subnet Mask:       {details['mask']}")
    lines.append(f"Broadcast Address: {details['broadcast']}")
    lines.append(f"Usable Host Range: {details['first_host']} - {details['last_host']}")
    lines.append(f"Total Addresses:   {details['total_hosts']}")
    lines.append(f"Usable Hosts:      {details['usable_hosts']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Part C: VLSM allocation
# ---------------------------------------------------------------------------

def hosts_to_prefix(hosts_needed):
    """Find the smallest prefix (largest usable block) that fits hosts_needed hosts."""
    if hosts_needed <= 0:
        raise ValueError("Hosts needed must be positive.")
    needed_addresses = hosts_needed + 2       # + network + broadcast
    host_bits = max(2, math.ceil(math.log2(needed_addresses)))
    prefix = 32 - host_bits
    if prefix < 0:
        raise ValueError("Not enough address space (32-bit) for this many hosts.")
    return prefix


def vlsm_allocate(base_network, base_prefix, demands):
    """
    demands: list of (name, hosts_needed) tuples.
    Returns a list of subnet-detail dicts (with 'name' and 'hosts_requested' added),
    in allocation order — sorted largest-first per the VLSM rule.
    """
    base_int = ip_to_int(base_network)
    base_mask = prefix_to_mask_int(base_prefix)
    base_network_int = base_int & base_mask
    base_broadcast_int = base_network_int | (~base_mask & 0xFFFFFFFF)

    sorted_demands = sorted(demands, key=lambda d: d[1], reverse=True)
    allocations = []
    cursor = base_network_int

    for name, hosts_needed in sorted_demands:
        prefix = hosts_to_prefix(hosts_needed)
        block_size = 2 ** (32 - prefix)

        # Align the cursor to a valid boundary for this block size.
        if cursor % block_size != 0:
            cursor = (cursor // block_size + 1) * block_size

        subnet_start = cursor
        subnet_end = subnet_start + block_size - 1

        if subnet_end > base_broadcast_int:
            raise ValueError(
                f"Not enough space left in {base_network}/{base_prefix} "
                f"to allocate '{name}' needing {hosts_needed} hosts."
            )

        details = calculate_subnet(int_to_ip(subnet_start), prefix)
        details['name'] = name
        details['hosts_requested'] = hosts_needed
        allocations.append(details)

        cursor = subnet_start + block_size

    return allocations


# ---------------------------------------------------------------------------
# Part D: Command-line interface
# ---------------------------------------------------------------------------

def run_single_subnet_mode():
    ip = input("Enter an IP address (e.g. 192.168.1.10): ").strip()
    prefix_raw = input("Enter the prefix length (e.g. 24): ").strip()
    try:
        prefix = int(prefix_raw)
        result = calculate_subnet(ip, prefix)
        print(format_subnet_report(result))
    except ValueError as e:
        print(f"Error: {e}")


def run_vlsm_mode():
    base_ip = input("Enter the base network address (e.g. 192.168.1.0): ").strip()
    base_prefix_raw = input("Enter the base prefix length (e.g. 24): ").strip()

    demands = []
    print("Enter each subnet's name and host count. Blank name to finish.")
    while True:
        name = input("  Subnet name: ").strip()
        if not name:
            break
        hosts_raw = input(f"  Hosts needed for '{name}': ").strip()
        try:
            demands.append((name, int(hosts_raw)))
        except ValueError:
            print("  Please enter a whole number for host count.")

    if not demands:
        print("No subnets entered.")
        return

    try:
        base_prefix = int(base_prefix_raw)
        allocations = vlsm_allocate(base_ip, base_prefix, demands)
        for alloc in allocations:
            title = f"{alloc['name']} (requested {alloc['hosts_requested']} hosts)"
            print(format_subnet_report(alloc, title=title))
    except ValueError as e:
        print(f"Error: {e}")


def main():
    while True:
        print("\n===== Subnet / VLSM Calculator =====")
        print("1. Calculate a single subnet")
        print("2. VLSM: allocate multiple subnets from one network")
        print("3. Quit")
        choice = input("Choose an option: ").strip()

        if choice == '1':
            run_single_subnet_mode()
        elif choice == '2':
            run_vlsm_mode()
        elif choice == '3':
            print("Goodbye.")
            break
        else:
            print("Invalid choice, try again.")


if __name__ == "__main__":
    main()
