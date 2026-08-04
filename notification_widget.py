"""
notification_widget.py - חלוניות התראה לפני סיום זמן שימוש
Computer Guardian - שומר המחשב
"""

from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, QRect
import PyQt6.QtWidgets as QtWidgets
from styles import get_notification_style
from time_manager import TimeManager


class NotificationWidget(QFrame):
    """
    חלונית התראה שצצה מהצד (animate-in/out).
    מוצגת כ-top-level window מעל הכל.
    """

    def __init__(self, message: str, remaining_seconds: int, dark: bool = False, parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.WindowStaysOnTopHint |
                         Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self.dark = dark
        self._auto_close_ms = 8000

        self._build_ui(message, remaining_seconds)
        self.setStyleSheet(get_notification_style(dark))
        self._position()
        self._start_auto_close()

    def _build_ui(self, message: str, remaining_secs: int):
        self.setObjectName("NotifFrame")
        self.setFixedWidth(310)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(6)

        # כותרת
        title_row = QHBoxLayout()
        icon = QLabel("⏰")
        icon.setStyleSheet("font-size: 20px;")
        title_row.addWidget(icon)

        title = QLabel("התראת זמן")
        title.setObjectName("NotifTitle")
        title_row.addWidget(title)
        title_row.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: none;
                color: #888; font-size: 14px; padding: 0 4px;
            }
            QPushButton:hover { color: #ef4444; }
        """)
        close_btn.setFixedSize(22, 22)
        close_btn.clicked.connect(self.close_anim)
        title_row.addWidget(close_btn)

        layout.addLayout(title_row)

        # גוף
        body = QLabel(message)
        body.setObjectName("NotifBody")
        body.setWordWrap(True)
        body.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        layout.addWidget(body)

        # זמן
        time_str = TimeManager.format_time_human(remaining_secs)
        sub = QLabel(f"נותר: {time_str}")
        sub.setObjectName("NotifSub")
        layout.addWidget(sub)

        # Progress bar פשוטה
        self._progress_label = QLabel()
        self._progress_label.setFixedHeight(4)
        self._progress_label.setStyleSheet(
            "background: #ef4444; border-radius: 2px;"
        )
        layout.addWidget(self._progress_label)
        self._progress_width = 274  # רוחב מלא
        self._progress_label.setFixedWidth(self._progress_width)

        # טיימר לצמצום הProgress
        self._elapsed = 0
        self._prog_timer = QTimer()
        self._prog_timer.setInterval(100)
        self._prog_timer.timeout.connect(self._update_progress)
        self._prog_timer.start()

    def _update_progress(self):
        self._elapsed += 100
        ratio = max(0, 1 - self._elapsed / self._auto_close_ms)
        self._progress_label.setFixedWidth(int(self._progress_width * ratio))

    def _position(self):
        """ממקם את החלונית בצד שמאל למטה של המסך"""
        screen = QtWidgets.QApplication.primaryScreen().geometry()
        w, h = 310, 120
        x = screen.right() - w - 20
        y = screen.bottom() - h - 60
        self.setGeometry(x, y, w, h)

    def show(self):
        super().show()
        # אנימציית כניסה - מימין פנימה
        screen = QtWidgets.QApplication.primaryScreen().geometry()
        start_x = screen.right()
        end_x   = screen.right() - 330
        y = self.y()

        self.anim = QPropertyAnimation(self, b"pos")
        self.anim.setDuration(350)
        self.anim.setStartValue(QPoint(start_x, y))
        self.anim.setEndValue(QPoint(end_x, y))
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.start()

    def close_anim(self):
        """אנימציית יציאה"""
        screen = QtWidgets.QApplication.primaryScreen().geometry()
        self.anim_out = QPropertyAnimation(self, b"pos")
        self.anim_out.setDuration(300)
        self.anim_out.setStartValue(self.pos())
        self.anim_out.setEndValue(QPoint(screen.right(), self.y()))
        self.anim_out.setEasingCurve(QEasingCurve.Type.InCubic)
        self.anim_out.finished.connect(self.close)
        self.anim_out.start()

    def _start_auto_close(self):
        QTimer.singleShot(self._auto_close_ms, self.close_anim)


class ExpiredDialog(QFrame):
    """
    דיאלוג שמוצג כשהזמן נגמר לחלוטין.
    מכסה את כל המסך ומחייב המתנה.
    """

    def __init__(self, username: str, dark: bool = False, parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.dark = dark
        self._build_ui(username)

    def _build_ui(self, username: str):
        screen = QtWidgets.QApplication.primaryScreen().geometry()
        self.setGeometry(screen)

        # שכבת רקע חצי-שקופה
        overlay = QFrame(self)
        overlay.setGeometry(self.rect())
        if self.dark:
            overlay.setStyleSheet("background: rgba(0,0,0,0.85); border-radius: 0;")
        else:
            overlay.setStyleSheet("background: rgba(0,0,20,0.80); border-radius: 0;")

        # כרטיס מרכזי
        card = QFrame(self)
        card.setFixedSize(420, 260)
        card.move(
            (screen.width() - 420) // 2,
            (screen.height() - 260) // 2,
        )
        if self.dark:
            card.setStyleSheet("""
                QFrame {
                    background: #161b22; border: 2px solid #da3633;
                    border-radius: 18px;
                }
            """)
        else:
            card.setStyleSheet("""
                QFrame {
                    background: white; border: 2px solid #ef4444;
                    border-radius: 18px;
                }
            """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(36, 32, 36, 32)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_lbl = QLabel("⏱️")
        icon_lbl.setStyleSheet("font-size: 44px;")
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_lbl)

        title = QLabel("נגמר זמן השימוש")
        title.setStyleSheet(f"""
            color: {'#f85149' if self.dark else '#ef4444'};
            font-size: 22px; font-weight: 700;
            font-family: 'Segoe UI', 'Arial Hebrew', sans-serif;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        user = self.display_name if hasattr(self, 'display_name') else username
        sub = QLabel(f"המחשב ייחסם כעת")
        sub.setStyleSheet(f"""
            color: {'#8b949e' if self.dark else '#6b7280'};
            font-size: 14px;
            font-family: 'Segoe UI', 'Arial Hebrew', sans-serif;
        """)
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub)

        # ספירה לאחור
        self._countdown = 5
        self._count_lbl = QLabel(f"נועל בעוד {self._countdown}...")
        self._count_lbl.setStyleSheet(f"""
            color: {'#e6edf3' if self.dark else '#0d1b2a'};
            font-size: 13px;
            font-family: 'Segoe UI', 'Arial Hebrew', sans-serif;
        """)
        self._count_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._count_lbl)

        self._timer = QTimer()
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick_countdown)
        self._timer.start()

        self.lock_callback = None

    def _tick_countdown(self):
        self._countdown -= 1
        self._count_lbl.setText(f"נועל בעוד {self._countdown}...")
        if self._countdown <= 0:
            self._timer.stop()
            if self.lock_callback:
                self.lock_callback()
