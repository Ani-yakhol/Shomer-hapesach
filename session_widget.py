"""
session_widget.py - חלונית זמן צפה במהלך שימוש במחשב
שומר הפתח v0.0.8
"""
import ctypes
from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFrame, QApplication, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPoint, QRect
from PyQt6.QtGui import QColor, QCursor
from styles import get_session_widget_style
from time_manager import TimeManager


def get_active_window_title() -> str:
    """מחזיר שם החלון הפעיל כרגע"""
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return ""
        buf = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value.strip()
        # נקה תוצאות לא רלוונטיות
        for skip in ("שומר הפתח", "Program Manager", ""):
            if title == skip:
                return ""
        return title[:40]
    except Exception:
        return ""


class SessionWidget(QWidget):
    """
    חלונית זמן קטנה וצפה בזמן שימוש.
    ניתן לגרירה, מזעור, יציאה, ומעבר למסך הכניסה.
    """
    logout_requested  = pyqtSignal()
    welcome_requested = pyqtSignal()   # מעבר למסך כניסה (לקנות חבילה וכו')

    def __init__(self, config_manager=None, username: str = "",
                 dark: bool = False, parent=None):
        super().__init__(parent)
        self.cm       = config_manager
        self.username = username
        self.dark     = dark

        self._drag_pos: QPoint | None = None
        self._minimized = False

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._build_ui()
        self.setStyleSheet(get_session_widget_style(dark))

        # מיקום: פינה שמאלית-עליונה
        self.move(16, 16)

        # ניטור אפליקציה פעילה (כל 2 שניות)
        self._app_timer = QTimer()
        self._app_timer.setInterval(2000)
        self._app_timer.timeout.connect(self._update_active_app)
        self._app_timer.start()

    # ── בניית UI ─────────────────────────────────────────────────

    def _build_ui(self):
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(0, 0, 0, 0)
        self._outer.setSpacing(0)

        self._frame = QFrame()
        self._frame.setObjectName("SessionWidget")
        self._frame.setFixedWidth(240)

        self._frame_layout = QVBoxLayout(self._frame)
        self._frame_layout.setContentsMargins(12, 10, 12, 10)
        self._frame_layout.setSpacing(6)

        # ── שורת כותרת ──
        top_row = QHBoxLayout()

        title_lbl = QLabel("⏱  שומר הפתח")
        title_lbl.setObjectName("SwTitle")
        top_row.addWidget(title_lbl)
        top_row.addStretch()

        # כפתור מזעור (מקטין לשורה אחת)
        self._min_btn = QPushButton("–")
        self._min_btn.setObjectName("SwMinimize")
        self._min_btn.setFixedSize(22, 22)
        self._min_btn.setToolTip("מזעור")
        self._min_btn.clicked.connect(self._toggle_minimize)
        top_row.addWidget(self._min_btn)

        self._frame_layout.addLayout(top_row)

        # ── תוכן (נמחק במזעור) ──
        self._content = QWidget()
        cl = QVBoxLayout(self._content)
        cl.setContentsMargins(0, 2, 0, 2)
        cl.setSpacing(5)

        # שם משתמש
        user = self.cm.get_user(self.username) if self.cm else {}
        display = (user.get("display_name") or self.username) if user else self.username
        name_lbl = QLabel(display)
        name_lbl.setObjectName("SwSub")
        name_lbl.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        cl.addWidget(name_lbl)

        # זמן סשן
        self._time_lbl = QLabel("00:00:00")
        self._time_lbl.setObjectName("SwTime")
        self._time_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(self._time_lbl)

        # זמן נותר
        self._rem_lbl = QLabel("")
        self._rem_lbl.setObjectName("SwSub")
        self._rem_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._rem_lbl.setWordWrap(True)
        cl.addWidget(self._rem_lbl)

        # אפליקציה פעילה
        self._app_lbl = QLabel("")
        self._app_lbl.setObjectName("SwApp")
        self._app_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._app_lbl.setWordWrap(True)
        cl.addWidget(self._app_lbl)

        # ── כפתורים ──
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self._welcome_btn = QPushButton("📋")
        self._welcome_btn.setObjectName("SwMinimize")
        self._welcome_btn.setFixedSize(28, 28)
        self._welcome_btn.setToolTip("מסך כניסה (קנה חבילות / היסטוריה)")
        self._welcome_btn.clicked.connect(self.welcome_requested.emit)
        btn_row.addWidget(self._welcome_btn)

        btn_row.addStretch()

        self._logout_btn = QPushButton("יציאה מהמשתמש ✕")
        self._logout_btn.setObjectName("SwLogout")
        self._logout_btn.setFixedHeight(28)
        self._logout_btn.setToolTip("יציאה מהמשתמש — חזרה למסך הנעילה. המחשב ממשיך לפעול.")
        self._logout_btn.clicked.connect(self.logout_requested.emit)
        btn_row.addWidget(self._logout_btn)

        cl.addLayout(btn_row)
        self._frame_layout.addWidget(self._content)
        self._outer.addWidget(self._frame)
        self.adjustSize()

    # ── מזעור / הגדלה ────────────────────────────────────────────

    def _toggle_minimize(self):
        self._minimized = not self._minimized
        self._content.setVisible(not self._minimized)
        self._min_btn.setText("□" if self._minimized else "–")
        self._frame.adjustSize()
        self.adjustSize()

        # שמור פינה שמאלית-עליונה
        self.move(16, 16)

    # ── עדכון זמן ────────────────────────────────────────────────

    def update_time(self, session_seconds: int, remaining):
        self._time_lbl.setText(TimeManager.format_time(session_seconds))

        if remaining is None:
            self._rem_lbl.setText("ללא הגבלת זמן")
            self._rem_lbl.setStyleSheet("color: #22c55e; font-size: 11px;")
        elif remaining == 0:
            self._rem_lbl.setText("⛔  נגמר הזמן!")
            self._rem_lbl.setStyleSheet("color: #ef4444; font-size: 12px; font-weight: 700;")
        else:
            color = "#22c55e" if remaining > 1800 else "#f59e0b" if remaining > 300 else "#ef4444"
            self._rem_lbl.setText(f"נותר: {TimeManager.format_time_human(remaining)}")
            self._rem_lbl.setStyleSheet(f"color: {color}; font-size: 11px;")

    def _update_active_app(self):
        title = get_active_window_title()
        if title:
            display = title if len(title) <= 35 else title[:32] + "..."
            self._app_lbl.setText(f"🖥 {display}")
        else:
            self._app_lbl.setText("")

    # ── גרירה ─────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def closeEvent(self, event):
        self._app_timer.stop()
        event.accept()
