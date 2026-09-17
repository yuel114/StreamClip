"""Local video playback inside a Tk HWND using Windows Media Foundation."""

from __future__ import annotations

import ctypes as c
from ctypes import wintypes as w
import math
import os
from pathlib import Path
import queue
import time
import uuid


class _Value(c.Union):
    _fields_ = [("time", c.c_longlong), ("storage", c.c_byte * (2 * c.sizeof(c.c_void_p)))]


class _PropVariant(c.Structure):
    _fields_ = [("vt", c.c_ushort), ("reserved", c.c_ushort * 3), ("value", _Value)]


class _EventHeader(c.Structure):
    _fields_ = [("kind", c.c_int), ("result", c.c_long), ("player", c.c_void_p), ("state", c.c_int), ("properties", c.c_void_p)]


class _Callback(c.Structure):
    _fields_ = [("vtable", c.POINTER(c.c_void_p))]


class MediaFoundationPlayer:
    """One local file and native renderer; all public methods run on the Tk thread.

    Interface slots and structures follow the Windows SDK's mfplay.h. MFPlay
    handles decoding, audio/video synchronization and aspect ratio; Python
    only polls its state. No external player process or codec fallback is used.
    """

    def __init__(self, window_id: int, path: Path, volume: float = 0.7):
        if os.name != "nt":
            raise RuntimeError("内嵌视频播放需要 Windows 10/11。")
        self.path = Path(path).resolve()
        if not self.path.is_file() or self.path.stat().st_size == 0:
            raise ValueError("切片文件不存在或为空，请重新生成切片。")
        self._pointer = c.c_void_p()
        self._com_initialized = False
        self._references = 1
        self._events: queue.SimpleQueue[tuple[int, int]] = queue.SimpleQueue()
        self.ready = self.playing = self.ended = False
        self.playing_requested = self._transition_pending = False
        self.position = self.duration = 0.0
        self._opened_at = time.monotonic()
        self._time_format = (c.c_byte * 16)()  # MFP_POSITIONTYPE_100NS = GUID_NULL.
        self._ole = c.WinDLL("ole32")
        self._ole.CoInitializeEx.argtypes = (c.c_void_p, w.DWORD)
        self._ole.CoInitializeEx.restype = c.c_long
        self._ole.CoUninitialize.argtypes = ()
        self._ole.CoUninitialize.restype = None
        result = self._ole.CoInitializeEx(None, 2)
        if result != -2147417850:  # RPC_E_CHANGED_MODE: an existing apartment is usable.
            self._check(result)
            self._com_initialized = True
        try:
            self._make_callback()
            library = self._library = c.WinDLL("mfplay")
            library.MFPCreateMediaPlayer.argtypes = (w.LPCWSTR, w.BOOL, w.DWORD, c.c_void_p, w.HWND, c.POINTER(c.c_void_p))
            library.MFPCreateMediaPlayer.restype = c.c_long
            # Free-threaded events only write to the queue; they never call Tk.
            self._check(library.MFPCreateMediaPlayer(str(self.path), False, 1, c.byref(self._callback), window_id, c.byref(self._pointer)))
            self.set_volume(volume)
        except Exception:
            self.close()
            raise

    @staticmethod
    def _check(result: int) -> None:
        if result < 0:
            raise RuntimeError(f"Windows 无法播放此视频（0x{result & 0xFFFFFFFF:08X}）。请检查文件是否完整，或重新生成 MP4 切片。")

    def _make_callback(self) -> None:
        supported = {uuid.UUID(value).bytes_le for value in ("00000000-0000-0000-C000-000000000046", "766C8FFB-5FDB-4FEA-A28D-B912996F51BD")}

        def query(_this, interface, output):
            output[0] = None
            if c.string_at(interface, 16) not in supported:
                return -2147467262  # E_NOINTERFACE
            output[0] = c.addressof(self._callback)
            add_ref(_this)
            return 0

        def add_ref(_this):
            self._references += 1
            return self._references

        def release(_this):
            self._references -= 1
            return self._references

        def event(_this, header):
            self._events.put((header.contents.kind, header.contents.result))

        # Keep Python callbacks alive until Shutdown and Release finish.
        self._callbacks = (
            c.WINFUNCTYPE(c.c_long, c.c_void_p, c.c_void_p, c.POINTER(c.c_void_p))(query),
            c.WINFUNCTYPE(w.ULONG, c.c_void_p)(add_ref),
            c.WINFUNCTYPE(w.ULONG, c.c_void_p)(release),
            c.WINFUNCTYPE(None, c.c_void_p, c.POINTER(_EventHeader))(event),
        )
        self._vtable = (c.c_void_p * 4)(*(c.cast(callback, c.c_void_p).value for callback in self._callbacks))
        self._callback = _Callback(self._vtable)

    def _call(self, slot: int, types: tuple = (), *args) -> None:
        if not self._pointer.value:
            raise RuntimeError("视频已关闭，请重新选择切片。")
        vtable = c.cast(self._pointer, c.POINTER(c.POINTER(c.c_void_p))).contents
        self._check(c.WINFUNCTYPE(c.c_long, c.c_void_p, *types)(vtable[slot])(self._pointer, *args))

    def _time(self, slot: int) -> float:
        value = _PropVariant()
        self._call(slot, (c.c_void_p, c.POINTER(_PropVariant)), c.byref(self._time_format), c.byref(value))
        if value.vt not in (20, 21):  # VT_I8 / VT_UI8, no allocated PROPVARIANT payload.
            raise RuntimeError("无法读取视频时间轴。")
        return max(0.0, value.value.time / 10_000_000)

    def poll(self) -> None:
        if not self._pointer.value:
            return
        while not self._events.empty():
            kind, result = self._events.get_nowait()
            self._check(result)
            if kind in (0, 1):  # Play / Pause have completed.
                self._transition_pending = False
            elif kind == 6:  # MFP_EVENT_TYPE_MEDIAITEM_SET
                self.ready = True
                self.duration = self._time(9)  # GetDuration
                if self.duration <= 0:
                    raise RuntimeError("视频时长无效，请重新生成切片。")
                self.update_video()
            elif kind == 11:  # MFP_EVENT_TYPE_PLAYBACK_ENDED
                self.ended = True
                self.playing_requested = False
        if not self.ready:
            if time.monotonic() - self._opened_at > 15:
                raise RuntimeError("视频加载超时，请检查文件或重新选择切片。")
            return
        state = c.c_int()
        self._call(13, (c.POINTER(c.c_int),), c.byref(state))  # GetState
        self.playing = state.value == 2 and not self.ended
        self.position = self.duration if self.ended else min(self.duration, self._time(8))
        self._sync_play_state()

    def play(self) -> None:
        if self.ready:
            if self.ended or self.position >= self.duration - 0.05:
                self.seek(0)
            self.playing_requested = True
            self._sync_play_state()

    def pause(self) -> None:
        self.playing_requested = False
        self._sync_play_state()

    def _sync_play_state(self) -> None:
        # MFPlay commands finish asynchronously. Serialize them, including a
        # tab being hidden before its pending Play event has completed.
        if not self.ready or self._transition_pending:
            return
        state = c.c_int()
        self._call(13, (c.POINTER(c.c_int),), c.byref(state))
        if (state.value == 2) != self.playing_requested:
            self._call(3 if self.playing_requested else 4)
            self._transition_pending = True

    def seek(self, seconds: float) -> None:
        if not self.ready:
            return
        if not math.isfinite(seconds):
            raise ValueError("播放时间必须是有限数值。")
        value = _PropVariant()
        value.vt = 20
        value.value.time = int(max(0.0, min(seconds, self.duration)) * 10_000_000)
        self._call(7, (c.c_void_p, c.POINTER(_PropVariant)), c.byref(self._time_format), c.byref(value))
        self.ended = False

    def set_volume(self, volume: float) -> None:
        if not math.isfinite(volume):
            raise ValueError("音量必须是有限数值。")
        self._call(20, (c.c_float,), max(0.0, min(1.0, volume)))  # SetVolume

    def update_video(self) -> None:
        if self.ready:
            self._call(32)  # UpdateVideo repaints and fits the current HWND client area.

    def close(self) -> None:
        try:
            if self._pointer.value:
                try:
                    self._call(38)  # Shutdown stops decoding and releases the media file.
                finally:
                    self._call(2)  # IUnknown::Release
                    self._pointer = c.c_void_p()
        finally:
            self.ready = self.playing = False
            self.playing_requested = False
            if self._com_initialized:
                self._ole.CoUninitialize()
                self._com_initialized = False
