"""
server.py — TCP Chat Server (one-on-one)

This is the "listening" side of the chat. It:
  1. Creates a TCP socket
  2. Binds it to a local address/port
  3. Listens for an incoming connection
  4. Accepts exactly one client
  5. Spawns a background thread to *receive* messages, while the main
     thread stays free to *send* messages typed by the user

Run this FIRST, then run client.py in a separate terminal.
"""

import socket
import threading
from datetime import datetime

HOST = "127.0.0.1"  # "localhost" — only accepts connections from this same machine.
                     # Change to "0.0.0.0" to accept connections from other devices
                     # on the same network.
PORT = 5555


def timestamp() -> str:
    """Helper: HH:MM:SS string used to stamp outgoing messages."""
    return datetime.now().strftime("%H:%M:%S")


def receive_messages(conn: socket.socket, stop_event: threading.Event) -> None:
    """
    Runs in its own background thread for the lifetime of the connection.

    WHY A SEPARATE THREAD?
    conn.recv() is a blocking call — it will not return until data
    arrives on the socket, or the connection is closed. If we only had
    one thread, the program would have to choose between waiting for
    incoming messages OR waiting for the user to type (input() also
    blocks). Running recv() here lets both happen "at the same time."

    IMPORTANT LIMITATION:
    TCP is a byte STREAM, not a sequence of discrete messages. A single
    conn.recv(4096) call is not guaranteed to return exactly one message
    someone sent — it could return part of a message, or several
    messages stuck together, depending on network timing. 
    This is a real simplification.
    """
    while not stop_event.is_set():
        try:
            data = conn.recv(4096)  # read up to 4096 bytes waiting in the socket's buffer
        except OSError:
            break

        if not data:
            # recv() returning an empty bytes object (b"") is TCP's way of
            # signaling "the other side closed the connection."
            print("\n[System] The other user disconnected. Press Enter to exit.")
            stop_event.set()
            break

        message = data.decode("utf-8")
        # Re-print the "You: " prompt after the incoming message so the
        # user's input line doesn't look broken mid-typing.
        print(f"\n{message}\nYou: ", end="", flush=True)


def main() -> None:
    # AF_INET     -> use IPv4 addressing
    # SOCK_STREAM -> use TCP (reliable, ordered byte stream) as opposed to
    #                SOCK_DGRAM, which would give you UDP (fire-and-forget packets)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Without this, restarting the server quickly after stopping it often
    # raises. This option tells the OS it's fine to reuse the address immediately.
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    server_socket.bind((HOST, PORT))  # bind (address, port) combination
    server_socket.listen(1)           # start listening; queue at most 1 pending connection
    print(f"[System] Server listening on {HOST}:{PORT}. Waiting for a client...")

    # accept() BLOCKS here until a client calls connect(). It returns a
    # NEW socket object (conn) dedicated to this one client, plus their
    # address — the original server_socket keeps listening for others
    # (we just never call accept() again, since this is one-on-one).
    conn, addr = server_socket.accept()
    print(f"[System] Client connected from {addr}")

    username = input("Enter your username: ").strip() or "Server"

    stop_event = threading.Event()
    receiver_thread = threading.Thread(
        target=receive_messages, args=(conn, stop_event), daemon=True
    )
    receiver_thread.start()

    print("[System] Connected! Type your messages below. Type /quit to exit.\n")

    try:
        while not stop_event.is_set():
            outgoing = input("You: ")

            if outgoing.strip() == "/quit":
                farewell = f"[{timestamp()}] {username} has left the chat."
                conn.sendall(farewell.encode("utf-8"))
                break

            formatted = f"[{timestamp()}] {username}: {outgoing}"
            # sendall() vs send(): send() can transmit only PART of the
            # data in one call and returns the byte count actually sent,
            # leaving you to loop and send the rest yourself. sendall()
            # does that looping for you and only returns once everything
            # is sent (or raises an error).
            conn.sendall(formatted.encode("utf-8"))
    except (KeyboardInterrupt, ConnectionResetError, BrokenPipeError):
        print("\n[System] Connection interrupted.")
    finally:
        stop_event.set()
        conn.close()
        server_socket.close()
        print("[System] Server shut down.")


if __name__ == "__main__":
    main()