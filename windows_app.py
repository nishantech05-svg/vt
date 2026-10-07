"""Lightweight Windows launcher: one instance, no-focus floating dictation panel."""
import ctypes
from ctypes import wintypes as w
import queue
import threading

u = ctypes.WinDLL("user32", use_last_error=True)
k = ctypes.WinDLL("kernel32", use_last_error=True)
g = ctypes.WinDLL("gdi32", use_last_error=True)
LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, w.HWND, w.UINT, w.WPARAM, w.LPARAM)


def bind(dll, name, result, *args):
    fn = getattr(dll, name)
    fn.restype, fn.argtypes = result, args
    return fn


bind(k, "CreateMutexW", w.HANDLE, ctypes.c_void_p, w.BOOL, w.LPCWSTR)
bind(k, "CreateEventW", w.HANDLE, ctypes.c_void_p, w.BOOL, w.BOOL, w.LPCWSTR)
bind(k, "SetEvent", w.BOOL, w.HANDLE)
bind(k, "WaitForSingleObject", w.DWORD, w.HANDLE, w.DWORD)
bind(k, "CloseHandle", w.BOOL, w.HANDLE)
bind(k, "GetModuleHandleW", w.HMODULE, w.LPCWSTR)
bind(u, "CreateWindowExW", w.HWND, w.DWORD, w.LPCWSTR, w.LPCWSTR, w.DWORD,
     ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, w.HWND, w.HMENU, w.HINSTANCE, ctypes.c_void_p)
bind(u, "DefWindowProcW", LRESULT, w.HWND, w.UINT, w.WPARAM, w.LPARAM)
bind(u, "SendMessageW", LRESULT, w.HWND, w.UINT, w.WPARAM, w.LPARAM)
bind(u, "SetWindowTextW", w.BOOL, w.HWND, w.LPCWSTR)
bind(u, "EnableWindow", w.BOOL, w.HWND, w.BOOL)
bind(u, "ShowWindow", w.BOOL, w.HWND, ctypes.c_int)
bind(u, "DestroyWindow", w.BOOL, w.HWND)
bind(u, "SetTimer", ctypes.c_size_t, w.HWND, ctypes.c_size_t, w.UINT, ctypes.c_void_p)
bind(u, "KillTimer", w.BOOL, w.HWND, ctypes.c_size_t)
bind(u, "GetForegroundWindow", w.HWND)
bind(u, "GetWindowThreadProcessId", w.DWORD, w.HWND, ctypes.POINTER(w.DWORD))
bind(k, "GetCurrentProcessId", w.DWORD)
bind(u, "GetMessageW", w.BOOL, ctypes.POINTER(w.MSG), w.HWND, w.UINT, w.UINT)
bind(u, "TranslateMessage", w.BOOL, ctypes.POINTER(w.MSG))
bind(u, "DispatchMessageW", LRESULT, ctypes.POINTER(w.MSG))
bind(g, "GetStockObject", w.HANDLE, ctypes.c_int)
bind(u, "SystemParametersInfoW", w.BOOL, w.UINT, w.UINT, ctypes.c_void_p, w.UINT)


class WindowClass(ctypes.Structure):
    _fields_ = [("style", w.UINT), ("proc", WNDPROC), ("cls_extra", ctypes.c_int),
               ("wnd_extra", ctypes.c_int), ("instance", w.HINSTANCE), ("icon", w.HICON),
               ("cursor", w.HANDLE), ("background", w.HBRUSH),
               ("menu", w.LPCWSTR), ("name", w.LPCWSTR)]


bind(u, "RegisterClassW", w.WORD, ctypes.POINTER(WindowClass))


class InstanceLock:
    def __init__(self, name="VoiceType.App.v1"):
        # The mutex is created atomically and Windows releases it on process exit.
        self.handle = k.CreateMutexW(None, False, "Local\\" + name)
        error = ctypes.get_last_error()
        if not self.handle:
            raise ctypes.WinError(error)
        self.primary = error != 183  # ERROR_ALREADY_EXISTS
        self.wake = k.CreateEventW(None, False, False, "Local\\" + name + ".Show")
        if not self.wake:
            k.CloseHandle(self.handle)
            raise ctypes.WinError(ctypes.get_last_error())
        if not self.primary:
            k.SetEvent(self.wake)

    def close(self):
        k.CloseHandle(self.wake)
        k.CloseHandle(self.handle)


class Player:
    def __init__(self, instance, show=True):
        self.instance = instance
        self.events = queue.Queue()
        self.commands = queue.Queue()
        self.engine = None
        self.target = None
        self.status = "Loading speech engine…"
        self.last_state = None
        self.closing = threading.Event()
        self.controls = {}
        self.proc = WNDPROC(self.window_proc)
        module = k.GetModuleHandleW(None)
        cls = WindowClass(0, self.proc, 0, 0, module, None, None, 6, None, "VoiceTypePlayer")
        if not u.RegisterClassW(ctypes.byref(cls)):
            raise ctypes.WinError(ctypes.get_last_error())
        area = w.RECT()
        if not u.SystemParametersInfoW(0x30, 0, ctypes.byref(area), 0):
            raise ctypes.WinError(ctypes.get_last_error())
        # TOPMOST + NOACTIVATE: controls never take the target app's keyboard focus.
        self.hwnd = u.CreateWindowExW(0x08000008, cls.name, "VoiceType", 0x00CA0000,
            max(area.left, area.right - 440), max(area.top, area.bottom - 260),
            420, 240, None, None, module, None)
        if not self.hwnd:
            raise ctypes.WinError(ctypes.get_last_error())
        self.control("STATIC", "VoiceType  •  Ctrl+Alt+Space", 16, 10, 380, 24, 10)
        self.control("STATIC", self.status, 16, 36, 380, 36, 11)
        self.control("EDIT", "Your transcript will appear here after you stop recording.",
                     16, 74, 380, 70, 12, 0x00200844)
        self.control("BUTTON", "Start", 16, 155, 180, 34, 101)
        self.control("BUTTON", "Stop", 216, 155, 180, 34, 102)
        self.refresh_buttons()
        if show:
            u.ShowWindow(self.hwnd, 4)  # SW_SHOWNOACTIVATE
        u.SetTimer(self.hwnd, 1, 100, None)

    def control(self, kind, text, x, y, width, height, identifier, style=0):
        handle = u.CreateWindowExW(0, kind, text, 0x50000000 | style,
            x, y, width, height, self.hwnd, identifier, k.GetModuleHandleW(None), None)
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        self.controls[identifier] = handle
        u.SendMessageW(handle, 0x30, g.GetStockObject(17), True)
        return handle

    def window_proc(self, hwnd, message, wp, lp):
        if message == 0x21:  # WM_MOUSEACTIVATE
            return 3  # MA_NOACTIVATE
        if message == 0x111:  # WM_COMMAND
            if (wp & 0xffff) in (101, 102):
                self.request("start" if (wp & 0xffff) == 101 else "stop")
            return 0
        if message == 0x113:  # WM_TIMER
            self.pump()
            return 0
        if message == 0x10:  # WM_CLOSE
            self.closing.set()
            self.commands.put("quit")
            u.DestroyWindow(hwnd)
            return 0
        if message == 2:  # WM_DESTROY
            u.KillTimer(hwnd, 1)
            u.PostQuitMessage(0)
            return 0
        return u.DefWindowProcW(hwnd, message, wp, lp)

    def request(self, command):
        self.commands.put(command)

    def refresh_buttons(self):
        engine = self.engine
        ready = engine is not None and engine._model is not None and not engine._transcribing
        recording = engine is not None and engine._stream is not None
        state = (ready, recording)
        if state != self.last_state:
            u.EnableWindow(self.controls[101], ready and not recording)
            u.EnableWindow(self.controls[102], recording)
            self.last_state = state

    def pump(self):
        if k.WaitForSingleObject(self.instance.wake, 0) == 0:
            u.ShowWindow(self.hwnd, 4)
        for _ in range(100):
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            u.SetWindowTextW(self.controls[11 if kind == "status" else 12], value)
        self.refresh_buttons()

    def insert_text(self, text):
        if self.closing.is_set():
            return
        if not self.target or u.GetForegroundWindow() != self.target:
            raise RuntimeError("Focus changed. Your transcript is kept in the panel.")
        from voice_type import type_at_cursor
        type_at_cursor(text)

    def worker(self):
        stop_hook = None
        try:
            from voice_type import VoiceType, keyboard, HOTKEY
            self.engine = VoiceType(
                on_status=lambda text: self.events.put(("status", text)),
                on_transcript=lambda text: self.events.put(("transcript", text)),
                insert_text=self.insert_text)
            self.events.put(("status", "Loading local model… First launch may download it."))
            self.engine._load_model()
            if self.closing.is_set():
                return
            token = keyboard.add_hotkey(HOTKEY, lambda: self.request("toggle"), trigger_on_release=True)
            stop_hook = lambda: keyboard.remove_hotkey(token)
            while not self.closing.is_set():
                command = self.commands.get()
                if command == "quit":
                    break
                if self.engine._transcribing:
                    continue
                recording = self.engine._stream is not None
                if (command == "start" and recording) or (command == "stop" and not recording):
                    continue
                if not recording:
                    foreground = u.GetForegroundWindow()
                    process_id = w.DWORD()
                    u.GetWindowThreadProcessId(foreground, ctypes.byref(process_id))
                    self.target = foreground if process_id.value != k.GetCurrentProcessId() else None
                self.engine.toggle_recording()
        except Exception as exc:
            self.events.put(("status", f"Unable to start: {exc}"))
        finally:
            if stop_hook:
                stop_hook()
            if self.engine and self.engine._stream:
                self.engine._stream.stop()
                self.engine._stream.close()

    def run(self):
        threading.Thread(target=self.worker, daemon=True).start()
        msg = w.MSG()
        while True:
            result = u.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if result == -1:
                raise ctypes.WinError(ctypes.get_last_error())
            if not result:
                break
            u.TranslateMessage(ctypes.byref(msg))
            u.DispatchMessageW(ctypes.byref(msg))


def main():
    instance = InstanceLock()
    try:
        if instance.primary:
            Player(instance).run()
    finally:
        instance.close()
