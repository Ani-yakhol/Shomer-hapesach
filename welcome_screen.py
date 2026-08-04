"""
welcome_screen.py - מסך כניסה למשתמש (לאחר סיסמה נכונה)
שומר הפתח v0.0.8

מנהל מערכת רואה כפתור "כניסה להגדרות".
משתמש רגיל רואה רק "כניסה למחשב".
לשוניות: קנה חבילות (אם מופעל), היסטוריה, הודעות (אם מופעל)
"""
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame, QPushButton,
    QTabWidget, QScrollArea, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QApplication, QSizePolicy, QListWidget, QListWidgetItem,
    QComboBox, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor
from styles import get_welcome_style
from time_manager import TimeManager


class WelcomeScreen(QWidget):
    enter_requested    = pyqtSignal()   # "כניסה למחשב"
    settings_requested = pyqtSignal()   # "כניסה להגדרות" (מנהל בלבד)
    exit_requested     = pyqtSignal()   # "יציאה" ← חזרה למסך נעילה ללא כניסה

    def __init__(self, config_manager, username: str, dark=False, is_returning=False, parent=None):
        super().__init__(parent)
        self.cm           = config_manager
        self.username     = username
        self.dark         = dark
        self.is_returning = is_returning
        self.user         = config_manager.get_user(username) or {}
        self.is_admin     = self.user.get("is_admin", False)

        self.setObjectName("WelcomeScreen")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        self.showFullScreen()

        self._build_ui()
        self.setStyleSheet(get_welcome_style(dark))

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0,0,0,0); root.setSpacing(0)

        # ── Header ──
        hdr = QFrame()
        hdr.setFixedHeight(70)
        hdr.setStyleSheet(
            f"background:{'#161b22' if self.dark else '#ffffff'};"
            f"border-bottom:1px solid {'#30363d' if self.dark else '#e2e8f4'};"
        )
        hl = QHBoxLayout(hdr); hl.setContentsMargins(36,0,36,0)
        logo = QLabel("🔐  שומר הפתח")
        logo.setStyleSheet(f"color:{'#e6edf3' if self.dark else '#0d1b2a'};"
                           "font-size:17px;font-weight:700;"
                           "font-family:'Segoe UI','Arial Hebrew',sans-serif;")
        hl.addWidget(logo); hl.addStretch()

        now_lbl = QLabel(datetime.now().strftime("%H:%M  |  %d/%m/%Y"))
        now_lbl.setStyleSheet(f"color:{'#8b949e' if self.dark else '#6b7280'};"
                              "font-size:14px;font-family:'Segoe UI',sans-serif;")
        hl.addWidget(now_lbl)
        root.addWidget(hdr)

        # ── Body ──
        body = QHBoxLayout()
        body.setContentsMargins(50,36,50,36); body.setSpacing(32)

        # ── עמודה שמאל ──
        left = QVBoxLayout(); left.setSpacing(18); left.setAlignment(Qt.AlignmentFlag.AlignTop)

        name = self.user.get("display_name") or self.username
        greeting = QLabel(f"שלום, {name}! 👋")
        greeting.setObjectName("WelcomeName")
        greeting.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        left.addWidget(greeting)

        sub_lbl = QLabel("ברוך הבא לשומר הפתח")
        sub_lbl.setObjectName("WelcomeSub")
        sub_lbl.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        left.addWidget(sub_lbl)

        left.addWidget(self._make_time_card())
        left.addWidget(self._make_restrictions_card())
        left.addStretch()

        # ── כפתורים ──
        btns_col = QVBoxLayout(); btns_col.setSpacing(10)

        enter_label = "▶   המשך שימוש" if self.is_returning else "▶   כניסה למחשב"
        enter_btn = QPushButton(enter_label)
        enter_btn.setObjectName("EnterBtn")
        enter_btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        enter_btn.setFixedHeight(50)
        enter_btn.clicked.connect(self.enter_requested.emit)
        btns_col.addWidget(enter_btn)

        if self.is_admin:
            settings_btn = QPushButton("⚙️   כניסה להגדרות")
            settings_btn.setObjectName("SettingsBtn")
            settings_btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            settings_btn.setFixedHeight(50)
            settings_btn.clicked.connect(self.settings_requested.emit)
            btns_col.addWidget(settings_btn)

        exit_btn = QPushButton("✕   יציאה מהמשתמש")
        exit_btn.setObjectName("ExitBtn")
        exit_btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        exit_btn.setFixedHeight(44)
        exit_btn.setToolTip("יציאה מהמשתמש — חזרה למסך הנעילה. המחשב ממשיך לפעול כרגיל.")
        exit_btn.clicked.connect(self.exit_requested.emit)
        btns_col.addWidget(exit_btn)

        left.addLayout(btns_col)
        body.addLayout(left, 2)

        # ── עמודה ימין: לשוניות ──
        tabs = QTabWidget()
        tabs.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        general_cfg = self.cm.get_general_cfg()
        show_pkgs   = general_cfg.get("show_packages_tab", True)
        show_msgs   = general_cfg.get("show_messages", True)

        if show_pkgs:
            tabs.addTab(self._make_packages_tab(), "🛒  קנה חבילות")

        tabs.addTab(self._make_history_tab(), "📋  היסטוריה")

        if show_msgs and not self.user.get("messages_blocked"):
            tabs.addTab(self._make_messages_tab(), "💬  הודעות")

        right = QVBoxLayout(); right.addWidget(tabs)
        body.addLayout(right, 3)

        root.addLayout(body)

    # ── כרטיס זמן ────────────────────────────────────────────────
    def _make_time_card(self):
        card = QFrame(); card.setObjectName("WelcomeCard")
        cl = QVBoxLayout(card); cl.setContentsMargins(18,14,18,14); cl.setSpacing(8)
        cl.setAlignment(Qt.AlignmentFlag.AlignRight)

        ttl = QLabel("⏱  זמן שימוש")
        ttl.setStyleSheet(f"color:{'#e6edf3' if self.dark else '#0d1b2a'};"
                          "font-size:15px;font-weight:600;"
                          "font-family:'Segoe UI','Arial Hebrew',sans-serif;")
        ttl.setLayoutDirection(Qt.LayoutDirection.RightToLeft); cl.addWidget(ttl)

        rem = self.cm.get_remaining_time_today(self.username)
        if rem is None:
            rem_text, color = "ללא הגבלת זמן ✓", "#22c55e"
        elif rem == 0:
            rem_text, color = "נגמר זמן השימוש להיום", "#ef4444"
        else:
            rem_text = TimeManager.format_time_human(rem) + " נותרו"
            color = "#f59e0b" if rem < 1800 else "#22c55e"

        rl = QLabel(rem_text)
        rl.setStyleSheet(f"color:{color};font-size:20px;font-weight:700;"
                         "font-family:'Segoe UI','Arial Hebrew',sans-serif;")
        rl.setLayoutDirection(Qt.LayoutDirection.RightToLeft); cl.addWidget(rl)

        used = self.cm.get_time_used_today(self.username)
        ul = QLabel(f"שומש היום: {TimeManager.format_time_human(used)}")
        ul.setStyleSheet(f"color:{'#8b949e' if self.dark else '#6b7280'};"
                         "font-size:13px;font-family:'Segoe UI','Arial Hebrew',sans-serif;")
        ul.setLayoutDirection(Qt.LayoutDirection.RightToLeft); cl.addWidget(ul)
        return card

    # ── כרטיס הגבלות ─────────────────────────────────────────────
    def _make_restrictions_card(self):
        card = QFrame(); card.setObjectName("WelcomeCard")
        cl = QVBoxLayout(card); cl.setContentsMargins(18,14,18,14); cl.setSpacing(6)

        ttl = QLabel("🔒  הגבלות פעילות")
        ttl.setStyleSheet(f"color:{'#e6edf3' if self.dark else '#0d1b2a'};"
                          "font-size:14px;font-weight:600;"
                          "font-family:'Segoe UI','Arial Hebrew',sans-serif;")
        ttl.setLayoutDirection(Qt.LayoutDirection.RightToLeft); cl.addWidget(ttl)

        items = []
        u = self.user
        if u.get("time_limit_daily"): items.append(f"זמן יומי: {u['time_limit_daily']} דקות")
        if u.get("time_limit_total"): items.append(f"זמן סשן: {u['time_limit_total']} דקות")
        if u.get("blocked_hours"):    items.append(f"חסימת שעות: {len(u['blocked_hours'])} חלונות")
        if u.get("blocked_dates"):    items.append(f"תאריכים חסומים: {len(u['blocked_dates'])}")
        if u.get("app_limits"):       items.append(f"הגבלות תוכנות: {len(u['app_limits'])}")

        if not items:
            lbl = QLabel("אין הגבלות פעילות ✓")
            lbl.setStyleSheet("color:#22c55e;font-size:13px;font-family:'Segoe UI','Arial Hebrew',sans-serif;")
            lbl.setLayoutDirection(Qt.LayoutDirection.RightToLeft); cl.addWidget(lbl)
        else:
            for item in items:
                lbl = QLabel(f"• {item}")
                lbl.setStyleSheet(f"color:{'#8b949e' if self.dark else '#6b7280'};"
                                  "font-size:12px;font-family:'Segoe UI','Arial Hebrew',sans-serif;")
                lbl.setWordWrap(True)
                lbl.setLayoutDirection(Qt.LayoutDirection.RightToLeft); cl.addWidget(lbl)
        return card

    # ── לשונית חבילות ────────────────────────────────────────────
    def _make_packages_tab(self):
        w = QWidget(); l = QVBoxLayout(w)
        l.setContentsMargins(12,12,12,12); l.setSpacing(10)

        lbl = QLabel("רכישת חבילות זמן / הדפסה:")
        lbl.setLayoutDirection(Qt.LayoutDirection.RightToLeft); l.addWidget(lbl)

        pkgs = self.cm.get_packages()
        if not pkgs:
            empty = QLabel("אין חבילות זמינות כרגע")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            l.addWidget(empty)
        else:
            for pkg in pkgs:
                row = QFrame(); row.setObjectName("WelcomeCard")
                rl = QHBoxLayout(row); rl.setContentsMargins(14,10,14,10)

                name_lbl = QLabel(f"{'⏱' if pkg.get('type')=='time' else '🖨'} {pkg.get('name','')}")
                name_lbl.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
                rl.addWidget(name_lbl); rl.addStretch()

                val = pkg.get("value",0)
                type_str = f"{val} דקות" if pkg.get("type")=="time" else f"{val} הדפסות"
                val_lbl = QLabel(type_str)
                val_lbl.setStyleSheet(f"color:{'#8b949e' if self.dark else '#6b7280'};font-size:12px;")
                rl.addWidget(val_lbl); rl.addSpacing(12)

                if pkg.get("has_price"):
                    price_lbl = QLabel(f"₪{pkg.get('price',0):.2f}")
                    price_lbl.setStyleSheet("color:#22c55e;font-weight:600;")
                    rl.addWidget(price_lbl); rl.addSpacing(8)

                buy_btn = QPushButton("בחר ▶")
                buy_btn.setObjectName("PrimaryBtn") if hasattr(buy_btn,"setObjectName") else None
                buy_btn.setStyleSheet("background:#2563eb;color:white;border:none;border-radius:7px;"
                                      "font-size:12px;font-weight:600;padding:5px 14px;")
                buy_btn.clicked.connect(lambda _, pid=pkg.get("id"): self._buy_package(pid))
                rl.addWidget(buy_btn)

                l.addWidget(row)

        l.addStretch()
        return w

    def _buy_package(self, pkg_id):
        ok = self.cm.add_package_to_user(self.username, pkg_id)
        if ok:
            QMessageBox.information(self, "הצלחה", "החבילה נוספה לחשבונך ✓")
        else:
            QMessageBox.warning(self, "שגיאה", "לא ניתן להוסיף את החבילה")

    # ── לשונית היסטוריה ──────────────────────────────────────────
    def _make_history_tab(self):
        w = QWidget(); l = QVBoxLayout(w)
        l.setContentsMargins(10,10,10,10); l.setSpacing(8)

        lbl = QLabel("היסטוריית שימוש שלך:")
        lbl.setLayoutDirection(Qt.LayoutDirection.RightToLeft); l.addWidget(lbl)

        history = self.user.get("session_history", [])
        if not history:
            empty = QLabel("אין היסטוריית שימוש עדיין")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter); l.addWidget(empty)
            return w

        table = QTableWidget(min(len(history),30), 4)
        table.setHorizontalHeaderLabels(["תאריך","כניסה","שימוש","הדפסות"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        for i, entry in enumerate(reversed(history[-30:])):
            table.setItem(i, 0, QTableWidgetItem(entry.get("date","")))
            table.setItem(i, 1, QTableWidgetItem(entry.get("login_time","")))
            dur = entry.get("duration_seconds", 0)
            table.setItem(i, 2, QTableWidgetItem(TimeManager.format_time_human(dur)))
            table.setItem(i, 3, QTableWidgetItem(str(entry.get("prints",0))))

        l.addWidget(table)
        return w

    # ── לשונית הודעות ─────────────────────────────────────────────
    def _make_messages_tab(self):
        w = QWidget(); l = QVBoxLayout(w)
        l.setContentsMargins(10,10,10,10); l.setSpacing(10)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._msg_container = QWidget()
        self._msg_layout = QVBoxLayout(self._msg_container)
        self._msg_layout.setAlignment(Qt.AlignmentFlag.AlignTop); self._msg_layout.setSpacing(8)
        self._load_messages()
        scroll.setWidget(self._msg_container)
        l.addWidget(scroll)

        row = QHBoxLayout(); row.setSpacing(8)
        self._msg_input = QLineEdit()
        self._msg_input.setObjectName("MsgInput")
        self._msg_input.setPlaceholderText("כתוב הודעה למנהל...")
        self._msg_input.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._msg_input.returnPressed.connect(self._send_msg)
        row.addWidget(self._msg_input)

        send_btn = QPushButton("שלח ▶"); send_btn.setObjectName("SendBtn")
        send_btn.clicked.connect(self._send_msg); row.addWidget(send_btn)
        l.addLayout(row)
        return w

    def _load_messages(self):
        for msg in self.user.get("messages",[]):
            self._add_bubble(msg)

    def _add_bubble(self, msg):
        is_user = msg.get("from")=="user"
        bubble = QFrame(); bubble.setObjectName("MsgUser" if is_user else "MsgAdmin")
        bl = QVBoxLayout(bubble); bl.setContentsMargins(12,8,12,8); bl.setSpacing(2)

        sender = QLabel("אתה" if is_user else "מנהל המערכת")
        sender.setStyleSheet(f"color:{'#388bfd' if is_user else '#3fb950'};"
                             "font-size:11px;font-weight:600;")
        sender.setLayoutDirection(Qt.LayoutDirection.RightToLeft); bl.addWidget(sender)

        txt = QLabel(msg.get("text","")); txt.setWordWrap(True)
        txt.setLayoutDirection(Qt.LayoutDirection.RightToLeft); bl.addWidget(txt)

        ts = msg.get("time","")
        try: ts = datetime.fromisoformat(ts).strftime("%d/%m %H:%M")
        except: pass
        tl = QLabel(ts); tl.setStyleSheet("color:#8b949e;font-size:10px;"); bl.addWidget(tl)

        align = QHBoxLayout()
        if is_user: align.addStretch(); align.addWidget(bubble)
        else:       align.addWidget(bubble); align.addStretch()

        ctr = QWidget(); ctr.setLayout(align)
        self._msg_layout.addWidget(ctr)

    def _send_msg(self):
        text = self._msg_input.text().strip()
        if not text: return
        self.cm.add_message_from_user(self.username, text)
        self._msg_input.clear()
        msg = {"from":"user","text":text,"time":datetime.now().isoformat()}
        self._add_bubble(msg)

    def closeEvent(self, event): event.ignore()
