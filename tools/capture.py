"""DIY Thermostat — bus trace capture client.

Connects to the ESP32 bus_jsonl stream (TCP 2373) and records it to a
timestamped .jsonl file. Auto-reconnects if the connection drops
(the ESP32 drops idle TCP clients after 5 min of bus silence, which
is exactly what happens while the furnace breaker is off).

Usage:
    python capture.py coldstart
    -> saves coldstart-2026-10-28-143000.jsonl next to this script
Stop with Ctrl+C; the .jsonl file is the capture.

Note: the client flushes per chunk — a 0 KB capture file means the
stream never started in that run, not that buffered data was lost.
"""

import socket
import sys
import time
import datetime

HOST = "192.168.1.72"
PORT = 2373


def main() -> None:
    name = sys.argv[1] if len(sys.argv) > 1 else "trace"
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    fname = f"{name}-{stamp}.jsonl"
    print(f"Recording to {fname} — Ctrl+C to stop.")
    lines = 0
    with open(fname, "wb") as f:
        while True:
            try:
                print(f"Connecting to {HOST}:{PORT} ...")
                sock = socket.create_connection((HOST, PORT), timeout=10)
                print("Connected. Waiting for bus traffic.")
                sock.settimeout(None)
                while True:
                    data = sock.recv(4096)
                    if not data:
                        raise ConnectionError("stream closed")
                    f.write(data)
                    f.flush()
                    lines += data.count(b"\n")
                    sys.stdout.write(data.decode(errors="replace"))
                    sys.stdout.flush()
            except KeyboardInterrupt:
                print(f"\nStopped. {lines} lines saved to {fname}")
                return
            except OSError as e:
                print(f"Connection problem ({e}). Retrying in 3 s...")
                time.sleep(3)


if __name__ == "__main__":
    main()
