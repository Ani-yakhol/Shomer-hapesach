"""
lock_screen.py - מסך נעילה
שומר הפתח v0.0.9

כניסת מנהל: F8 (ניתן לשינוי) → דיאלוג סיסמה בלבד.
אין כפתור מנהל גלוי. אין ציון צירוף מקשים.
"""
import ctypes
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QHBoxLayout, QFrame, QApplication, QGraphicsDropShadowEffect,
    QDialog, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve, QPoint
from PyQt6.QtGui import QColor, QKeyEvent, QPixmap, QPalette, QBrush, QPainter
from styles import get_lockscreen_style


# ── חישוב תאריך עברי (fallback כש-hdate לא מותקן) ─────────────────
_HEB_MONTHS = [
    "", "תשרי", "חשון", "כסלו", "טבת", "שבט",
    "אדר", "ניסן", "אייר", "סיון", "תמוז", "אב", "אלול",
    "אדר א׳", "אדר ב׳",
]
_HEB_UNITS = [
    "", "א", "ב", "ג", "ד", "ה", "ו", "ז", "ח", "ט",
    "י", "יא", "יב", "יג", "יד", "טו", "טז", "יז", "יח", "יט",
    "כ", "כא", "כב", "כג", "כד", "כה", "כו", "כז", "כח", "כט", "ל",
]
_HEB_TENS  = ["", "י", "כ", "ל", "מ", "נ", "ס", "ע", "פ", "צ"]
_HEB_HUNDS = ["", "ק", "ר", "ש", "ת", "תק", "תר", "תש", "תת", "תתק"]


def _to_heb_year(n: int) -> str:
    """ממיר מספר שנה (mod 1000) לאותיות עבריות עם גרשיים."""
    r, h, t, u = "", n // 100, (n % 100) // 10, n % 10
    r += _HEB_HUNDS[h] if h < len(_HEB_HUNDS) else ""
    tens_unit = t * 10 + u
    if tens_unit == 15: r += "טו"
    elif tens_unit == 16: r += "טז"
    else:
        if t: r += _HEB_TENS[t] if t < len(_HEB_TENS) else ""
        if u: r += _HEB_UNITS[u] if u < len(_HEB_UNITS) else str(u)
    if len(r) > 1:
        return r[:-1] + '״' + r[-1]
    return (r + "׳") if r else ""


def _gregorian_to_hebrew_str(dt: datetime) -> str:
    """ממיר תאריך לועזי לתאריך עברי. דיוק מלא לפי אלגוריתם Dershowitz & Reingold."""
    y, m, d = dt.year, dt.month, dt.day
    # Julian Day Number
    a = (14 - m) // 12
    yr = y + 4800 - a
    mr = m + 12 * a - 3
    jdn = d + (153*mr+2)//5 + 365*yr + yr//4 - yr//100 + yr//400 - 32045
    # JDN → עברי
    c = jdn + 32082
    d1 = (4*c+3)//1461
    d2 = c - (1461*d1)//4
    m1 = (5*d2+2)//153
    day_h   = d2 - (153*m1+2)//5 + 1
    month_h = m1 + (1 if m1 < 10 else -9)
    year_h  = d1 - 4716 + (1 if m1 < 10 else 0)
    # שנה מעוברת — אדר א/ב
    leap = ((7*year_h+1) % 19) < 7
    if month_h == 6 and leap:
        month_h = 14  # אדר א׳
    day_str   = _HEB_UNITS[day_h] if 0 < day_h < len(_HEB_UNITS) else str(day_h)
    month_str = _HEB_MONTHS[month_h] if 0 < month_h < len(_HEB_MONTHS) else ""
    year_str  = _to_heb_year(year_h % 1000)
    return f"{day_str} {month_str} {year_str}"


def set_taskbar_visible(visible: bool):
    try:
        F, S = ctypes.windll.user32.FindWindowW, ctypes.windll.user32.ShowWindow
        h = F("Shell_TrayWnd", None)
        if h: S(h, 5 if visible else 0)
        h2 = F("Windows.UI.Core.CoreWindow", "Windows Shell Experience Host")
        if h2: S(h2, 5 if visible else 0)
    except: pass


def bring_to_front(hwnd):
    try:
        ctypes.windll.user32.SetForegroundWindow(hwnd)
        ctypes.windll.user32.BringWindowToTop(hwnd)
    except: pass


def _close_start_menu():
    """
    סוגר את תפריט התחל אם נפתח — עובד ב-Windows 10/11.
    מחפש את חלונות StartMenu/StartUI ומסתיר אותם.
    """
    try:
        user32 = ctypes.windll.user32
        SW_HIDE = 0

        # Windows 10 — "DV2ControlHost" / "Windows.UI.Core.CoreWindow"
        start_classes = [
            "Windows.UI.Core.CoreWindow",   # Start menu Win10/11
            "DV2ControlHost",               # Start menu legacy
            "Shell_TrayWnd",                # Taskbar (כבר מוסתר, אבל בטוח)
        ]
        # שם החלון של תפריט התחל ב-Windows 11
        start_titles = ["Start", "תפריט התחל", "Cortana"]

        def _enum_callback(hwnd, _):
            if not user32.IsWindowVisible(hwnd):
                return True
            cls_buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, cls_buf, 256)
            cls = cls_buf.value
            if any(sc in cls for sc in ["Windows.UI.Core", "DV2Control"]):
                title_buf = ctypes.create_unicode_buffer(256)
                user32.GetWindowTextW(hwnd, title_buf, 256)
                title = title_buf.value
                if any(t in title for t in start_titles) or not title:
                    # שלח Escape לחלון התפריט לפני הסתרה
                    WM_KEYDOWN = 0x0100; VK_ESCAPE = 0x1B
                    user32.PostMessageW(hwnd, WM_KEYDOWN, VK_ESCAPE, 0)
            return True

        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
        user32.EnumWindows(EnumWindowsProc(_enum_callback), 0)
    except Exception:
        pass


# ── דיאלוג סיסמת מנהל מהירה (F8) ────────────────────────────────

class QuickAdminDialog(QDialog):
    """חלונית קטנה להקשת סיסמת מנהל בלבד (F8)"""

    def __init__(self, config_manager, dark=False, parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.WindowStaysOnTopHint)
        self.cm   = config_manager
        self.dark = dark
        self.setStyleSheet(get_lockscreen_style(dark))
        self.setMinimumHeight(240)
        self.setFixedWidth(340)
        self._center()
        self._build()

    def _center(self):
        s = QApplication.primaryScreen().geometry()
        self.move((s.width()-320)//2, (s.height()-220)//2)

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0,0,0,0)

        card = QFrame(); card.setObjectName("LoginCard")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(28,24,28,24); cl.setSpacing(12)
        cl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        ttl = QLabel("כניסת מנהל מערכת")
        ttl.setObjectName("LockTitle")
        ttl.setStyleSheet("font-size:17px;")
        ttl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(ttl)

        lbl = QLabel("סיסמת ניהול:")
        lbl.setObjectName("InputLabel")
        lbl.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        cl.addWidget(lbl)

        self._pwd = QLineEdit()
        self._pwd.setObjectName("LoginInput")
        self._pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self._pwd.setPlaceholderText("הכנס סיסמת מנהל")
        self._pwd.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._pwd.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._pwd.returnPressed.connect(self._try)
        cl.addWidget(self._pwd)

        self._err = QLabel("")
        self._err.setObjectName("ErrorLabel")
        self._err.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._err.hide()
        cl.addWidget(self._err)

        row = QHBoxLayout(); row.setSpacing(8)
        ok = QPushButton("כניסה ◀"); ok.setObjectName("LoginBtn")
        ok.clicked.connect(self._try); row.addWidget(ok)
        cancel = QPushButton("ביטול"); cancel.setObjectName("NightBtn")
        cancel.clicked.connect(self.reject); row.addWidget(cancel)
        cl.addLayout(row)

        root.addWidget(card)
        root.addStretch(0)
        QTimer.singleShot(100, self._pwd.setFocus)

    def _try(self):
        p = self._pwd.text()
        if self.cm.verify_admin_password(p):
            self.accept()
        else:
            self._err.setText("סיסמה שגויה")
            self._err.show()
            self._pwd.clear()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape: self.reject()
        else: super().keyPressEvent(e)


# ══════════════════════════════════════════════════════════════════

class LangToggle(QFrame):
    """
    תצוגת שפת מקלדת נוכחית — Status בלבד.
    מציג את השפה הנוכחית, מתעדכן בזמן אמת.
    אינו לחיץ (לא ניתן לשנות דרכו — רק דרך מקשי המחשב).
    """
    lang_changed = pyqtSignal(str)   # נשמר לתאימות אחורית

    MODES = [
        ("HE",      "עברית"),
        ("EN",      "English"),
        ("EN_CAPS", "ENGLISH"),
    ]

    def __init__(self, dark=False, parent=None):
        super().__init__(parent)
        self.dark = dark
        self._current = "HE"
        self._build()

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        icon_lbl = QLabel("⌨")
        icon_lbl.setStyleSheet("font-size:14px; padding:0 6px 0 0;")
        layout.addWidget(icon_lbl)

        self._status_lbl = QLabel("עברית")
        self._status_lbl.setStyleSheet(
            "font-size:13px; font-weight:600; padding:4px 12px;"
            "border:1.5px solid rgba(128,128,128,0.3); border-radius:8px;"
            f"color:{'#58a6ff' if self.dark else '#2563eb'};"
            f"background:{'rgba(56,139,253,0.12)' if self.dark else 'rgba(37,99,235,0.08)'};"
            "font-family:'Segoe UI','Arial Hebrew',sans-serif;"
        )
        layout.addWidget(self._status_lbl)

    def set_current(self, mode: str):
        """עדכון תצוגת השפה הנוכחית"""
        if mode == self._current:
            return
        self._current = mode
        labels = {"HE": "עברית", "EN": "English", "EN_CAPS": "ENGLISH"}
        self._status_lbl.setText(labels.get(mode, mode))

    @staticmethod
    def detect_current_lang() -> str:
        """
        קורא את שפת המקלדת הנוכחית.
        Caps Lock פעיל + כל שפה → EN_CAPS (אותיות גדולות).
        עברית בלבד (ללא Caps) → HE.
        """
        try:
            user32  = ctypes.windll.user32
            hwnd    = user32.GetForegroundWindow()
            tid     = user32.GetWindowThreadProcessId(hwnd, None)
            hkl     = user32.GetKeyboardLayout(tid)
            lang_id = hkl & 0xFFFF
            VK_CAPITAL = 0x14
            caps_on = bool(user32.GetKeyState(VK_CAPITAL) & 1)

            LANG_ID_MAP = {
                0x040D: "HE", 0x080D: "HE",
                0x0409: "EN", 0x0809: "EN", 0x0C09: "EN",
            }
            base = LANG_ID_MAP.get(lang_id, "EN")

            # Caps Lock פעיל בכל שפה → ENGLISH (אותיות גדולות)
            if caps_on:
                return "EN_CAPS"
            return base
        except Exception:
            return "HE"


# ══════════════════════════════════════════════════════════════════

class LockScreen(QWidget):
    login_success   = pyqtSignal(str)   # username
    admin_requested = pyqtSignal()

    def __init__(self, config_manager, dark=False, show_remaining="", parent=None):
        super().__init__(parent)
        self.cm             = config_manager
        self.dark           = dark
        self.show_remaining = show_remaining
        self._failed        = 0
        self._locked_until  = None
        self._lock_timer    = QTimer()
        self._lock_timer.timeout.connect(self._check_lockout)

        ls_cfg = config_manager.get_lock_screen_cfg()
        self._admin_hotkey = ls_cfg.get("admin_hotkey", "F8")

        self._setup_window()
        self._build_ui()
        self._apply_style()
        self._start_clock()

        self._focus_timer = QTimer()
        self._focus_timer.setInterval(350)   # מהיר יותר — לזיהוי תפריט התחל
        self._focus_timer.timeout.connect(self._ensure_focus)
        self._focus_timer.start()

    def _setup_window(self):
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        self.setObjectName("LockScreen")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.showFullScreen()

    def _apply_background(self):
        ls = self.cm.get_lock_screen_cfg()
        bg_image = ls.get("bg_image", "").strip()
        bg_color = ls.get("bg_color", "").strip()
        bg_fit   = ls.get("bg_fit", "fill")

        self._bg_pixmap = None  # איפוס

        if bg_image:
            pix = QPixmap(bg_image)
            if not pix.isNull():
                screen = QApplication.primaryScreen().geometry()
                if bg_fit in ("fill", "stretch"):
                    pix = pix.scaled(screen.width(), screen.height(),
                                     Qt.AspectRatioMode.IgnoreAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation)
                elif bg_fit == "fit":
                    pix = pix.scaled(screen.width(), screen.height(),
                                     Qt.AspectRatioMode.KeepAspectRatio,
                                     Qt.TransformationMode.SmoothTransformation)
                elif bg_fit == "center":
                    pass  # לא מקטינים — מרכזים ב-paintEvent
                self._bg_pixmap  = pix
                self._bg_fit     = bg_fit
                self._bg_color_fallback = None
                # שקיפות כדי שה-paintEvent יציג
                self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
                self.setAutoFillBackground(False)
                # הסרת רקע מ-stylesheet
                self.setStyleSheet(
                    self.styleSheet() +
                    "\nQWidget#LockScreen { background: transparent; }"
                )
                self.update()
                return

        if bg_color:
            self._bg_pixmap = None
            self._bg_color_fallback = bg_color
            self.setStyleSheet(
                self.styleSheet() +
                f"\nQWidget#LockScreen {{ background: {bg_color}; }}"
            )
            self.update()
            return

    def paintEvent(self, event):
        """ציור רקע מותאם אישית לפני כל ילד אחר"""
        super().paintEvent(event)
        pix = getattr(self, "_bg_pixmap", None)
        if pix and not pix.isNull():
            from PyQt6.QtGui import QPainter
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            fit = getattr(self, "_bg_fit", "fill")
            if fit == "center":
                # מרכז ללא שינוי גודל
                x = (self.width()  - pix.width())  // 2
                y = (self.height() - pix.height()) // 2
                painter.drawPixmap(x, y, pix)
            else:
                painter.drawPixmap(self.rect(), pix)
            painter.end()

    def _ensure_focus(self):
        """שמר פוקוס ועצור את תפריט התחל אם נפתח"""
        if not self.isVisible():
            return
        # הסתר חלון תפריט התחל אם נפתח
        _close_start_menu()
        if not self.isActiveWindow():
            self.activateWindow(); self.raise_()
            try: bring_to_front(int(self.winId()))
            except: pass

    # ── UI ────────────────────────────────────────────────────────
    def _build_ui(self):
        ls = self.cm.get_lock_screen_cfg()
        show_ads = ls.get("show_ads", False)
        show_reg = ls.get("show_self_register", False)

        root = QHBoxLayout(self)
        root.setContentsMargins(0,0,0,0)
        root.setSpacing(0)

        # ── עמודה ראשית ──
        main_col = QVBoxLayout()
        main_col.setContentsMargins(0,0,0,0)

        # שורה עליונה — שעון בלבד (ללא כפתור מצב לילה)
        top = QHBoxLayout()
        top.setContentsMargins(32,24,32,0)
        top.addStretch()

        clk_col = QVBoxLayout(); clk_col.setSpacing(2)
        self._clock_lbl = QLabel("00:00"); self._clock_lbl.setObjectName("LockClock")
        self._clock_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        clk_col.addWidget(self._clock_lbl)
        self._date_lbl = QLabel(""); self._date_lbl.setObjectName("LockDate")
        self._date_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        clk_col.addWidget(self._date_lbl)
        top.addLayout(clk_col)

        top.addStretch()
        main_col.addLayout(top)
        main_col.addStretch()

        # כרטיס כניסה — מיקום לפי הגדרות
        center = QHBoxLayout()
        ml = ls.get("login_margin_left")
        if ml is not None and ml >= 0:
            center.addSpacing(ml)
        else:
            center.addStretch()
        card = QFrame(); card.setObjectName("LoginCard"); card.setFixedWidth(390)
        # החל עיצוב מותאם אישית לתיבת כניסה
        _card_transparent = ls.get("card_bg_transparent", False)
        _card_bg          = ls.get("card_bg_color", "")
        _card_border_col  = ls.get("card_border_color", "")
        _card_border_w    = ls.get("card_border_width", 1)
        if _card_transparent:
            card.setStyleSheet("QFrame#LoginCard{background:transparent;border:none;}")
        elif _card_bg or _card_border_col or _card_border_w != 1:
            bg_val     = _card_bg or "rgba(255,255,255,0.93)"
            border_col = _card_border_col or "rgba(200,215,240,0.9)"
            card.setStyleSheet(
                f"QFrame#LoginCard{{background:{bg_val};"
                f"border:{_card_border_w}px solid {border_col};border-radius:20px;}}"
            )
        sh = QGraphicsDropShadowEffect()
        sh.setBlurRadius(50); sh.setColor(QColor(0,0,0,80)); sh.setOffset(0,10)
        card.setGraphicsEffect(sh)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(38,36,38,36); cl.setSpacing(14)
        cl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("🖥️"); icon.setStyleSheet("font-size:42px;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter); cl.addWidget(icon)

        ttl = QLabel("שומר הפתח"); ttl.setObjectName("LockTitle")
        ttl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ttl.setLayoutDirection(Qt.LayoutDirection.RightToLeft); cl.addWidget(ttl)

        if self.show_remaining:
            rl = QLabel(self.show_remaining)
            rl.setStyleSheet("color:#22c55e;font-size:13px;font-weight:600;"
                             "background:rgba(34,197,94,0.10);"
                             "border:1px solid rgba(34,197,94,0.25);"
                             "border-radius:7px;padding:6px 12px;"
                             "font-family:'Segoe UI','Arial Hebrew',sans-serif;")
            rl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            rl.setWordWrap(True); cl.addWidget(rl)

        # הודעת חסימה כללית
        self._block_msg_lbl = QLabel("")
        self._block_msg_lbl.setStyleSheet(
            "color:#ef4444;font-size:13px;font-weight:700;"
            "background:rgba(239,68,68,0.10);border:1px solid rgba(239,68,68,0.3);"
            "border-radius:7px;padding:8px 12px;"
            "font-family:'Segoe UI','Arial Hebrew',sans-serif;"
        )
        self._block_msg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._block_msg_lbl.setWordWrap(True)
        self._block_msg_lbl.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._block_msg_lbl.hide()
        cl.addWidget(self._block_msg_lbl)
        QTimer.singleShot(100, self._update_block_msg)

        cl.addSpacing(4)

        ul = QLabel("שם משתמש"); ul.setObjectName("InputLabel")
        ul.setLayoutDirection(Qt.LayoutDirection.RightToLeft); cl.addWidget(ul)
        self._user_inp = QLineEdit()
        self._user_inp.setObjectName("LoginInput")
        self._user_inp.setPlaceholderText("הכנס שם משתמש")
        self._user_inp.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._user_inp.setAlignment(Qt.AlignmentFlag.AlignAbsolute | Qt.AlignmentFlag.AlignRight)
        self._user_inp.setMaxLength(50); cl.addWidget(self._user_inp)

        pl = QLabel("סיסמה"); pl.setObjectName("InputLabel")
        pl.setLayoutDirection(Qt.LayoutDirection.RightToLeft); cl.addWidget(pl)
        self._pwd_inp = QLineEdit()
        self._pwd_inp.setObjectName("LoginInput")
        self._pwd_inp.setEchoMode(QLineEdit.EchoMode.Password)
        self._pwd_inp.setPlaceholderText("הכנס סיסמה")
        self._pwd_inp.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._pwd_inp.setAlignment(Qt.AlignmentFlag.AlignAbsolute | Qt.AlignmentFlag.AlignRight)
        self._pwd_inp.setMaxLength(128)
        self._pwd_inp.returnPressed.connect(self._on_login); cl.addWidget(self._pwd_inp)

        # חיבור: Enter בשדה שם משתמש → עבור לשדה סיסמה
        self._user_inp.returnPressed.connect(self._pwd_inp.setFocus)

        # ── מתג שפת מקלדת ──
        self._lang_toggle = LangToggle(dark=self.dark, parent=self)
        self._lang_toggle.lang_changed.connect(self._on_lang_selected)
        cl.addWidget(self._lang_toggle, 0, Qt.AlignmentFlag.AlignCenter)

        self._err_lbl = QLabel(""); self._err_lbl.setObjectName("ErrorLabel")
        self._err_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._err_lbl.setWordWrap(True)
        self._err_lbl.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._err_lbl.hide(); cl.addWidget(self._err_lbl)

        self._login_btn = QPushButton("כניסה למחשב  ←")
        self._login_btn.setObjectName("LoginBtn")
        self._login_btn.clicked.connect(self._on_login)
        self._login_btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        cl.addWidget(self._login_btn)

        # הרשמה עצמאית
        if show_reg:
            reg_lbl = QLabel('<a href="#" style="color:#3d7bd6;">אין לך חשבון? פתח חשבון חדש</a>')
            reg_lbl.setOpenExternalLinks(False)
            reg_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
            reg_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            reg_lbl.linkActivated.connect(self._open_register)
            cl.addWidget(reg_lbl)

        center.addWidget(card, 0, Qt.AlignmentFlag.AlignCenter)
        mr = ls.get("login_margin_right")
        if mr is not None and mr >= 0:
            center.addSpacing(mr)
        else:
            center.addStretch()
        # מרחק אנכי
        mt = ls.get("login_margin_top")
        mb = ls.get("login_margin_bottom")
        if mt is not None and mt >= 0:
            main_col.addSpacing(mt)
        main_col.addLayout(center)
        if mb is not None and mb >= 0:
            main_col.addSpacing(mb)
        main_col.addStretch()

        # footer — ללא תצוגת שפה (המתג מוצג בכרטיס)
        footer_row = QHBoxLayout(); footer_row.setContentsMargins(24,0,24,0)
        footer_lbl = QLabel("שומר הפתח • v0.0.10")
        footer_lbl.setObjectName("FooterLabel")
        footer_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_row.addStretch()
        footer_row.addWidget(footer_lbl)
        footer_row.addStretch()
        main_col.addLayout(footer_row); main_col.addSpacing(14)

        root.addLayout(main_col, 1)

        # ── פאנל פרסומות (ימין) ──
        if show_ads:
            ads_w = ls.get("ads_width", 300)
            self._ads_panel = self._build_ads_panel(ls, ads_w)
            root.addWidget(self._ads_panel)

        QTimer.singleShot(350, self._user_inp.setFocus)
        # קרא שפה נוכחית וסנכרן את המתג
        QTimer.singleShot(500, self._sync_lang_toggle)
        # החל רקע מותאם אישית
        QTimer.singleShot(100, self._apply_background)

    def _build_ads_panel(self, ls, width):
        ads_height  = ls.get("ads_height", 400) or 400
        show_arrows = ls.get("ads_show_arrows", True)
        img_fit     = ls.get("ads_img_fit", "fit")

        # מרחקי שוליים
        m_top    = ls.get("ads_margin_top",    0)
        m_bottom = ls.get("ads_margin_bottom",  0)
        m_left   = ls.get("ads_margin_left",    0)
        m_right  = ls.get("ads_margin_right",  16)

        # חבילת-חוץ — מרחקי שוליים
        outer = QWidget()
        outer.setFixedWidth(width + m_left + m_right)
        ol = QVBoxLayout(outer)
        ol.setContentsMargins(m_left, m_top, m_right, m_bottom)
        ol.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # מסגרת חיצונית שחורה — גדולה ב-2px מכל צד מהתוכן
        border_frame = QFrame()
        border_frame.setFixedWidth(width + 4)   # +4 = 2px בכל צד
        border_frame.setFixedHeight(ads_height + 4)
        border_frame.setStyleSheet(
            "QFrame { background:transparent; border:2px solid black; border-radius:0px; }"
        )
        border_layout = QVBoxLayout(border_frame)
        border_layout.setContentsMargins(2, 2, 2, 2)   # 2px padding = תוכן בתוך הגבול
        border_layout.setSpacing(0)

        # תיבת התוכן (תמונה) — StackedWidget כדי שחיצים יהיו overlay
        from PyQt6.QtWidgets import QStackedLayout
        ads_container = QWidget()
        ads_container.setFixedWidth(width)
        ads_container.setFixedHeight(ads_height)

        self._ads_images  = ls.get("ads_images", [])
        self._ads_idx     = 0
        self._ads_img_fit = img_fit

        # תמונה — תשכב מתחת
        self._ads_lbl = QLabel(ads_container)
        self._ads_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._ads_lbl.setGeometry(0, 0, width, ads_height)
        self._ads_lbl.setStyleSheet("background:white; border:none;")

        if show_arrows:
            # חצים בתוך התמונה — overlay ב-QLabel על גבי
            arrow_style = (
                "QPushButton {"
                "  background:transparent;"
                "  color:black;"
                "  font-size:22px; font-weight:900;"
                "  border:none;"
                "  text-shadow: -1px -1px 0 white, 1px -1px 0 white,"
                "               -1px 1px 0 white,  1px 1px 0 white;"  # מתאר לבן
                "}"
                "QPushButton:hover { color:#222; }"
            )
            arrow_h = 40
            arrow_y = ads_height - arrow_h - 4   # 4px מהתחתית

            self._prev_btn = QPushButton("❮", ads_container)
            self._prev_btn.setStyleSheet(arrow_style)
            self._prev_btn.setFixedSize(36, arrow_h)
            self._prev_btn.setGeometry(8, arrow_y, 36, arrow_h)
            self._prev_btn.clicked.connect(self._ads_prev)
            self._prev_btn.raise_()

            self._next_btn = QPushButton("❯", ads_container)
            self._next_btn.setStyleSheet(arrow_style)
            self._next_btn.setFixedSize(36, arrow_h)
            self._next_btn.setGeometry(width - 44, arrow_y, 36, arrow_h)
            self._next_btn.clicked.connect(self._ads_next)
            self._next_btn.raise_()

            # מונה — מרכז בתחתית
            self._ads_counter = QLabel("1 / 1", ads_container)
            self._ads_counter.setStyleSheet(
                "color:white; background:rgba(0,0,0,0.45); border-radius:4px;"
                "font-size:11px; padding:2px 8px; border:none;"
            )
            self._ads_counter.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._ads_counter.setFixedSize(60, 20)
            self._ads_counter.setGeometry(
                (width - 60) // 2, ads_height - 26, 60, 20
            )
            self._ads_counter.raise_()
        else:
            self._ads_counter = None

        border_layout.addWidget(ads_container)
        ol.addWidget(border_frame, 0, Qt.AlignmentFlag.AlignCenter)

        interval = ls.get("ads_interval", 5) * 1000
        self._ads_timer = QTimer(); self._ads_timer.setInterval(interval)
        self._ads_timer.timeout.connect(self._ads_next)
        if self._ads_images:
            self._show_ad(0); self._ads_timer.start()

        return outer

    def _show_ad(self, idx):
        if not self._ads_images: return
        path = self._ads_images[idx % len(self._ads_images)]
        pix  = QPixmap(path)
        if pix.isNull(): return
        fit = getattr(self, "_ads_img_fit", "fit")
        w   = self._ads_lbl.width()  or 280
        h   = self._ads_lbl.height() or 200
        if fit == "fill":
            pix = pix.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio,
                              Qt.TransformationMode.SmoothTransformation)
        elif fit == "stretch":
            pix = pix.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio,
                              Qt.TransformationMode.SmoothTransformation)
        else:
            pix = pix.scaled(w, h, Qt.AspectRatioMode.KeepAspectRatio,
                              Qt.TransformationMode.SmoothTransformation)
        self._ads_lbl.setPixmap(pix)
        if self._ads_counter:
            total = len(self._ads_images)
            self._ads_counter.setText(f"{idx+1} / {total}")

    def _ads_next(self):
        self._ads_idx = (self._ads_idx + 1) % max(1, len(self._ads_images))
        self._show_ad(self._ads_idx)

    def _ads_prev(self):
        self._ads_idx = (self._ads_idx - 1) % max(1, len(self._ads_images))
        self._show_ad(self._ads_idx)

    # ── שפת מקלדת ────────────────────────────────────────────────
    def _sync_lang_toggle(self):
        """מסנכרן את המתג לשפה האמיתית של המחשב"""
        mode = LangToggle.detect_current_lang()
        if hasattr(self, "_lang_toggle"):
            self._lang_toggle.set_current(mode)

    def _on_lang_selected(self, mode: str):
        """כשמשתמש לוחץ על מצב במתג — העברת פוקוס לשדה הטקסט"""
        QTimer.singleShot(80, self._user_inp.setFocus)

    def _update_lang(self):
        """מעדכן את המתג לשפה הנוכחית (נקרא כל שנייה)"""
        self._sync_lang_toggle()

    # ── שעון ──────────────────────────────────────────────────────
    def _start_clock(self):
        # החל צבע שעה/תאריך פעם אחת
        ls  = self.cm.get_lock_screen_cfg()
        clr = ls.get("clock_text_color", "")
        if clr:
            clk_style = (f"color:{clr};font-family:'Segoe UI',sans-serif;"
                         "font-size:52px;font-weight:200;letter-spacing:2px;")
            date_style = (f"color:{clr};font-family:'Segoe UI','Arial Hebrew',sans-serif;"
                          "font-size:15px;")
            self._clock_lbl.setStyleSheet(clk_style)
            self._date_lbl.setStyleSheet(date_style)

        self._update_clock()
        self._clock_timer = QTimer()
        self._clock_timer.setInterval(1000)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.timeout.connect(self._update_lang)
        self._clock_timer.start()

    def _update_clock(self):
        now = datetime.now()
        ls  = self.cm.get_lock_screen_cfg()

        # ── שעה ──
        fmt = ls.get("clock_time_format", "24")
        self._clock_lbl.setText(
            now.strftime("%I:%M %p") if fmt == "12" else now.strftime("%H:%M")
        )

        # ── צבע (מוגדר פעם אחת ב-_start_clock, לא מצטבר) ──

        # ── תאריך לועזי ──
        days_he   = ["שני","שלישי","רביעי","חמישי","שישי","שבת","ראשון"]
        months_he = ["","ינואר","פברואר","מרץ","אפריל","מאי","יוני",
                     "יולי","אוגוסט","ספטמבר","אוקטובר","נובמבר","דצמבר"]
        greg_str = f"יום {days_he[now.weekday()]}, {now.day} {months_he[now.month]} {now.year}"

        # ── תאריך עברי ──
        heb_str = self._get_hebrew_date(now)

        mode = ls.get("clock_date_mode", "both")
        if mode == "hebrew":
            self._date_lbl.setText(heb_str or greg_str)
        elif mode == "gregorian":
            self._date_lbl.setText(greg_str)
        else:   # both
            self._date_lbl.setText(f"{greg_str}  •  {heb_str}" if heb_str else greg_str)

    @staticmethod
    def _get_hebrew_date(dt: datetime) -> str:
        """מחזיר תאריך עברי מדויק כמחרוזת. מנסה hdate; fallback לחישוב ידני."""
        try:
            import hdate
            hd = hdate.HDate(datetime=dt)
            # hdate >= 1.0: hd.hebrew_date_str()  /  hdate < 1.0: str(hd)
            if hasattr(hd, 'hebrew_date_str'):
                return hd.hebrew_date_str()
            return str(hd)
        except ImportError:
            pass
        except Exception:
            pass
        # ── fallback: חישוב עברי ידני ──
        try:
            return _gregorian_to_hebrew_str(dt)
        except Exception:
            return ""

    # ── כניסה ─────────────────────────────────────────────────────
    def _on_login(self):
        if self._locked_until:
            rem = (self._locked_until - datetime.now()).total_seconds()
            if rem > 0:
                self._show_err(f"חסום ל-{int(rem)} שניות"); return
            self._locked_until = None; self._failed = 0

        username = self._user_inp.text().strip()
        password = self._pwd_inp.text()

        if not username:
            self._show_err("נא להכניס שם משתמש")
            self._shake(); return

        if not password:
            # אזהרת סיסמה — רק אם הסמן בשדה הסיסמה (לא ב-Enter על שם משתמש)
            self._show_err("נא להכניס סיסמה")
            self._pwd_inp.setFocus()
            self._shake(); return

        user = self.cm.verify_user(username, password)
        if user is None:
            self._failed += 1; self._pwd_inp.clear()
            if self._failed >= 5:
                import datetime as dt
                self._locked_until = dt.datetime.now() + dt.timedelta(seconds=30)
                self._show_err("יותר מדי ניסיונות — חסום ל-30 שניות")
                self._lock_timer.start(1000)
            else:
                self._show_err(f"שם משתמש או סיסמה שגויים ({5-self._failed} נותרו)")
            self._shake(); return

        # בדיקת חסימה כללית (לא מנהל)
        if not (user.get("is_admin")):
            from datetime import datetime as _dt
            for block in self.cm.config.get("global_blocks", []):
                if self.cm._matches_block(block, _dt.now()):
                    self._show_err("⛔  המחשב חסום כעת לשימוש")
                    self._shake(); return

        blocked, reason = self.cm.is_user_blocked_now(username)
        if blocked:
            self._show_err(f"גישה חסומה: {reason}"); self._shake(); return

        self._failed = 0; self._pwd_inp.clear(); self._hide_err()
        self.login_success.emit(username)

    def _check_lockout(self):
        if self._locked_until:
            rem = (self._locked_until - datetime.now()).total_seconds()
            if rem <= 0:
                self._locked_until = None; self._failed = 0
                self._lock_timer.stop(); self._hide_err()
            else:
                self._show_err(f"חסום ל-{int(rem)} שניות")

    # ── כניסת מנהל (F8) ──────────────────────────────────────────
    def _open_quick_admin(self):
        self._focus_timer.stop()
        dlg = QuickAdminDialog(self.cm, self.dark, parent=self)
        result = dlg.exec()
        self._focus_timer.start()
        if result == QDialog.DialogCode.Accepted:
            self.admin_requested.emit()

    # ── הרשמה עצמאית ─────────────────────────────────────────────
    def _open_register(self):
        from register_dialog import RegisterDialog
        dlg = RegisterDialog(self.cm, self.dark, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._show_err("החשבון נוצר בהצלחה! ניתן להתחבר עכשיו")

    # ── מקשים ────────────────────────────────────────────────────
    def keyPressEvent(self, event: QKeyEvent):
        key  = event.key()
        mods = event.modifiers()

        ctrl  = bool(mods & Qt.KeyboardModifier.ControlModifier)
        alt   = bool(mods & Qt.KeyboardModifier.AltModifier)
        shift = bool(mods & Qt.KeyboardModifier.ShiftModifier)
        win   = bool(mods & Qt.KeyboardModifier.MetaModifier)

        # ── Alt+Shift מותר — החלפת שפה ──
        if alt and shift and not ctrl and not win:
            super().keyPressEvent(event)
            # עדכן מתג אחרי החלפה (השהייה קצרה לתת לWindows להחליף)
            QTimer.singleShot(200, self._sync_lang_toggle)
            return

        # ── מקשים חסומים לחלוטין ──
        BLOCKED = {
            Qt.Key.Key_Super_L, Qt.Key.Key_Super_R,
            Qt.Key.Key_Meta,
            Qt.Key.Key_Escape,
            Qt.Key.Key_F1, Qt.Key.Key_F2, Qt.Key.Key_F3,
            Qt.Key.Key_F4, Qt.Key.Key_F11, Qt.Key.Key_F12,
            Qt.Key.Key_Print,
            Qt.Key.Key_Pause,
        }
        if key in BLOCKED:
            return

        if win: return
        if ctrl and alt: return
        if alt and key == Qt.Key.Key_F4: return
        if alt and key == Qt.Key.Key_Tab: return
        if ctrl and key == Qt.Key.Key_Escape: return
        if ctrl and shift and key == Qt.Key.Key_Escape: return
        if ctrl and key == Qt.Key.Key_F: return

        # hotkey מנהל (F8 ברירת מחדל)
        hotkey_map = {
            "F8":  Qt.Key.Key_F8,  "F9":  Qt.Key.Key_F9,
            "F10": Qt.Key.Key_F10, "F7":  Qt.Key.Key_F7,
            "F6":  Qt.Key.Key_F6,  "F5":  Qt.Key.Key_F5,
        }
        target_key = hotkey_map.get(self._admin_hotkey, Qt.Key.Key_F8)
        if key == target_key:
            self._open_quick_admin(); return

        if key == Qt.Key.Key_Tab:
            self._pwd_inp.setFocus() if self._user_inp.hasFocus() else self._user_inp.setFocus()
            return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self._user_inp.hasFocus():
                self._pwd_inp.setFocus()
            else:
                self._on_login()
            return

        super().keyPressEvent(event)

    # ── עיצוב ─────────────────────────────────────────────────────
    def _show_err(self, msg):
        self._err_lbl.setText(msg); self._err_lbl.show()

    def _hide_err(self):
        self._err_lbl.hide(); self._err_lbl.setText("")

    def _shake(self):
        orig = self._pwd_inp.pos()
        anim = QPropertyAnimation(self._pwd_inp, b"pos")
        anim.setDuration(300)
        for pct, dx in [(0.15,-10),(0.35,10),(0.55,-7),(0.75,5)]:
            anim.setKeyValueAt(pct, QPoint(orig.x()+dx, orig.y()))
        anim.setKeyValueAt(0, orig); anim.setKeyValueAt(1.0, orig)
        anim.setEasingCurve(QEasingCurve.Type.Linear)
        anim.start(); self._shake_anim = anim

    def _update_block_msg(self):
        """בדוק אם המחשב חסום כעת — הצג הודעה"""
        try:
            for block in self.cm.config.get("global_blocks", []):
                if not block.get("show_msg", True):
                    continue
                from datetime import datetime as _dt
                if self.cm._matches_block(block, _dt.now()):
                    name = block.get("name", "חסימה")
                    self._block_msg_lbl.setText(f"⛔  המחשב חסום כעת: {name}")
                    self._block_msg_lbl.show()
                    return
        except Exception:
            pass
        self._block_msg_lbl.hide()

    def _apply_style(self):
        self.setStyleSheet(get_lockscreen_style(self.dark))

    def closeEvent(self, event): event.ignore()

    def shutdown(self):
        self._focus_timer.stop()
        if hasattr(self, '_clock_timer'): self._clock_timer.stop()
        set_taskbar_visible(True)

    # נקרא מ-keyboard hook
    def on_admin_hotkey(self):
        QTimer.singleShot(0, self._open_quick_admin)
