#!/usr/bin/env python3
"""
Simple WHOIS Lookup Tool

Looks up registration info for a domain by querying a WHOIS server directly
over a raw TCP socket (port 43). Only supports a few common TLDs for now.
"""

import argparse
import socket

WHOIS_SERVERS = {
    "com": "whois.verisign-grs.com",
    "net": "whois.verisign-grs.com",
    "org": "whois.pir.org",
}


def get_whois_server(domain):
    """Return the WHOIS server to query, based on the domain's TLD."""
    tld = domain.rsplit(".", 1)[-1].lower()
    return WHOIS_SERVERS.get(tld)


def whois_lookup(domain, server, port=43, timeout=5):
    """Query a WHOIS server for a domain and return the raw text response."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    sock.connect((server, port))
    sock.sendall((domain + "\r\n").encode("utf-8"))

    # WHOIS servers don't send a length up front, they just close the
    # connection when they're done, so keep reading until that happens.
    response = b""
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            break
        response += chunk

    sock.close()
    return response.decode("utf-8", errors="replace")


def main():
    parser = argparse.ArgumentParser(description="Simple WHOIS lookup tool.")
    parser.add_argument("domain", help="Domain to look up, e.g. example.com")
    args = parser.parse_args()

    server = get_whois_server(args.domain)
    if not server:
        print("Sorry, no WHOIS server configured for that domain's TLD.")
        print(f"Supported TLDs: {', '.join(WHOIS_SERVERS.keys())}")
        return

    print(f"Querying {server} for {args.domain}...\n")
    result = whois_lookup(args.domain, server)
    print(result)


if __name__ == "__main__":
    main()