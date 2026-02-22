"""
discord_rpc.py — StatusAI Custom Discord IPC Client
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Pure synchronous Discord Rich Presence client using Windows named pipes.
Zero asyncio dependency — no event loop conflicts.
"""

import ctypes
import ctypes.wintypes
import json
import os
import struct
import time


# ──────────────────────────────────────────────
#  Win32 Constants
# ──────────────────────────────────────────────

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = ctypes.wintypes.HANDLE(-1).value


# ──────────────────────────────────────────────
#  Discord IPC Client
# ──────────────────────────────────────────────

class DiscordRPC:
    """
    Fully synchronous Discord Rich Presence client.
    Communicates via Windows named pipes — no asyncio, no pypresence.
    """

    def __init__(self, client_id: str):
        self.client_id = client_id
        self._pipe: int | None = None
        self._connected = False
        self._start_time: int = 0

    @property
    def connected(self) -> bool:
        return self._connected

    # ── Connection ──

    def connect(self) -> dict:
        """Connect to Discord IPC and perform handshake."""
        for i in range(10):
            pipe_path = f"\\\\.\\pipe\\discord-ipc-{i}"
            try:
                handle = ctypes.windll.kernel32.CreateFileW(
                    pipe_path,
                    GENERIC_READ | GENERIC_WRITE,
                    0,
                    None,
                    OPEN_EXISTING,
                    0,
                    None,
                )
                # Check valid handle (compare as unsigned)
                if handle == INVALID_HANDLE_VALUE or handle == -1 or handle == 0:
                    continue

                self._pipe = handle
                break
            except Exception:
                continue

        if self._pipe is None:
            raise ConnectionError(
                "Discord IPC pipe bulunamadı! Discord uygulaması açık mı?"
            )

        # Handshake
        self._send(0, {"v": 1, "client_id": self.client_id})
        _, response = self._recv()

        if response.get("evt") == "ERROR":
            error_data = response.get("data", {})
            code = error_data.get("code", "?")
            msg = error_data.get("message", "Unknown error")
            self._close_pipe()
            raise ConnectionError(f"Error Code: {code} Message: {msg}")

        self._connected = True
        self._start_time = int(time.time())
        return response

    # ── RPC Operations ──

    def update(
        self,
        state: str | None = None,
        details: str | None = None,
        large_image: str | None = None,
        large_text: str | None = None,
        small_image: str | None = None,
        small_text: str | None = None,
        buttons: list[dict] | None = None,
    ) -> dict:
        """Update Discord Rich Presence with optional buttons."""
        if not self._connected:
            raise RuntimeError("RPC bağlantısı yok! Önce connect() çağırın.")

        activity: dict = {}

        if state:
            activity["state"] = state
        if details:
            activity["details"] = details

        # Assets
        assets: dict = {}
        if large_image:
            assets["large_image"] = large_image
        if large_text:
            assets["large_text"] = large_text
        if small_image:
            assets["small_image"] = small_image
        if small_text:
            assets["small_text"] = small_text
        if assets:
            activity["assets"] = assets

        # Timestamps (use connect time so elapsed doesn't reset)
        activity["timestamps"] = {"start": self._start_time}

        # Buttons (max 2)
        if buttons:
            activity["buttons"] = buttons[:2]

        nonce = f"{os.getpid()}-{time.time()}"
        payload = {
            "cmd": "SET_ACTIVITY",
            "args": {"pid": os.getpid(), "activity": activity},
            "nonce": nonce,
        }

        self._send(1, payload)
        _, response = self._recv()

        if response.get("evt") == "ERROR":
            error_data = response.get("data", {})
            raise RuntimeError(error_data.get("message", "RPC Update Error"))

        return response

    def clear(self):
        """Clear Discord Rich Presence."""
        if not self._connected:
            return

        nonce = f"{os.getpid()}-{time.time()}"
        payload = {
            "cmd": "SET_ACTIVITY",
            "args": {"pid": os.getpid(), "activity": None},
            "nonce": nonce,
        }
        try:
            self._send(1, payload)
            self._recv()
        except Exception:
            pass

    def close(self):
        """Close the IPC connection."""
        try:
            self.clear()
        except Exception:
            pass
        self._close_pipe()
        self._connected = False

    # ── Low-level IPC ──

    def _send(self, opcode: int, payload: dict):
        """Send a message to the Discord IPC pipe."""
        data = json.dumps(payload).encode("utf-8")
        header = struct.pack("<II", opcode, len(data))
        message = header + data

        written = ctypes.c_ulong(0)
        success = ctypes.windll.kernel32.WriteFile(
            self._pipe,
            message,
            len(message),
            ctypes.byref(written),
            None,
        )
        if not success:
            raise ConnectionError("IPC yazma hatası")

    def _recv(self) -> tuple[int, dict]:
        """Read a message from the Discord IPC pipe."""
        # Read header (8 bytes: opcode + length)
        header_buf = ctypes.create_string_buffer(8)
        read = ctypes.c_ulong(0)
        success = ctypes.windll.kernel32.ReadFile(
            self._pipe,
            header_buf,
            8,
            ctypes.byref(read),
            None,
        )
        if not success or read.value < 8:
            raise ConnectionError("IPC okuma hatası (header)")

        opcode, length = struct.unpack("<II", header_buf.raw)

        # Read payload
        data_buf = ctypes.create_string_buffer(length)
        success = ctypes.windll.kernel32.ReadFile(
            self._pipe,
            data_buf,
            length,
            ctypes.byref(read),
            None,
        )
        if not success:
            raise ConnectionError("IPC okuma hatası (data)")

        response = json.loads(data_buf.raw[: read.value].decode("utf-8"))
        return opcode, response

    def _close_pipe(self):
        """Close the named pipe handle."""
        if self._pipe is not None:
            try:
                ctypes.windll.kernel32.CloseHandle(self._pipe)
            except Exception:
                pass
            self._pipe = None
