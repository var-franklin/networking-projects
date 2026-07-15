#!/usr/bin/env python3
"""
Simple UDP Chat (peer-to-peer)

Two people run this same script to chat with each other over UDP.
Each side listens on its own port and sends straight to the other side's port.
There's no "client" or "server" here — both sides work exactly the same way.
"""

import argparse
import socket
import threading
from datetime import datetime


def timestamp():
    """Return the current time as HH:MM:SS."""
    return datetime.now().strftime("%H:%M:%S")


def receive_messages(sock, stop_event):
    """Wait for incoming messages in the background and print them."""
    while not stop_event.is_set():
        try:
            data, addr = sock.recvfrom(4096)
        except OSError:
            break

        message = data.decode("utf-8")
        print(f"\n{message}\nYou: ", end="", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Simple UDP peer-to-peer chat.")
    parser.add_argument("listen_port", type=int, help="Port this side listens on")
    parser.add_argument("peer_port", type=int, help="Port the other side is listening on")
    parser.add_argument("--peer-host", default="127.0.0.1",
                         help="Peer's IP address (default: 127.0.0.1, same machine)")
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Bind on 0.0.0.0 so this also works if the peer is on another device later,
    # not just on this same machine.
    sock.bind(("0.0.0.0", args.listen_port))

    peer_address = (args.peer_host, args.peer_port)
    username = input("Enter your username: ").strip() or "User"

    stop_event = threading.Event()
    receiver_thread = threading.Thread(
        target=receive_messages, args=(sock, stop_event), daemon=True
    )
    receiver_thread.start()

    print(f"[System] Listening on port {args.listen_port}, sending to {peer_address}.")
    print("[System] Type your messages below. Type /quit to exit.\n")

    try:
        while not stop_event.is_set():
            outgoing = input("You: ")

            if outgoing.strip() == "/quit":
                break

            formatted = f"[{timestamp()}] {username}: {outgoing}"
            sock.sendto(formatted.encode("utf-8"), peer_address)
    except (KeyboardInterrupt, OSError):
        print("\n[System] Chat interrupted.")
    finally:
        stop_event.set()
        sock.close()
        print("[System] Chat closed.")


if __name__ == "__main__":
    main()