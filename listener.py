import os
import subprocess
import serial
import socket
import threading
import time
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# === Config ===
SERIAL_PORT  = "/dev/tty.usbmodem14601"
BAUD         = 115200
UDP_PORT     = 5555
DEDUP_WINDOW = 0.5

# === Per-unit trigger handlers ===
# Return True to suppress the default log line.
# Stubs — replace body to handle events. Signature: (unit_name, guid, source) -> bool
# Return True to suppress the default log line.
def on_trigger(*_) -> bool:
    return False

TRIGGER_HANDLERS: dict[str, callable] = {
    # "ButtonA": lambda guid, source: subprocess.run(["osascript", "-e", '...']),
}

# Signature: (unit_names: list[str], source: str) -> bool
def on_combo(*_) -> bool:
    return False

# Signature: (unit_name: str, guid: str) -> bool
def on_slave_connected(*_) -> bool:
    return False

# === State ===
_dedup: dict[str, float] = {}
_dedup_lock = threading.Lock()
_slaves: dict[str, str] = {}   # guid -> name

def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")

def _dedup_check(key: str) -> bool:
    """Returns True if the message is a duplicate and should be dropped."""
    now = time.monotonic()
    with _dedup_lock:
        if now - _dedup.get(key, 0) < DEDUP_WINDOW:
            return True
        _dedup[key] = now
        expired = [k for k, v in _dedup.items() if now - v > DEDUP_WINDOW * 20]
        for k in expired:
            del _dedup[k]
    return False

def _handle_trigger(parts: list[str], source: str):
    if len(parts) < 3:
        return
    unit_name = parts[1]
    guid      = parts[2]

    if _dedup_check(f"TRIGGER_{guid}"):
        return

    handler = TRIGGER_HANDLERS.get(unit_name)
    if handler:
        handler(guid, source)
    else:
        subprocess.Popen(["python", "main.py"], cwd=SCRIPT_DIR)
        if not on_trigger(unit_name, guid, source):
            print(f"[{_ts()}][{source}] TRIGGER  unit={unit_name}  id={guid[-4:]}")

def _handle_combo(source: str):
    key = f"COMBO_{int(time.monotonic() / DEDUP_WINDOW)}"
    if _dedup_check(key):
        return
    names = list(_slaves.values()) if _slaves else []
    if not on_combo(names, source):
        print(f"[{_ts()}][{source}] COMBO!   units={names if names else '?'}")

def _handle_slave_connected(parts: list[str], source: str):
    if len(parts) < 3:
        return
    # Format: SLAVE_CONNECTED_<name>_<guid>
    unit_name  = parts[1]
    slave_guid = parts[2]
    _slaves[slave_guid] = unit_name
    if not on_slave_connected(unit_name, slave_guid):
        print(f"[{_ts()}][{source}] ONLINE   unit={unit_name}  id={slave_guid[-4:]}")

_DISPATCH = {
    "TRIGGER": _handle_trigger,
    "COMBO":   lambda _, source: _handle_combo(source),
    "SLAVE":   _handle_slave_connected,
}

def handle_message(raw: str, source: str):
    parts = raw.strip().split("_")
    if not parts:
        return
    handler = _DISPATCH.get(parts[0])
    if handler:
        handler(parts, source)
    else:
        print(f"[{_ts()}][{source}] {raw}")

# === Transport threads ===
def serial_listener():
    while True:
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD, timeout=1)
            print(f"[{_ts()}] Serial connected on {SERIAL_PORT}")
            while True:
                line = ser.readline().decode(errors="ignore").strip()
                if line:
                    handle_message(line, "USB")
        except serial.SerialException:
            print(f"[{_ts()}] Serial port {SERIAL_PORT} not found — UDP still active, retrying in 5s")
            time.sleep(5)

def udp_listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if os.name != "nt":
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind(("", UDP_PORT))
    except OSError as e:
        print(f"[{_ts()}] UDP bind failed on port {UDP_PORT}: {e}")
        print(f"[{_ts()}] Check nothing else is using port {UDP_PORT}, or allow it through your firewall.")
        return
    print(f"[{_ts()}] UDP listening on port {UDP_PORT}")
    while True:
        data, addr = sock.recvfrom(1024)
        msg = data.decode(errors="ignore").strip()
        handle_message(msg, f"WiFi/{addr[0]}")

if __name__ == "__main__":
    print(f"Quickkey listener  —  serial={SERIAL_PORT}  udp={UDP_PORT}\n")
    threading.Thread(target=serial_listener, daemon=True).start()
    threading.Thread(target=udp_listener,    daemon=True).start()
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nExiting.")
