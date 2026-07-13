"""
client.py — TCP Chat Client

This is the "connecting" side of the chat. It:
  1. Creates a TCP socket
  2. Actively connects to the server's address/port
  3. Spawns a background thread to *receive* messages, while the main
     thread stays free to *send* messages typed by the user

Run server.py FIRST, then run this in a separate terminal.
"""

import socket
import threading
from datetime import datetime

HOST = "127.0.0.1"  # Must match the server's HOST — the address it's listening on.
PORT = 5555         # Must match the server's PORT.


def timestamp() -> str:
    """Helper: HH:MM:SS string used to stamp outgoing messages."""
    return datetime.now().strftime("%H:%M:%S")


def receive_messages(sock: socket.socket, stop_event: threading.Event) -> None:
    """
    Same role as on the server side: block on recv() in the background so
    the main thread stays free to read from input(). See server.py for a
    fuller explanation of why this needs its own thread, and the note
    about TCP not guaranteeing one recv() = one sent message.
    """
    while not stop_event.is_set():
        try:
            data = sock.recv(4096)
        except OSError:
            break

        if not data:
            print("\n[System] The other user disconnected. Press Enter to exit.")
            stop_event.set()
            break

        message = data.decode("utf-8")
        print(f"\n{message}\nYou: ", end="", flush=True)


def main() -> None:
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    print(f"[System] Connecting to {HOST}:{PORT}...")
    # connect() performs the TCP three-way handshake (SYN / SYN-ACK / ACK)
    # under the hood. This call blocks until the connection is established
    # or it fails (e.g. ConnectionRefusedError if no server is listening).
    client_socket.connect((HOST, PORT))
    print("[System] Connected!")

    username = input("Enter your username: ").strip() or "Client"

    stop_event = threading.Event()
    receiver_thread = threading.Thread(
        target=receive_messages, args=(client_socket, stop_event), daemon=True
    )
    receiver_thread.start()

    print("[System] Type your messages below. Type /quit to exit.\n")

    try:
        while not stop_event.is_set():
            outgoing = input("You: ")

            if outgoing.strip() == "/quit":
                farewell = f"[{timestamp()}] {username} has left the chat."
                client_socket.sendall(farewell.encode("utf-8"))
                break

            formatted = f"[{timestamp()}] {username}: {outgoing}"
            client_socket.sendall(formatted.encode("utf-8"))
    except (KeyboardInterrupt, ConnectionResetError, BrokenPipeError):
        print("\n[System] Connection interrupted.")
    except ConnectionRefusedError:
        print("\n[System] Could not connect — is server.py running?")
    finally:
        stop_event.set()
        client_socket.close()
        print("[System] Client shut down.")


if __name__ == "__main__":
    main()