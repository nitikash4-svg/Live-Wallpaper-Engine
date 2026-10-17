"""
Live Wallpaper for Windows 10/11
  * Plays a looping video behind the desktop icons on every monitor
  * Tray menu: choose video, pause, mute, start with Windows, compatibility mode
  * Starts at logon through a Scheduled Task (high priority, no Explorer delay)
  * Self-healing: restarts a stalled video, re-attaches after Explorer restarts
Requires:  pip install PyQt6
"""
import os
import sys
import json
import time
import ctypes
import winreg
import traceback
import subprocess
from ctypes import wintypes
from pathlib import Path
from xml.sax.saxutils import escape

APP = "LiveWallpaper"
DIR = Path(os.environ.get("APPDATA", Path.home())) / APP
CFG_FILE, FRAME_FILE, LOG_FILE = DIR / "config.json", DIR / "frame.png", DIR / "error.log"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
DEFAULTS = {"video": "", "muted": True, "autostart": True,
            "static_frame": True, "compat": False, "task_cmd": ""}


# ------------------------------------------------------------ config/log ----
def log_error(exc_info=None):
    try:
        DIR.mkdir(parents=True, exist_ok=True)
        text = "".join(traceback.format_exception(*(exc_info or sys.exc_info())))
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S\n") + text + "\n")
    except Exception:
        pass


def _excepthook(*exc_info):
    log_error(exc_info)
    if sys.stderr:
        traceback.print_exception(*exc_info)


sys.excepthook = _excepthook


def load_cfg():
    try:
        return {**DEFAULTS, **json.loads(CFG_FILE.read_text("utf-8"))}
    except Exception:
        return dict(DEFAULTS)


def save_cfg(cfg):
    DIR.mkdir(parents=True, exist_ok=True)
    CFG_FILE.write_text(json.dumps(cfg, indent=2), "utf-8")


CFG = load_cfg()
if CFG["compat"]:                       # Windows Media Foundation backend
    os.environ["QT_MEDIA_BACKEND"] = "windows"

from PyQt6.QtCore import Qt, QUrl, QTimer, QPoint                      # noqa: E402
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction, QPolygon  # noqa: E402
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QFileDialog  # noqa: E402
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput, QVideoSink  # noqa: E402
from PyQt6.QtMultimediaWidgets import QVideoWidget                     # noqa: E402

# ----------------------------------------------------------------- Win32 ----
user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
HWND = wintypes.HWND

user32.FindWindowW.restype = HWND
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowExW.restype = HWND
user32.FindWindowExW.argtypes = [HWND, HWND, wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.SetParent.restype = HWND
user32.SetParent.argtypes = [HWND, HWND]
user32.IsWindow.argtypes = [HWND]
user32.GetWindowRect.argtypes = [HWND, ctypes.POINTER(wintypes.RECT)]
user32.MoveWindow.argtypes = [HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.BOOL]
user32.ShowWindow.argtypes = [HWND, ctypes.c_int]
user32.SetWindowPos.argtypes = [HWND, HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, wintypes.UINT]
user32.SendMessageTimeoutW.argtypes = [HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM,
                                       wintypes.UINT, wintypes.UINT, ctypes.POINTER(ctypes.c_size_t)]
_get_long = getattr(user32, "GetWindowLongPtrW", user32.GetWindowLongW)
_set_long = getattr(user32, "SetWindowLongPtrW", user32.SetWindowLongW)
_get_long.restype = ctypes.c_ssize_t
_get_long.argtypes = [HWND, ctypes.c_int]
_set_long.restype = ctypes.c_ssize_t
_set_long.argtypes = [HWND, ctypes.c_int, ctypes.c_ssize_t]

kernel32.GetCurrentProcess.restype = wintypes.HANDLE
kernel32.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
kernel32.SetPriorityClass.restype = wintypes.BOOL
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

GWL_STYLE = -16
WS_CHILD, WS_POPUP, WS_CAPTION = 0x40000000, 0x80000000, 0x00C00000
HWND_BOTTOM = HWND(1)
SWP_FLAGS = 0x1 | 0x2 | 0x10          # NOSIZE | NOMOVE | NOACTIVATE
PRIO_HIGH, PRIO_NORMAL = 0x80, 0x20
MUTEX = None


def set_priority(cls):
    try:
        kernel32.SetPriorityClass(kernel32.GetCurrentProcess(), cls)
    except Exception:
        log_error()


def set_static_wallpaper(path):
    user32.SystemParametersInfoW(0x14, 0, str(path), 3)   # SPI_SETDESKWALLPAPER


def get_monitors():
    """Physical-pixel rect (x, y, w, h) of every monitor."""
    rects = []
    proc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HANDLE, wintypes.HDC,
                              ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)

    def cb(_m, _dc, rc, _lp):
        r = rc.contents
        rects.append((r.left, r.top, r.right - r.left, r.bottom - r.top))
        return True

    user32.EnumDisplayMonitors(None, None, proc(cb), 0)
    return rects


def find_desktop_host(timeout=90):
    """
    Returns (host_hwnd, wallpaper_workerw_or_None), or (None, None).
    Win10 / Win11 < 24H2: a WorkerW sibling sits behind the icon window.
    Win11 24H2+:          a WorkerW child lives inside Progman.
    """
    end = time.time() + timeout
    progman = None
    while not progman and time.time() < end:       # wait for Explorer at boot
        progman = user32.FindWindowW("Progman", None)
        if not progman:
            time.sleep(0.1)
    if not progman:
        return None, None

    res = ctypes.c_size_t()
    user32.SendMessageTimeoutW(progman, 0x052C, 0xD, 0x1, 0, 1000, ctypes.byref(res))
    user32.SendMessageTimeoutW(progman, 0x052C, 0, 0, 0, 1000, ctypes.byref(res))

    found = {"w": None}
    proc = ctypes.WINFUNCTYPE(wintypes.BOOL, HWND, wintypes.LPARAM)

    def cb(hwnd, _lp):
        if user32.FindWindowExW(hwnd, None, "SHELLDLL_DefView", None):
            w = user32.FindWindowExW(None, hwnd, "WorkerW", None)
            if w:
                found["w"] = w
        return True

    child = None
    for _ in range(25):                            # up to ~2.5 s, usually instant
        found["w"] = None
        user32.EnumWindows(proc(cb), 0)
        if found["w"]:
            return found["w"], None                # classic layout
        child = user32.FindWindowExW(progman, None, "WorkerW", None)
        if child:
            break
        time.sleep(0.1)
    return progman, child                          # 24H2 layout


def attach_to_desktop(hwnd, host, wp_worker, rect):
    x, y, w, h = rect
    style = (_get_long(hwnd, GWL_STYLE) & ~(WS_POPUP | WS_CAPTION)) | WS_CHILD
    _set_long(hwnd, GWL_STYLE, style)
    user32.SetParent(hwnd, host)
    hr = wintypes.RECT()
    user32.GetWindowRect(host, ctypes.byref(hr))
    user32.MoveWindow(hwnd, x - hr.left, y - hr.top, w, h, True)
    user32.ShowWindow(hwnd, 5)
    if wp_worker:   # 24H2 order: wallpaper layer < our video < desktop icons
        user32.SetWindowPos(hwnd, HWND_BOTTOM, 0, 0, 0, 0, SWP_FLAGS)
        user32.SetWindowPos(wp_worker, HWND_BOTTOM, 0, 0, 0, 0, SWP_FLAGS)


# --------------------------------------------------------------- startup ----
def autostart_parts():
    if getattr(sys, "frozen", False):
        return sys.executable, ""
    pyw = Path(sys.executable).with_name("pythonw.exe")
    exe = pyw if pyw.exists() else Path(sys.executable)
    return str(exe), f'"{os.path.abspath(__file__)}"'


def _task_xml(cmd, args):
    user = escape(f"{os.environ.get('USERDOMAIN', '')}\\{os.environ.get('USERNAME', '')}")
    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers><LogonTrigger><Enabled>true</Enabled><UserId>{user}</UserId></LogonTrigger></Triggers>
  <Principals><Principal id="Author"><UserId>{user}</UserId><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>4</Priority>
    <Enabled>true</Enabled>
  </Settings>
  <Actions Context="Author"><Exec><Command>{escape(cmd)}</Command><Arguments>{escape(args)}</Arguments></Exec></Actions>
</Task>"""


def _run_key(enabled):
    exe, args = autostart_parts()
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if enabled:
            winreg.SetValueEx(k, APP, 0, winreg.REG_SZ, f'"{exe}" {args}'.strip())
        else:
            try:
                winreg.DeleteValue(k, APP)
            except FileNotFoundError:
                pass


def _schtasks(*args):
    return subprocess.run(["schtasks", *args], capture_output=True, stdin=subprocess.DEVNULL,
                          creationflags=0x08000000).returncode      # CREATE_NO_WINDOW


def set_autostart(enabled):
    """Scheduled Task at logon; falls back to the Run key. Returns True on success."""
    try:
        if enabled:
            DIR.mkdir(parents=True, exist_ok=True)
            xml = DIR / "task.xml"
            xml.write_text(_task_xml(*autostart_parts()), encoding="utf-16")
            if _schtasks("/Create", "/TN", APP, "/XML", str(xml), "/F") == 0:
                _run_key(False)
            else:
                _run_key(True)
        else:
            _schtasks("/Delete", "/TN", APP, "/F")
            _run_key(False)
        return True
    except Exception:
        log_error()
        return False


def restart_self():
    global MUTEX
    if MUTEX:
        kernel32.CloseHandle(MUTEX)     # release the single-instance lock
        MUTEX = None
    exe, args = autostart_parts()
    subprocess.Popen(f'"{exe}" {args}'.strip(), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, close_fds=True, creationflags=0x08000008)
    QApplication.quit()


# ------------------------------------------------------------- wallpaper ----
PLAYING = QMediaPlayer.PlaybackState.PlayingState


class Screen(QVideoWidget):
    """One video window covering one monitor."""

    def __init__(self, rect, with_audio):
        super().__init__()
        self.rect_px, self.path, self.last_pos, self.stalls = rect, "", -1, 0
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatioByExpanding)
        self.player = QMediaPlayer(self)
        self.audio = None
        if with_audio:
            self.audio = QAudioOutput(self)
            self.audio.setVolume(0.3)
            self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self)
        self.player.mediaStatusChanged.connect(self._on_status)

    def _on_status(self, status):               # manual loop: more reliable than setLoops
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            QTimer.singleShot(0, self._rewind)

    def _rewind(self):
        self.player.setPosition(0)
        self.player.play()

    def set_muted(self, muted):
        if self.audio:
            self.audio.setMuted(muted)

    def load(self, path):
        self.path, self.last_pos, self.stalls = path, -1, 0
        self.player.setSource(QUrl.fromLocalFile(path))
        self.player.play()

    def ensure_playing(self):
        """Called every few seconds: revive a stopped or frozen player."""
        p = self.player
        if p.playbackState() != PLAYING:
            p.play()
            self.stalls = 0
        else:
            pos = p.position()
            self.stalls = self.stalls + 1 if pos == self.last_pos else 0
            self.last_pos = pos
            if self.stalls >= 2 and self.path:
                self.load(self.path)


class Manager:
    def __init__(self, app, cfg):
        self.app, self.cfg = app, cfg
        self.screens, self.host, self.paused, self._grab = [], None, False, None
        self.tray = QSystemTrayIcon(self._icon(), app)
        self.tray.setToolTip("Live Wallpaper")
        self._build_menu()
        self.tray.show()
        if cfg["autostart"] and cfg["task_cmd"] != " ".join(autostart_parts()):
            self.register_startup()
        QTimer.singleShot(100, self.start)
        QTimer.singleShot(20000, lambda: set_priority(PRIO_NORMAL))   # boot finished
        self.timer = QTimer()
        self.timer.timeout.connect(self._watchdog)
        self.timer.start(5000)

    # ---- tray
    @staticmethod
    def _icon():
        pm = QPixmap(64, 64)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#4f8cff"))
        p.drawRoundedRect(4, 8, 56, 48, 10, 10)
        p.setBrush(QColor("white"))
        p.drawPolygon(QPolygon([QPoint(26, 22), QPoint(26, 42), QPoint(44, 32)]))
        p.end()
        return QIcon(pm)

    def _build_menu(self):
        m = self.menu = QMenu()
        m.addAction("Choose video...", self.choose_video)
        self.act_pause = m.addAction("Pause", self.toggle_pause)
        for text, key in (("Mute", "muted"),
                          ("Start with Windows", "autostart"),
                          ("Use video frame as static wallpaper", "static_frame"),
                          ("Compatibility mode (restarts app)", "compat")):
            a = QAction(text, m)
            a.setCheckable(True)
            a.setChecked(self.cfg[key])
            a.toggled.connect(lambda v, k=key: self.set_flag(k, v))
            m.addAction(a)
        m.addSeparator()
        m.addAction("Quit", self.quit)
        self.tray.setContextMenu(m)

    def notify(self, text):
        self.tray.showMessage("Live Wallpaper", text)

    # ---- actions
    def choose_video(self):
        f, _ = QFileDialog.getOpenFileName(
            None, "Choose wallpaper video", str(Path.home() / "Videos"),
            "Video (*.mp4 *.mkv *.webm *.avi *.mov *.wmv)")
        if f:
            self.cfg["video"] = f
            save_cfg(self.cfg)
            self.start()
            self.grab_still(f)

    def toggle_pause(self):
        self.paused = not self.paused
        for s in self.screens:
            s.player.pause() if self.paused else s.player.play()
        self.act_pause.setText("Resume" if self.paused else "Pause")

    def set_flag(self, key, value):
        self.cfg[key] = value
        save_cfg(self.cfg)
        if key == "muted":
            for s in self.screens:
                s.set_muted(value)
        elif key == "autostart":
            self.register_startup()
        elif key == "static_frame" and value and FRAME_FILE.exists():
            set_static_wallpaper(FRAME_FILE)
        elif key == "compat":
            restart_self()

    def register_startup(self):
        if self.cfg["autostart"]:
            if set_autostart(True):
                self.cfg["task_cmd"] = " ".join(autostart_parts())
        else:
            set_autostart(False)
            self.cfg["task_cmd"] = ""
        save_cfg(self.cfg)

    def quit(self):
        self._clear()
        self.tray.hide()
        self.app.quit()

    # ---- wallpaper lifecycle
    def _clear(self):
        for s in self.screens:
            s.player.stop()
            s.close()
            s.deleteLater()
        self.screens = []

    def start(self):
        self._clear()
        video = self.cfg["video"]
        if not (video and os.path.exists(video)):
            self.notify("Right-click the tray icon and choose a video to begin.")
            return
        host, wp_worker = find_desktop_host()
        if not host:
            self.notify("Could not find the desktop window.")
            return
        self.host = host
        for i, rect in enumerate(get_monitors()):
            s = Screen(rect, i == 0)
            s.set_muted(self.cfg["muted"])
            s.show()
            attach_to_desktop(int(s.winId()), host, wp_worker, rect)
            s.load(video)
            self.screens.append(s)
        self.paused = False
        self.act_pause.setText("Pause")
        if not FRAME_FILE.exists():
            self.grab_still(video)

    def grab_still(self, video):
        """Save one frame via a separate short-lived player, so the live
        wallpaper's decoder is never touched. Used as static/lock-screen image."""
        player, sink = QMediaPlayer(), QVideoSink()
        player.setVideoSink(sink)
        self._grab = (player, sink)
        seen = [0]

        def on_frame(frame):
            seen[0] += 1
            if player.position() < 800 and seen[0] < 90:
                return
            sink.videoFrameChanged.disconnect(on_frame)
            img = frame.toImage()
            player.stop()
            if not img.isNull():
                DIR.mkdir(parents=True, exist_ok=True)
                img.save(str(FRAME_FILE), "PNG")
                if self.cfg["static_frame"]:
                    set_static_wallpaper(FRAME_FILE)

        sink.videoFrameChanged.connect(on_frame)
        player.setSource(QUrl.fromLocalFile(video))
        player.play()
        QTimer.singleShot(10000, player.stop)

    def _watchdog(self):
        if not self.screens:
            return
        if len(get_monitors()) != len(self.screens) or not user32.IsWindow(self.host):
            self.start()                      # Explorer restarted / monitors changed
        elif not self.paused:
            for s in self.screens:
                s.ensure_playing()


def main():
    global MUTEX
    MUTEX = kernel32.CreateMutexW(None, False, f"Local\\{APP}")
    if ctypes.get_last_error() == 183:        # already running
        return
    set_priority(PRIO_HIGH)                   # fast start; lowered after boot
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    manager = Manager(app, CFG)               # noqa: F841  (keep reference)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
