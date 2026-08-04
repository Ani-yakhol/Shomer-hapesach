"""
keyboard_hook.py - חסימת מקשי מערכת ב-Windows
Computer Guardian - שומר המחשב

משתמש ב-SetWindowsHookEx עם WH_KEYBOARD_LL לחסימה ברמה נמוכה.

מאפשר:
- הקלדה רגילה (אותיות, מספרים, רווח, מחיקה, Tab, Enter)
- Alt+Shift — החלפת שפת מקלדת
- מקשי ניווט וסימני פיסוק
חוסם:
- מקשי Windows (LWin, RWin) + כל צירוף Win+X
- Alt+Tab, Alt+F4, Alt+Esc, Alt+F10
- Ctrl+Esc, Ctrl+Shift+Esc (Task Manager)
- Print Screen, Sleep
- F1 (Help)
"""

import ctypes
import ctypes.wintypes
import threading
import logging

logger = logging.getLogger(__name__)

# Windows constants
WH_KEYBOARD_LL  = 13
WM_KEYDOWN      = 0x0100
WM_KEYUP        = 0x0101
WM_SYSKEYDOWN   = 0x0104
WM_SYSKEYUP     = 0x0105
WM_QUIT         = 0x0012
HC_ACTION       = 0

LLKHF_ALTDOWN   = 0x00000020
LLKHF_INJECTED  = 0x00000010

# Virtual key codes
VK_LWIN     = 0x5B
VK_RWIN     = 0x5C
VK_ESCAPE   = 0x1B
VK_TAB      = 0x09
VK_F1       = 0x70
VK_F4       = 0x73
VK_F10      = 0x79
VK_F11      = 0x7A
VK_F12      = 0x7B
VK_APPS     = 0x5D   # Context menu key
VK_SNAPSHOT = 0x2C   # Print Screen
VK_CONTROL  = 0x11
VK_SHIFT    = 0x10
VK_MENU     = 0x12   # Alt key
VK_SLEEP    = 0x5F
VK_DELETE   = 0x2E

# מקשי F2-F12 (F1 כבר מוגדר למעלה)
VK_F2  = 0x71
VK_F3  = 0x72
VK_F5  = 0x74
VK_F6  = 0x75
VK_F7  = 0x76
VK_F8  = 0x77   # ← חסר — זו הייתה הסיבה לקריסה
VK_F9  = 0x78

# מפתחות שיחסמו תמיד (ללא קשר למודיפיירים)
# הערה: מקש ה-admin hotkey (ברירת מחדל F8) נתפס לפני בדיקה זו
ALWAYS_BLOCKED = frozenset({
    VK_LWIN, VK_RWIN,       # מקשי Windows — חוסם כל Win+X אוטומטית
    VK_APPS,                 # תפריט הקשר
    VK_SNAPSHOT,             # Print Screen
    VK_SLEEP,                # Sleep
    # F1-F12 — כולם חסומים (ה-admin hotkey נתפס קודם ולא יגיע לכאן)
    VK_F1, VK_F2, VK_F3, VK_F4,
    VK_F5, VK_F6, VK_F7, VK_F8,
    VK_F9, VK_F10, VK_F11, VK_F12,
})

# מפתחות שנחסמים כאשר Alt לחוץ
# הערה: VK_SHIFT אינו ברשימה — Alt+Shift מאפשר החלפת שפה!
ALT_BLOCKED = frozenset({
    VK_TAB,     # Alt+Tab  — מעבר חלונות
    VK_F4,      # Alt+F4   — סגירת חלון
    VK_F10,     # Alt+F10  — תפריט
    VK_ESCAPE,  # Alt+Esc  — מיזעור חלון
})

# מפתחות שנחסמים כאשר Ctrl לחוץ
CTRL_BLOCKED = frozenset({
    VK_ESCAPE,  # Ctrl+Esc      — תפריט התחל
    VK_F4,      # Ctrl+F4       — סגירת Tab/חלון
})


class KBDLLHOOKSTRUCT(ctypes.Structure):
    """מבנה נתוני ה-hook של לוח המקשים ב-Windows"""
    _fields_ = [
        ("vkCode",      ctypes.wintypes.DWORD),
        ("scanCode",    ctypes.wintypes.DWORD),
        ("flags",       ctypes.wintypes.DWORD),
        ("time",        ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


# ── תיקון קריטי: LRESULT ב-Windows 64-bit הוא 64-bit ──
# HOOKPROC עם c_int גורם לכך שהגרסה ה-64-bit של RAX מכילה זבל,
# ו-Windows מפרש כל return כ"חסום" — שום מקש לא עובר.
LRESULT = ctypes.c_longlong   # LRESULT = LONG_PTR = 64-bit ב-x64

HOOKPROC = ctypes.WINFUNCTYPE(
    LRESULT,                    # ← חייב LRESULT, לא c_int!
    ctypes.c_int,
    ctypes.wintypes.WPARAM,
    ctypes.wintypes.LPARAM,
)

# הגדרת restype נכון ל-CallNextHookEx
_user32 = ctypes.windll.user32
_user32.CallNextHookEx.restype  = LRESULT
_user32.CallNextHookEx.argtypes = [
    ctypes.c_void_p,
    ctypes.c_int,
    ctypes.wintypes.WPARAM,
    ctypes.wintypes.LPARAM,
]


class KeyboardBlocker:
    """
    חוסם מקשי מערכת ב-Windows באמצעות Low-Level Keyboard Hook.

    מאפשר:
    - הקלדה רגילה בתיבות טקסט (אותיות, מספרים, Backspace, Enter...)
    - Alt+Shift — החלפת שפת מקלדת
    - צירוף מקשים אחד להגדרה (ברירת מחדל: F8) לכניסת מנהל

    חוסם:
    - מקש Windows (+ כל Win+X)
    - Alt+Tab, Alt+F4, Alt+Esc
    - Ctrl+Esc (תפריט התחל), Ctrl+Shift+Esc (Task Manager)
    - Print Screen, Sleep
    """

    def __init__(
        self,
        admin_hotkey_callback=None,
        admin_hotkey: str = "F8",
        admin_vk: int = None,
        admin_modifiers: list = None,
    ):
        self.admin_hotkey_callback = admin_hotkey_callback

        # תמיכה בשני סגנונות קריאה: admin_hotkey="F8" או admin_vk=0x77
        if admin_vk is not None:
            self.admin_vk = admin_vk
        else:
            hotkey_vk_map = {
                "F5": 0x74, "F6": 0x75, "F7": 0x76, "F8": 0x77,
                "F9": 0x78, "F10": 0x79,
            }
            self.admin_vk = hotkey_vk_map.get(admin_hotkey, 0x77)  # ברירת מחדל F8

        self.admin_modifiers = set(admin_modifiers or [])   # ריק = ללא מודיפיירים

        self._hook   = None
        self._thread: threading.Thread | None = None
        self._active = False

        # חייב לשמור reference כדי למנוע GC
        self._hook_proc = HOOKPROC(self._low_level_handler)

    def _get_modifier_state(self) -> dict:
        user32 = ctypes.windll.user32
        return {
            "ctrl":  bool(user32.GetAsyncKeyState(VK_CONTROL) & 0x8000),
            "shift": bool(user32.GetAsyncKeyState(VK_SHIFT)   & 0x8000),
            "alt":   bool(user32.GetAsyncKeyState(VK_MENU)    & 0x8000),
        }

    def _low_level_handler(self, nCode: int, wParam: int, lParam: int) -> int:
        """
        ה-callback של ה-hook.
        מחזיר LRESULT(1) = חוסם את המקש.
        מחזיר CallNextHookEx = מעביר הלאה.
        """
        if nCode < HC_ACTION or not self._active:
            return _user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

        try:
            kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            vk         = kb.vkCode
            flags      = kb.flags
            is_keydown = wParam in (WM_KEYDOWN, WM_SYSKEYDOWN)
            alt_down   = bool(flags & LLKHF_ALTDOWN)

            mods = self._get_modifier_state()

            # ── Alt+Shift מאפשר — החלפת שפת מקלדת ──
            if alt_down and vk == VK_SHIFT:
                return _user32.CallNextHookEx(self._hook, nCode, wParam, lParam)
            if mods["shift"] and vk == VK_MENU:
                return _user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

            # ── בדיקת hotkey מנהל (רק על keydown) ──
            if is_keydown and self.admin_hotkey_callback:
                if vk == self.admin_vk:
                    mods_ok = all(mods.get(m, False) for m in self.admin_modifiers) \
                              if self.admin_modifiers else True
                    if mods_ok:
                        threading.Thread(
                            target=self.admin_hotkey_callback, daemon=True
                        ).start()
                        return LRESULT(1)

            # ── חסימת מקשי Windows תמיד ──
            if vk in ALWAYS_BLOCKED:
                return LRESULT(1)

            # ── חסימת Alt+X (למעט Alt+Shift שטופל למעלה) ──
            if alt_down and vk in ALT_BLOCKED:
                return LRESULT(1)

            # ── חסימת Ctrl+X ──
            if mods["ctrl"] and vk in CTRL_BLOCKED:
                return LRESULT(1)

            # ── חסימת Ctrl+Shift+Esc (Task Manager) ──
            if mods["ctrl"] and mods["shift"] and vk == VK_ESCAPE:
                return LRESULT(1)

            # ── חסימת Ctrl+Alt+Del ──
            if mods["ctrl"] and alt_down and vk == VK_DELETE:
                return LRESULT(1)

        except Exception as e:
            logger.error(f"שגיאה ב-hook: {e}")

        return _user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

    def start(self):
        """מפעיל את חסימת המקשים ב-thread נפרד עם message pump"""
        if self._active:
            return
        self._active = True

        def _run():
            try:
                # WH_KEYBOARD_LL הוא hook ברמה נמוכה — hmod חייב להיות NULL
                self._hook = ctypes.windll.user32.SetWindowsHookExW(
                    WH_KEYBOARD_LL,
                    self._hook_proc,
                    None,   # NULL — נדרש עבור WH_KEYBOARD_LL (לא DLL)
                    0,
                )
                if not self._hook:
                    err = ctypes.windll.kernel32.GetLastError()
                    logger.error(f"SetWindowsHookExW נכשל, שגיאה: {err}")
                    return

                logger.info("Keyboard hook הופעל")

                msg = ctypes.wintypes.MSG()
                while self._active:
                    ret = ctypes.windll.user32.GetMessageW(
                        ctypes.byref(msg), None, 0, 0
                    )
                    if ret <= 0:
                        break
                    ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
                    ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))

            finally:
                if self._hook:
                    ctypes.windll.user32.UnhookWindowsHookEx(self._hook)
                    self._hook = None
                logger.info("Keyboard hook הוסר")

        self._thread = threading.Thread(target=_run, name="KeyboardHook", daemon=True)
        self._thread.start()

    def stop(self):
        """עוצר את ה-hook"""
        self._active = False
        if self._thread and self._thread.ident:
            try:
                ctypes.windll.user32.PostThreadMessageW(
                    self._thread.ident, WM_QUIT, 0, 0
                )
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=2.0)
        self._thread = None

    def pause(self):
        """מפסיק זמנית את החסימה"""
        self._active = False

    def resume(self):
        """ממשיך את החסימה"""
        self._active = True
