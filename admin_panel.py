"""
admin_panel.py - פאנל הגדרות מלא
שומר הפתח v2.0
לשוניות: ראשי, מחשבים נוספים, מסך נעילה, מסך יציאה,
         משתמשים, חבילות, מדפסות, תוכנות, חסימות, מצב קיוסק, הודעות, הגדרות
"""
import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QFrame, QPushButton, QLineEdit, QScrollArea, QStackedWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox,
    QSpinBox, QComboBox, QDialog, QMessageBox, QFileDialog,
    QTabWidget, QListWidget, QListWidgetItem, QTimeEdit,
    QDateEdit, QGroupBox, QFormLayout, QTextEdit, QSizePolicy,
    QApplication, QDoubleSpinBox, QDialogButtonBox, QSplitter,
    QColorDialog, QInputDialog
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QTime, QDate
from PyQt6.QtGui import QColor, QPixmap, QIcon
from styles import get_panel_style
from time_manager import TimeManager


class AdminPanel(QMainWindow):
    panel_closed = pyqtSignal()

    PAGES = [
        ("🏠  ראשי",            "DashboardPage"),
        ("🖥️  מחשבים נוספים",   "NetworkPage"),
        ("🔒  מסך נעילה",        "LockScreenPage"),
        ("🚪  מסך יציאה",        "ExitScreenPage"),
        ("👥  משתמשים",          "UsersPage"),
        ("📦  חבילות",           "PackagesPage"),
        ("💳  תשלום",            "PaymentPage"),
        ("🖨️  מדפסות",          "PrintersPage"),
        ("📱  תוכנות",           "AppsPage"),
        ("⛔  חסימות",           "BlocksPage"),
        ("🌑  כיבוי ת. מסך",     "ScreenOffPage"),
        ("🏪  מצב קיוסק",        "KioskPage"),
        ("💬  הודעות",           "MessagesPage"),
        ("⚙️  הגדרות",           "SettingsPage"),
        ("ℹ️  אודות",            "AboutPage"),
    ]

    def __init__(self, config_manager, dark=False, parent=None):
        super().__init__(parent)
        self.cm   = config_manager
        self.dark = dark
        self.setWindowTitle("שומר הפתח – פאנל הגדרות")
        self.setMinimumSize(1050, 780)
        self.resize(1200, 880)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        try:
            self._build_ui()
        except Exception as e:
            import traceback, logging
            logging.getLogger(__name__).error(f"AdminPanel._build_ui קרסה: {traceback.format_exc()}")
            raise  # העבר הלאה כדי שmain.py יתפוס
        self.setStyleSheet(get_panel_style(dark))
        self._select_page(0)

    def _build_ui(self):
        central = QWidget(); self.setCentralWidget(central)
        root = QHBoxLayout(central); root.setContentsMargins(0,0,0,0); root.setSpacing(0)

        # Sidebar
        self._sidebar = QFrame(); self._sidebar.setObjectName("Sidebar")
        self._sidebar.setFixedWidth(210)
        sl = QVBoxLayout(self._sidebar); sl.setContentsMargins(10,18,10,18); sl.setSpacing(3)
        sl.setAlignment(Qt.AlignmentFlag.AlignTop)

        logo_w = QWidget(); logo_hl = QHBoxLayout(logo_w)
        logo_hl.setContentsMargins(6,8,6,14); logo_hl.setSpacing(0)
        logo = QLabel("🔐  שומר הפתח")
        logo.setStyleSheet("font-size:15px;font-weight:700;"
                           "font-family:'Segoe UI','Arial Hebrew',sans-serif;")
        logo.setLayoutDirection(Qt.LayoutDirection.RightToLeft); logo_hl.addWidget(logo)
        logo_hl.addStretch()
        ver_lbl = QLabel("v0.0.10")
        ver_lbl.setStyleSheet("font-size:11px;font-weight:400;color:rgba(128,128,128,0.75);"
                              "font-family:'Segoe UI',sans-serif;")
        logo_hl.addWidget(ver_lbl)
        sl.addWidget(logo_w)

        # כפתור הודעות עם badge
        self._unread_badge = 0
        self._side_btns = []
        for i, (name, _) in enumerate(self.PAGES):
            display = name
            if name.startswith("💬"):
                n = self.cm.unread_messages_count()
                if n > 0: display = f"{name} 🔴{n}"
            btn = QPushButton(display); btn.setObjectName("SideBtn")
            btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            btn.clicked.connect(lambda _, idx=i: self._select_page(idx))
            sl.addWidget(btn); self._side_btns.append(btn)

        sl.addStretch()
        close_btn = QPushButton("✕  סגור פאנל"); close_btn.setObjectName("DangerBtn")
        close_btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        close_btn.clicked.connect(self._close); sl.addWidget(close_btn)

        root.addWidget(self._sidebar)

        # Stack
        self._stack = QStackedWidget()
        root.addWidget(self._stack, 1)

        # יצירת דפים
        self._pages = []
        page_classes = [
            DashboardPage, NetworkPage, LockScreenPage, ExitScreenPage,
            UsersPage, PackagesPage, PaymentPage, PrintersPage, AppsPage,
            BlocksPage,ScreenOffPage, KioskPage, MessagesPage, SettingsPage,
            AboutPage
        ]
        for cls in page_classes:
            pg = cls(self.cm, self.dark, self._toggle_dark if cls == SettingsPage else None)
            self._stack.addWidget(pg); self._pages.append(pg)

    def _select_page(self, idx):
        self._stack.setCurrentIndex(idx)
        for i, btn in enumerate(self._side_btns):
            btn.setProperty("selected", i == idx)
            btn.style().unpolish(btn); btn.style().polish(btn)
        pg = self._pages[idx]
        if hasattr(pg, "refresh"): pg.refresh()

    def _toggle_dark(self):
        self.dark = not self.dark
        self.cm.set_dark_mode(self.dark)
        self.setStyleSheet(get_panel_style(self.dark))

    def _close(self):
        self.hide(); self.panel_closed.emit()

    def closeEvent(self, event):
        self._close(); event.ignore()


# ══════════════════════════════════════════════════════════════════
# Helper
# ══════════════════════════════════════════════════════════════════

class BasePage(QWidget):
    def __init__(self, cm, dark, extra=None):
        super().__init__()
        self.cm = cm; self.dark = dark
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

    def _title(self, text, sub=""):
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(0,0,0,4); l.setSpacing(2)
        t = QLabel(text); t.setObjectName("PanelTitle"); l.addWidget(t)
        if sub:
            s = QLabel(sub); s.setObjectName("PanelSub"); l.addWidget(s)
        return w

    def _card(self):
        f = QFrame(); f.setObjectName("Card"); return f

    def _sep(self):
        f = QFrame(); f.setFrameShape(QFrame.Shape.HLine)
        f.setStyleSheet("color:rgba(128,128,128,0.2);margin:4px 0;"); return f

    def refresh(self): pass


# ══════════════════════════════════════════════════════════════════
# דף ראשי
# ══════════════════════════════════════════════════════════════════
class DashboardPage(BasePage):
    def __init__(self, cm, dark, _=None):
        super().__init__(cm, dark)
        self._build()

    def _build(self):
        l = QVBoxLayout(self); l.setContentsMargins(28,28,28,28); l.setSpacing(18)
        l.addWidget(self._title("לוח מחוונים","סקירה כללית של המערכת"))

        stats = self.cm.get_total_stats()
        row = QHBoxLayout(); row.setSpacing(14)
        for title, val, sub in [
            ("👥 משתמשים", str(stats["total_users"]), "סה\"כ"),
            ("🔑 מנהלים", str(stats["admin_users"]), "חשבונות מנהל"),
            ("⏱ שימוש כולל", TimeManager.format_time_human(stats["total_usage_seconds"]), "מכלל המשתמשים"),
            ("🖨 הדפסות", str(stats["total_prints"]), "סה\"כ הדפסות"),
            ("🟢 פעילים היום", str(stats["active_today"]), "משתמשים"),
        ]:
            card = self._card(); cl = QVBoxLayout(card)
            cl.setContentsMargins(16,14,16,14); cl.setSpacing(3)
            cl.setAlignment(Qt.AlignmentFlag.AlignRight)
            t = QLabel(title); t.setObjectName("CardSub"); cl.addWidget(t)
            v = QLabel(val); v.setStyleSheet("font-size:28px;font-weight:700;"); cl.addWidget(v)
            s = QLabel(sub); s.setObjectName("CardSub"); cl.addWidget(s)
            row.addWidget(card)
        l.addLayout(row)

        l.addWidget(QLabel("פעילות אחרונה:"))
        self._list = QListWidget(); self._list.setMaximumHeight(180)
        self._fill_list(); l.addWidget(self._list)

        # ── כיבוי התוכנה ──────────────────────────────────────────
        l.addWidget(self._build_pause_card())
        l.addStretch()

    def _build_pause_card(self) -> QFrame:
        """בונה את כרטיס יציאה מהתוכנה"""
        card = self._card()
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 16, 20, 16); cl.setSpacing(12)

        # כותרת
        hdr = QHBoxLayout()
        icon_lbl = QLabel("⚡")
        icon_lbl.setStyleSheet("font-size:20px;")
        hdr.addWidget(icon_lbl)
        title_lbl = QLabel("שליטה בתוכנה")
        title_lbl.setObjectName("CardTitle")
        hdr.addWidget(title_lbl)
        hdr.addStretch()
        cl.addLayout(hdr)

        # ── שורה: יציאה מהתוכנה ──
        row = QHBoxLayout(); row.setSpacing(10)
        desc = QLabel("יציאה מהתוכנה — המחשב לא יהיה מנוטר (יש להפעיל מחדש ידנית)")
        desc.setObjectName("CardSub")
        desc.setWordWrap(True)
        row.addWidget(desc, 1)

        exit_btn = QPushButton("🚪  יציאה")
        exit_btn.setObjectName("DangerBtn")
        exit_btn.setFixedHeight(36)
        exit_btn.clicked.connect(self._on_exit_app)
        row.addWidget(exit_btn)
        cl.addLayout(row)

        return card

    def _on_exit_app(self):
        res = QMessageBox.question(
            self, "כיבוי שומר הפתח",
            "לכבות את שומר הפתח לגמרי?\n\n"
            "המחשב ימשיך לפעול כרגיל — רק שומר הפתח יכבה.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if res == QMessageBox.StandardButton.Yes:
            try:
                from registry_manager import unblock_ctrl_alt_del
                unblock_ctrl_alt_del()
            except Exception:
                pass
            # סגור את החלון ואז צא — ללא הפעלת panel_closed (שמביא למסך נעילה)
            try:
                self.window().hide()
            except Exception:
                pass
            QTimer.singleShot(150, QApplication.instance().quit)

    CITIES = [
        ("ירושלים",         31.7683, 35.2137),
        ("תל אביב",          32.0853, 34.7818),
        ("חיפה",             32.7940, 34.9896),
        ("באר שבע",          31.2530, 34.7915),
        ("אשדוד",            31.8040, 34.6550),
        ("אשקלון",           31.6688, 34.5743),
        ("פתח תקווה",        32.0872, 34.8867),
        ("בני ברק",          32.0833, 34.8333),
        ("ביתר עילית",       31.6996, 35.1213),
        ("מודיעין עילית",    31.9285, 35.0445),
        ("מודיעין-מכבים",    31.8967, 35.0100),
        ("נתניה",            32.3215, 34.8532),
        ("ראשון לציון",      31.9730, 34.7925),
        ("רחובות",           31.8928, 34.8115),
        ("חולון",            32.0114, 34.7795),
        ("בת ים",            32.0236, 34.7502),
        ("קריית שמונה",      33.2073, 35.5695),
        ("טבריה",            32.7958, 35.5302),
        ("צפת",              32.9647, 35.4960),
        ("נצרת",             32.6993, 35.2960),
        ("אילת",             29.5577, 34.9519),
        ("רמת גן",           32.0684, 34.8248),
        ("גבעתיים",          32.0683, 34.8122),
        ("קריית ביאליק",     32.8381, 35.0930),
        ("לוד",              31.9530, 34.8953),
        ("רמלה",             31.9298, 34.8710),
        ("נס ציונה",         31.9305, 34.7990),
        ("ירוחם",            30.9882, 34.9295),
        ("קריית גת",         31.6087, 34.7673),
        ("אופקים",           31.3122, 34.6225),
        ("דימונה",           31.0688, 35.0327),
        ("עפולה",            32.6074, 35.2895),
        ("חדרה",             32.4338, 34.9196),
        ("כפר סבא",          32.1773, 34.9077),
        ("הרצליה",           32.1651, 34.8439),
        ("רעננה",            32.1840, 34.8730),
        ("גן יבנה",          31.7891, 34.7061),
        ("אריאל",            32.1052, 35.1680),
        ("מעלה אדומים",      31.7711, 35.2976),
        ("בית שמש",          31.7457, 35.0063),
        ("טלזסטון",         31.7583, 35.1138),
        ("קריית ארבע",       31.5302, 35.1122),
    ]

    JEWISH_HOLIDAYS = [
        ("ראש השנה",      "rosh_hashana"),
        ("יום כיפור",     "yom_kippur"),
        ("סוכות",         "sukkot"),
        ("שמחת תורה",    "simchat_torah"),
        ("חנוכה",         "chanukah"),
        ("טו בשבט",     "tu_bishvat"),
        ("פורים",         "purim"),
        ("פסח",           "pesach"),
        ("יום העצמאות",   "yom_haatzmaut"),
        ("לג בעומר",    "lag_baomer"),
        ("שבועות",        "shavuot"),
        ("תשעה באב",     "tisha_beav"),
    ]

    def _pick_city(self):
        from PyQt6.QtWidgets import QInputDialog
        names = [c[0] for c in self.CITIES]
        name, ok = QInputDialog.getItem(self, "בחר עיר", "עיר:", names, 0, False)
        if ok and name:
            for cname, lat, lon in self.CITIES:
                if cname == name:
                    self._shab_lat.setText(str(lat))
                    self._shab_lon.setText(str(lon))
                    break

    def _show_holidays(self):
        dlg = HolidayListDialog(
            self.cm.config.get("general",{}).get("blocked_holidays", [h[1] for h in self.JEWISH_HOLIDAYS]),
            self.JEWISH_HOLIDAYS, self.dark, self
        )
        if dlg.exec():
            self.cm.config["general"]["blocked_holidays"] = dlg.get_selected()
            self.cm.save()
            QMessageBox.information(self,"שמירה","רשימת חגים עודכנה ✓")

    def _save_shabbat(self):
        try:
            lat = float(self._shab_lat.text())
            lon = float(self._shab_lon.text())
        except ValueError:
            QMessageBox.warning(self,"שגיאה","קו רוחב/אורך חייב להיות מספר"); return
        cfg = self.cm.config["general"]
        cfg["block_shabbat_chag"]    = self._block_shabbat.isChecked()
        cfg["shabbat_mins_before"]   = self._shab_before.value()
        cfg["shabbat_mins_after"]    = self._shab_after.value()
        cfg["location_lat"]          = lat
        cfg["location_lon"]          = lon
        self.cm.save()
        QMessageBox.information(self,"שמירה","הגדרות שבת נשמרו ✓")

    def _fill_list(self):
        self._list.clear()
        for uname, ud in list(self.cm.get_all_users().items())[:15]:
            dn = ud.get("display_name") or uname
            used = self.cm.get_time_used_today(uname)
            self._list.addItem(f"{dn}   |   שימוש היום: {TimeManager.format_time_human(used)}")

    def refresh(self):
        self._fill_list()


# ══════════════════════════════════════════════════════════════════
# מחשבים נוספים — גישת תיקייה שיתופית
# ══════════════════════════════════════════════════════════════════
class NetworkPage(BasePage):
    """
    ניהול רשת מבוסס תיקייה שיתופית.
    כל מחשב כותב קובץ סטטוס משלו תחת תיקיית Status ומשתף קובץ הגדרות/משתמשים.
    """
    ROLE_LABELS = [
        "standalone – עצמאי (ברירת מחדל, ללא שיתוף)",
        "primary – מחשב ראשי (התיקייה השיתופית אצלו)",
        "secondary – מחשב משני (מתחבר לתיקייה הראשית)",
    ]
    ROLE_KEYS = ["standalone", "primary", "secondary"]

    def __init__(self, cm, dark, _=None):
        super().__init__(cm, dark)
        self._refresh_timer = QTimer()
        self._refresh_timer.setInterval(15000)   # רענון כל 15 שניות
        self._refresh_timer.timeout.connect(self._scan_status)
        self._build()

    def _build(self):
        l = QVBoxLayout(self); l.setContentsMargins(28,28,28,28); l.setSpacing(14)
        l.addWidget(self._title("מחשבים נוספים","שיתוף הגדרות ומשתמשים דרך תיקייה משותפת"))

        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget(); cl = QVBoxLayout(content); cl.setContentsMargins(0,0,0,0); cl.setSpacing(14)

        # ── זיהוי מחשב נוכחי ──
        try:
            import socket
            hostname = socket.gethostname()
        except Exception:
            hostname = "לא זמין"
        cfg = self.cm.get_general_cfg()
        my_uid = cfg.get("machine_uid", "")

        id_card = self._card(); idl = QHBoxLayout(id_card); idl.setContentsMargins(16,12,16,12)
        id_lbl = QLabel(f"🖥️  שם מחשב: {hostname}   |   מזהה ייחודי: {my_uid or '(יחולק בשמירה)'}")
        id_lbl.setStyleSheet("font-weight:600;font-size:13px;")
        id_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        idl.addWidget(id_lbl); cl.addWidget(id_card)

        # ── תיקיית נתונים ──
        folder_card = self._card(); fl2 = QVBoxLayout(folder_card)
        fl2.setContentsMargins(20,16,20,16); fl2.setSpacing(10)
        fl2.addWidget(QLabel("📁  תיקיית נתונים משותפת"))
        fl2.addWidget(QLabel(
            "הזן נתיב לתיקייה בה יישמרו ההגדרות והמשתמשים.\n"
            "ניתן להשתמש בנתיב רשת (לדוגמה: \\\\Server\\ShomerData) "
            "או בתיקייה מקומית.",
            objectName="PanelSub"
        ).also(lambda w: w.setWordWrap(True)) if False else self._make_sub(
            "הזן נתיב לתיקייה. בתיקייה משותפת ברשת: \\\\שם-שרת\\שיתוף.\n"
            "⚠️  אם כבר קיימים קבצים בתיקייה (ממחשב אחר) — הנתונים הקיימים יישמרו!"
        ))
        folder_row = QHBoxLayout()
        self._folder = QLineEdit(cfg.get("shared_folder", ""))
        self._folder.setPlaceholderText(r"לדוגמה: \\Server\ShomerData  או  C:\ShomerShared")
        folder_row.addWidget(self._folder)
        browse_btn = QPushButton("עיון..."); browse_btn.setObjectName("SecondaryBtn")
        browse_btn.clicked.connect(self._browse_folder); folder_row.addWidget(browse_btn)
        fl2.addLayout(folder_row)
        cl.addWidget(folder_card)

        # ── תפקיד המחשב ──
        role_card = self._card(); rl = QFormLayout(role_card)
        rl.setContentsMargins(20,16,20,16); rl.setSpacing(10)
        rl.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self._role = QComboBox()
        self._role.addItems(self.ROLE_LABELS)
        cur_role = cfg.get("network_role", "standalone")
        self._role.setCurrentIndex(self.ROLE_KEYS.index(cur_role) if cur_role in self.ROLE_KEYS else 0)
        self._role.currentIndexChanged.connect(self._on_role_changed)
        rl.addRow("תפקיד המחשב:", self._role)

        # אזהרה: primary
        self._primary_warn = QLabel(
            "⚠️  לפני הגדרת 'ראשי' — ודא שאין מחשב ראשי אחר בתיקייה זו!\n"
            "לחץ 'בדוק תיקייה' לאחר בחירת הנתיב."
        )
        self._primary_warn.setStyleSheet("color:#f59e0b;font-size:11px;font-style:italic;")
        self._primary_warn.setWordWrap(True)
        self._primary_warn.setVisible(self._role.currentIndex() == 1)
        rl.addRow("", self._primary_warn)
        cl.addWidget(role_card)

        # ── הוראות ──
        instr_card = self._card(); il = QVBoxLayout(instr_card)
        il.setContentsMargins(20,14,20,14); il.setSpacing(8)
        il.addWidget(QLabel("📋  הוראות הגדרה", objectName="CardTitle"))
        steps = [
            "1. בחר תיקייה שיתופית ברשת (או תיקייה מקומית משותפת).",
            "2. במחשב הראשון — הגדר 'ראשי' ולחץ שמור. הוא יצור את קבצי ההגדרות.",
            "3. בכל מחשב נוסף — הגדר 'משני', בחר את אותה תיקייה, לחץ שמור.",
            "4. אם כבר קיימים קבצים בתיקייה (מהגדרה קודמת) — הנתונים נשמרים ולא נדרסים!",
            "5. כל מחשב כותב קובץ סטטוס בתיקיית Status כל 15 שניות.",
        ]
        for s in steps:
            lbl = QLabel(s); lbl.setObjectName("PanelSub"); lbl.setWordWrap(True)
            il.addWidget(lbl)
        cl.addWidget(instr_card)

        # ── מחשבים מחוברים ──
        status_card = self._card(); stl = QVBoxLayout(status_card)
        stl.setContentsMargins(20,14,20,14); stl.setSpacing(8)
        hdr_row = QHBoxLayout()
        hdr_row.addWidget(QLabel("🌐  מחשבים מחוברים:"))
        hdr_row.addStretch()
        refresh_btn = QPushButton("🔄 רענן"); refresh_btn.setObjectName("SecondaryBtn")
        refresh_btn.setFixedHeight(28); refresh_btn.clicked.connect(self._scan_status)
        hdr_row.addWidget(refresh_btn); stl.addLayout(hdr_row)
        self._status_list = QListWidget(); self._status_list.setMaximumHeight(140)
        self._status_list.addItem("(לחץ 'רענן' לאחר שמירה)")
        stl.addWidget(self._status_list)
        cl.addWidget(status_card)

        cl.addStretch()
        scroll.setWidget(content); l.addWidget(scroll)

        btns = QHBoxLayout()
        check_btn = QPushButton("🔍  בדוק תיקייה"); check_btn.setObjectName("SecondaryBtn")
        check_btn.clicked.connect(self._check_folder); btns.addWidget(check_btn)
        save_btn = QPushButton("💾  שמור"); save_btn.setObjectName("PrimaryBtn")
        save_btn.clicked.connect(self._save); btns.addWidget(save_btn)
        btns.addStretch(); l.addLayout(btns)
        self._refresh_timer.start()

    def _make_sub(self, text):
        lbl = QLabel(text); lbl.setObjectName("PanelSub"); lbl.setWordWrap(True)
        return lbl

    def _browse_folder(self):
        from PyQt6.QtWidgets import QFileDialog
        path = QFileDialog.getExistingDirectory(self, "בחר תיקייה שיתופית", self._folder.text() or "")
        if path:
            self._folder.setText(path.replace("/", "\\"))

    def _on_role_changed(self, idx):
        self._primary_warn.setVisible(idx == 1)

    def _check_folder(self):
        path = self._folder.text().strip()
        if not path:
            QMessageBox.warning(self, "שגיאה", "יש להזין נתיב לתיקייה תחילה"); return
        import os
        if not os.path.isdir(path):
            QMessageBox.warning(self, "שגיאה", f"התיקייה לא קיימת או אינה נגישה:\n{path}"); return

        # בדוק אם יש כבר מחשב ראשי מוגדר
        primary_info = self._find_existing_primary(path)
        cfg_file = os.path.join(path, "config.json")
        has_config = os.path.isfile(cfg_file)

        lines = [f"✅  התיקייה נגישה: {path}"]
        if has_config:
            lines.append("📄  נמצאו קבצי הגדרות קיימים — יישמרו ולא יידרסו!")
        else:
            lines.append("📭  אין קבצי הגדרות קיימים — יווצרו בשמירה.")
        if primary_info:
            lines.append(f"👑  מחשב ראשי קיים: {primary_info}")
        else:
            lines.append("👑  לא נמצא מחשב ראשי — ניתן להגדיר כ'ראשי'.")
        QMessageBox.information(self, "בדיקת תיקייה", "\n".join(lines))

    def _find_existing_primary(self, folder_path) -> str | None:
        """מחפש קובץ סטטוס עם primary=True בתיקיית Status"""
        import os, json, time
        status_dir = os.path.join(folder_path, "Status")
        if not os.path.isdir(status_dir):
            return None
        now = time.time()
        for fname in os.listdir(status_dir):
            if not fname.endswith(".json"):
                continue
            try:
                fp = os.path.join(status_dir, fname)
                age = now - os.path.getmtime(fp)
                if age > 60: continue   # מחשב לא פעיל
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("role") == "primary":
                    return data.get("hostname", fname)
            except Exception:
                pass
        return None

    def _scan_status(self):
        """סורק את תיקיית Status ומציג מחשבים פעילים"""
        self._status_list.clear()
        cfg = self.cm.get_general_cfg()
        folder = cfg.get("shared_folder", "")
        if not folder:
            self._status_list.addItem("(לא הוגדרה תיקייה שיתופית)")
            return
        import os, json, time
        status_dir = os.path.join(folder, "Status")
        if not os.path.isdir(status_dir):
            self._status_list.addItem("(תיקיית Status לא נמצאה — שמור תחילה)")
            return
        now = time.time()
        found = 0
        my_uid = cfg.get("machine_uid", "")
        for fname in sorted(os.listdir(status_dir)):
            if not fname.endswith(".json"):
                continue
            try:
                fp = os.path.join(status_dir, fname)
                age = now - os.path.getmtime(fp)
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
                uid  = data.get("uid", fname)
                host = data.get("hostname", uid)
                role = data.get("role", "secondary")
                ts   = data.get("ts", "")
                mark = "👑" if role == "primary" else "🖥️"
                me   = " (המחשב הנוכחי)" if uid == my_uid else ""
                status = "🟢 פעיל" if age < 45 else "🔴 לא מגיב"
                self._status_list.addItem(f"{mark}  {host}{me}   {status}   ({role})")
                found += 1
            except Exception:
                pass
        if found == 0:
            self._status_list.addItem("לא נמצאו מחשבים פעילים")

    def _write_my_status(self, folder, uid, hostname, role):
        """כותב קובץ סטטוס של המחשב הנוכחי"""
        import os, json
        from datetime import datetime
        status_dir = os.path.join(folder, "Status")
        os.makedirs(status_dir, exist_ok=True)
        fp = os.path.join(status_dir, f"{uid}.json")
        data = {
            "uid":      uid,
            "hostname": hostname,
            "role":     role,
            "ts":       datetime.now().isoformat(),
            "version":  "0.0.7",
        }
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _save(self):
        import os, uuid, socket
        path   = self._folder.text().strip()
        role   = self.ROLE_KEYS[self._role.currentIndex()]
        cfg    = self.cm.get_general_cfg()

        # אם standalone — שמור בלי תיקייה
        if role == "standalone":
            cfg["network_role"]    = "standalone"
            cfg["shared_folder"]   = ""
            self.cm.save()
            self._refresh_timer.stop()
            QMessageBox.information(self, "שמירה", "מצב עצמאי — ללא שיתוף ✓")
            return

        if not path:
            QMessageBox.warning(self, "שגיאה", "יש לבחור תיקייה שיתופית"); return
        if not os.path.isdir(path):
            ans = QMessageBox.question(self, "תיקייה לא קיימת",
                f"התיקייה אינה קיימת:\n{path}\n\nלנסות ליצור אותה?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if ans == QMessageBox.StandardButton.Yes:
                try: os.makedirs(path, exist_ok=True)
                except Exception as e:
                    QMessageBox.critical(self, "שגיאה", f"לא ניתן ליצור תיקייה:\n{e}"); return
            else:
                return

        # בדוק primary כפול
        if role == "primary":
            existing = self._find_existing_primary(path)
            my_uid = cfg.get("machine_uid", "")
            if existing and existing != cfg.get("machine_uid"):
                ans = QMessageBox.question(self, "מחשב ראשי קיים",
                    f"נמצא מחשב ראשי קיים: {existing}\n"
                    "האם להמשיך ולהגדיר כ'ראשי' בכל זאת? (יגרום לקונפליקט!)",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if ans != QMessageBox.StandardButton.Yes:
                    return

        # צור UID ייחודי אם אין
        if not cfg.get("machine_uid"):
            try:
                import uuid as _uuid
                mac = _uuid.getnode()
                cfg["machine_uid"] = f"{socket.gethostname()}-{hex(mac)[2:8].upper()}"
            except Exception:
                cfg["machine_uid"] = str(uuid.uuid4())[:8].upper()

        uid      = cfg["machine_uid"]
        hostname = socket.gethostname() if socket else uid

        # שמור הגדרות
        cfg["network_role"]  = role
        cfg["shared_folder"] = path
        self.cm.save()

        # כתוב סטטוס
        try:
            self._write_my_status(path, uid, hostname, role)
        except Exception as e:
            QMessageBox.warning(self, "אזהרה", f"הגדרות נשמרו, אך כתיבת קובץ סטטוס נכשלה:\n{e}")
            return

        self._refresh_timer.start()
        self._scan_status()
        QMessageBox.information(self, "שמירה",
            f"הגדרות נשמרו ✓\n\nתפקיד: {role}\nתיקייה: {path}\nמזהה: {uid}")

    def refresh(self):
        self._scan_status()


# ══════════════════════════════════════════════════════════════════
# מסך נעילה
# ══════════════════════════════════════════════════════════════════
class LockScreenPage(BasePage):
    def __init__(self, cm, dark, _=None):
        super().__init__(cm, dark); self._build()

    def _build(self):
        l = QVBoxLayout(self); l.setContentsMargins(28,28,28,28); l.setSpacing(16)
        l.addWidget(self._title("הגדרות מסך נעילה"))
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget(); cl = QVBoxLayout(content); cl.setContentsMargins(0,0,0,0); cl.setSpacing(14)

        ls = self.cm.get_lock_screen_cfg()

        # ── Hotkey מנהל ──
        hk_card = self._card(); hkl = QFormLayout(hk_card)
        hkl.setContentsMargins(20,16,20,16); hkl.setSpacing(10)
        hkl.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self._hotkey = QComboBox()
        self._hotkey.addItems(["F5","F6","F7","F8","F9","F10"])
        hk_map = {"F5":0,"F6":1,"F7":2,"F8":3,"F9":4,"F10":5}
        self._hotkey.setCurrentIndex(hk_map.get(ls.get("admin_hotkey","F8"),3))
        hkl.addRow("מקש כניסת מנהל (F8 ברירת מחדל):", self._hotkey)

        self._admin_pwd = QLineEdit(ls.get("admin_password","admin"))
        hkl.addRow("סיסמת מנהל מהירה:", self._admin_pwd)
        cl.addWidget(hk_card)

        # ── רקע ──
        bg_card = self._card(); bgl = QFormLayout(bg_card)
        bgl.setContentsMargins(20,16,20,16); bgl.setSpacing(10)
        bgl.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # גודל מסך מזוהה
        try:
            from PyQt6.QtWidgets import QApplication as _QApp
            scr = _QApp.primaryScreen().geometry()
            scr_txt = f"📐  גודל מסך מזוהה: {scr.width()} × {scr.height()} פיקסל"
            recommended = f"{scr.width()}×{scr.height()}"
        except Exception:
            scr_txt = "גודל מסך: לא זוהה"
            recommended = "1920×1080"
        scr_lbl = QLabel(scr_txt)
        scr_lbl.setStyleSheet("font-size:13px;font-weight:600;color:#2563eb;"
                              "background:rgba(37,99,235,0.08);border-radius:7px;padding:6px 12px;")
        bgl.addRow("", scr_lbl)

        color_row = QHBoxLayout()
        self._bg_color_btn = QPushButton()
        self._bg_color_btn.setFixedSize(40,28)
        self._bg_color = ls.get("bg_color","#e8f0fe")
        self._bg_color_btn.setStyleSheet(f"background:{self._bg_color};border:1px solid #888;border-radius:5px;")
        self._bg_color_btn.clicked.connect(self._pick_color)
        color_row.addWidget(self._bg_color_btn)
        self._bg_color_lbl = QLabel(self._bg_color)
        color_row.addWidget(self._bg_color_lbl); color_row.addStretch()
        bgl.addRow("צבע רקע:", color_row)

        img_row = QHBoxLayout()
        self._bg_img = QLineEdit(ls.get("bg_image",""))
        self._bg_img.setPlaceholderText(f"נתיב לתמונה — גודל מומלץ: {recommended} פיקסל")
        img_row.addWidget(self._bg_img)
        browse = QPushButton("עיון..."); browse.setObjectName("SecondaryBtn")
        browse.clicked.connect(self._browse_bg)
        img_row.addWidget(browse)
        bgl.addRow("תמונת רקע:", img_row)

        self._bg_fit = QComboBox()
        self._bg_fit.addItems(["fill – מלא","fit – התאם","stretch – מותח","center – מרכז"])
        fit_map = {"fill":0,"fit":1,"stretch":2,"center":3}
        self._bg_fit.setCurrentIndex(fit_map.get(ls.get("bg_fit","fill"),0))
        bgl.addRow("התאמת תמונה:", self._bg_fit)

        # הערת תיקיה משותפת
        shared_note_bg = QLabel("💡  בחיבור כמה מחשבים — הנח את תמונת הרקע בתיקיה משותפת ברשת")
        shared_note_bg.setStyleSheet("font-size:11px;color:#6b7280;font-style:italic;padding:4px 0;")
        shared_note_bg.setWordWrap(True)
        bgl.addRow("", shared_note_bg)
        cl.addWidget(bg_card)

        # ── הגדרות שעה ותאריך ──
        clk_card = self._card(); ckl = QFormLayout(clk_card)
        ckl.setContentsMargins(20,16,20,16); ckl.setSpacing(10)
        ckl.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        clk_title = QLabel("🕐  הגדרות שעה ותאריך")
        clk_title.setObjectName("CardTitle")
        ckl.addRow(clk_title)

        self._time_fmt = QComboBox()
        self._time_fmt.addItems(["24 שעות  (14:30)", "12 שעות  (02:30 PM)"])
        self._time_fmt.setCurrentIndex(0 if ls.get("clock_time_format","24") == "24" else 1)
        ckl.addRow("פורמט שעה:", self._time_fmt)

        self._date_mode = QComboBox()
        self._date_mode.addItems([
            "שניהם — לועזי ועברי",
            "עברי בלבד",
            "לועזי בלבד",
        ])
        mode_map = {"both": 0, "hebrew": 1, "gregorian": 2}
        self._date_mode.setCurrentIndex(mode_map.get(ls.get("clock_date_mode","both"), 0))
        ckl.addRow("הצגת תאריך:", self._date_mode)

        # בחירת צבע טקסט
        clock_color_row = QHBoxLayout()
        self._clock_color = ls.get("clock_text_color", "")
        self._clock_color_btn = QPushButton()
        self._clock_color_btn.setFixedSize(40, 28)
        clr_preview = self._clock_color or "#ffffff"
        self._clock_color_btn.setStyleSheet(
            f"background:{clr_preview};border:1px solid #888;border-radius:5px;"
        )
        self._clock_color_btn.clicked.connect(self._pick_clock_color)
        clock_color_row.addWidget(self._clock_color_btn)
        self._clock_color_lbl = QLabel(self._clock_color or "(ברירת מחדל)")
        clock_color_row.addWidget(self._clock_color_lbl)
        clr_reset = QPushButton("איפוס"); clr_reset.setObjectName("SecondaryBtn")
        clr_reset.setFixedHeight(28)
        clr_reset.clicked.connect(self._reset_clock_color)
        clock_color_row.addWidget(clr_reset)
        clock_color_row.addStretch()
        ckl.addRow("צבע שעה ותאריך:", clock_color_row)

        hint_he = QLabel("💡  לתאריך עברי מדויק: pip install hdate")
        hint_he.setStyleSheet("font-size:11px;color:#6b7280;font-style:italic;")
        ckl.addRow("", hint_he)
        cl.addWidget(clk_card)

        # ── עיצוב תיבת כניסה ──
        card_style_card = self._card(); csl = QVBoxLayout(card_style_card)
        csl.setContentsMargins(20,16,20,16); csl.setSpacing(10)
        cs_title = QLabel("🎨  עיצוב תיבת הכניסה")
        cs_title.setObjectName("CardTitle"); csl.addWidget(cs_title)

        cs_form = QFormLayout(); cs_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # צבע רקע תיבה
        card_color_row = QHBoxLayout()
        self._card_bg_transparent = QCheckBox("רקע שקוף לגמרי")
        self._card_bg_transparent.setChecked(ls.get("card_bg_transparent", False))
        card_color_row.addWidget(self._card_bg_transparent)

        self._card_bg_btn = QPushButton()
        self._card_bg_btn.setFixedSize(40,28)
        self._card_bg_color = ls.get("card_bg_color","")
        bg_preview = self._card_bg_color or "#ffffff"
        self._card_bg_btn.setStyleSheet(f"background:{bg_preview};border:1px solid #888;border-radius:5px;")
        self._card_bg_btn.clicked.connect(self._pick_card_bg)
        card_color_row.addWidget(self._card_bg_btn)
        self._card_bg_lbl = QLabel(self._card_bg_color or "(ברירת מחדל)")
        card_color_row.addWidget(self._card_bg_lbl); card_color_row.addStretch()
        cs_form.addRow("רקע תיבה:", card_color_row)

        # צבע קו מתאר
        border_row = QHBoxLayout()
        self._card_border_btn = QPushButton()
        self._card_border_btn.setFixedSize(40,28)
        self._card_border_color = ls.get("card_border_color","")
        border_preview = self._card_border_color or "#c8d7f0"
        self._card_border_btn.setStyleSheet(f"background:{border_preview};border:1px solid #888;border-radius:5px;")
        self._card_border_btn.clicked.connect(self._pick_card_border)
        border_row.addWidget(self._card_border_btn)
        self._card_border_lbl = QLabel(self._card_border_color or "(ברירת מחדל)")
        border_row.addWidget(self._card_border_lbl)
        border_row.addStretch()
        cs_form.addRow("צבע מתאר:", border_row)

        # עובי קו מתאר
        self._card_border_width = QSpinBox()
        self._card_border_width.setRange(0, 10); self._card_border_width.setSuffix(" px")
        self._card_border_width.setValue(ls.get("card_border_width", 1))
        cs_form.addRow("עובי מתאר:", self._card_border_width)

        csl.addLayout(cs_form)
        cl.addWidget(card_style_card)

        # ── מיקום תיבת כניסת משתמש ──
        pos_card = self._card(); posl = QVBoxLayout(pos_card)
        posl.setContentsMargins(20,16,20,16); posl.setSpacing(10)
        pos_title = QLabel("📍  מיקום תיבת כניסת משתמש")
        pos_title.setObjectName("CardTitle"); posl.addWidget(pos_title)
        pos_sub = QLabel("מרחק יחסי מקצוות המסך (פיקסלים) — ללא קשר לתיבת הפרסומות. השאר -1 למרכוז אוטומטי.")
        pos_sub.setObjectName("CardSub"); pos_sub.setWordWrap(True); posl.addWidget(pos_sub)

        pos_form = QFormLayout(); pos_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        def _make_pos_spin(val):
            s = QSpinBox(); s.setRange(-1, 9999); s.setSpecialValueText("אוטומטי (מרכז)")
            s.setValue(val if val is not None and val >= 0 else -1)
            return s

        self._pos_top    = _make_pos_spin(ls.get("login_margin_top"))
        self._pos_bottom = _make_pos_spin(ls.get("login_margin_bottom"))
        self._pos_right  = _make_pos_spin(ls.get("login_margin_right"))
        self._pos_left   = _make_pos_spin(ls.get("login_margin_left"))
        pos_form.addRow("מרחק מלמעלה (px):",  self._pos_top)
        pos_form.addRow("מרחק מלמטה (px):",   self._pos_bottom)
        pos_form.addRow("מרחק מימין (px):",    self._pos_right)
        pos_form.addRow("מרחק משמאל (px):",    self._pos_left)
        posl.addLayout(pos_form)
        cl.addWidget(pos_card)

        # ── פרסומות ──
        ads_card = self._card(); adsl = QVBoxLayout(ads_card)
        adsl.setContentsMargins(20,16,20,16); adsl.setSpacing(10)

        # גודל מסך לפרסומות
        try:
            from PyQt6.QtWidgets import QApplication as _QApp2
            scr2 = _QApp2.primaryScreen().geometry()
            _scr_w2, _scr_h2 = scr2.width(), scr2.height()
            ads_scr_lbl = QLabel(f"📐  גודל מסך: {_scr_w2} × {_scr_h2} פיקסל")
        except Exception:
            _scr_w2, _scr_h2 = 1920, 1080
            ads_scr_lbl = QLabel("גודל מסך: לא זוהה")
        ads_scr_lbl.setStyleSheet("font-size:12px;font-weight:600;color:#2563eb;"
                                   "background:rgba(37,99,235,0.08);border-radius:6px;padding:4px 10px;")
        adsl.addWidget(ads_scr_lbl)

        self._show_ads = QCheckBox("הפעל פאנל פרסומות")
        self._show_ads.setChecked(ls.get("show_ads",False)); adsl.addWidget(self._show_ads)

        ads_form = QFormLayout(); ads_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # גדלים מומלצים A4/A5/A6 — לפי 96dpi standard
        # A4=794×1123, A5=559×794, A6=397×559 (portrait @ 96dpi)
        ADS_PRESETS = {
            "A4 – 794×1123 px":  (794, 1123),
            "A5 – 559×794 px":   (559, 794),
            "A6 – 397×559 px":   (397, 559),
            "מותאם אישית":        None,
        }
        self._ads_preset = QComboBox()
        self._ads_preset.addItems(list(ADS_PRESETS.keys()))
        self._ads_preset.setCurrentIndex(1)  # ברירת מחדל A5
        adsl.addWidget(QLabel("גודל מוגדר מראש:"))
        adsl.addWidget(self._ads_preset)
        self._ADS_PRESETS = ADS_PRESETS

        def _apply_preset(idx):
            items = list(ADS_PRESETS.values())
            if items[idx]:
                w, h = items[idx]
                self._ads_width.setValue(w)
                self._ads_height.setValue(h)
        self._ads_preset.currentIndexChanged.connect(_apply_preset)

        def _make_ads_large_spin(key, default):
            s = QSpinBox(); s.setRange(100, 9999); s.setSuffix(" px"); s.setValue(ls.get(key, default))
            return s

        self._ads_width  = _make_ads_large_spin("ads_width",  559)
        self._ads_height = _make_ads_large_spin("ads_height", 794)
        ads_form.addRow("רוחב תיבה (px):",  self._ads_width)
        ads_form.addRow("גובה תיבה (px):",  self._ads_height)

        # מרחקי שוליים — עד 9999
        def _make_ads_margin_spin(key, default):
            s = QSpinBox(); s.setRange(0, 9999); s.setSuffix(" px"); s.setValue(ls.get(key, default))
            return s

        self._ads_margin_top    = _make_ads_margin_spin("ads_margin_top",    0)
        self._ads_margin_bottom = _make_ads_margin_spin("ads_margin_bottom",  0)
        self._ads_margin_left   = _make_ads_margin_spin("ads_margin_left",    0)
        self._ads_margin_right  = _make_ads_margin_spin("ads_margin_right",  16)
        ads_form.addRow("שוליים מלמעלה (px):",  self._ads_margin_top)
        ads_form.addRow("שוליים מלמטה (px):",   self._ads_margin_bottom)
        ads_form.addRow("שוליים משמאל (px):",    self._ads_margin_left)
        ads_form.addRow("שוליים מימין (px):",    self._ads_margin_right)

        self._ads_interval = QSpinBox(); self._ads_interval.setRange(2,60); self._ads_interval.setSuffix(" שניות")
        self._ads_interval.setValue(ls.get("ads_interval",5)); ads_form.addRow("זמן בין תמונות:", self._ads_interval)
        self._ads_show_arrows = QCheckBox("הצג חיצי ניווט בתחתית הפרסומת")
        self._ads_show_arrows.setChecked(ls.get("ads_show_arrows",True)); ads_form.addRow("", self._ads_show_arrows)
        self._ads_img_fit = QComboBox()
        self._ads_img_fit.addItems(["fit – התאם ללא מריחה (ברירת מחדל)","fill – מלא את כל התיבה","stretch – מתח"])
        fit_map2 = {"fit":0,"fill":1,"stretch":2}
        self._ads_img_fit.setCurrentIndex(fit_map2.get(ls.get("ads_img_fit","fit"),0))
        ads_form.addRow("התאמת תמונה:", self._ads_img_fit)
        adsl.addLayout(ads_form)

        # גודל מומלץ לתמונות לפי גודל תיבה
        self._ads_rec_lbl = QLabel()
        self._ads_rec_lbl.setStyleSheet("font-size:11px;color:#6b7280;font-style:italic;")

        def _update_rec_lbl():
            w = self._ads_width.value(); h = self._ads_height.value()
            self._ads_rec_lbl.setText(f"גודל מומלץ לתמונות: {w}×{h} פיקסל")
        self._ads_width.valueChanged.connect(lambda _: _update_rec_lbl())
        self._ads_height.valueChanged.connect(lambda _: _update_rec_lbl())
        _update_rec_lbl()

        # תמונות פרסומות — רב-בחירה + PDF
        ads_list_hdr = QHBoxLayout()
        ads_list_hdr.addWidget(QLabel("תמונות / PDF פרסומות:"))
        ads_list_hdr.addWidget(self._ads_rec_lbl)
        ads_list_hdr.addStretch()
        adsl.addLayout(ads_list_hdr)

        ads_list_row = QHBoxLayout()
        self._ads_list = QListWidget(); self._ads_list.setMaximumHeight(130)
        for img in ls.get("ads_images",[]): self._ads_list.addItem(img)
        ads_list_row.addWidget(self._ads_list)
        ads_btns = QVBoxLayout()
        add_btn = QPushButton("+ הוסף"); add_btn.setObjectName("PrimaryBtn")
        add_btn.clicked.connect(self._add_ad_file); ads_btns.addWidget(add_btn)
        del_img = QPushButton("מחק"); del_img.setObjectName("DangerBtn")
        del_img.clicked.connect(lambda: self._ads_list.takeItem(self._ads_list.currentRow()))
        ads_btns.addWidget(del_img); ads_btns.addStretch()
        ads_list_row.addLayout(ads_btns)
        adsl.addLayout(ads_list_row)

        # הערת תיקיה משותפת לפרסומות
        shared_note_ads = QLabel("💡  בחיבור כמה מחשבים — הנח את קבצי הפרסומות בתיקיה משותפת ברשת")
        shared_note_ads.setStyleSheet("font-size:11px;color:#6b7280;font-style:italic;padding:4px 0;")
        shared_note_ads.setWordWrap(True)
        adsl.addWidget(shared_note_ads)
        cl.addWidget(ads_card)

        cl.addStretch()
        scroll.setWidget(content); l.addWidget(scroll)

        save = QPushButton("💾  שמור הגדרות מסך נעילה"); save.setObjectName("PrimaryBtn")
        save.clicked.connect(self._save); l.addWidget(save)

    def _pick_card_bg(self):
        col = QColorDialog.getColor(QColor(self._card_bg_color or "#ffffff"), self, "בחר צבע רקע תיבה")
        if col.isValid():
            self._card_bg_color = col.name()
            self._card_bg_btn.setStyleSheet(f"background:{self._card_bg_color};border:1px solid #888;border-radius:5px;")
            self._card_bg_lbl.setText(self._card_bg_color)

    def _pick_card_border(self):
        col = QColorDialog.getColor(QColor(self._card_border_color or "#c8d7f0"), self, "בחר צבע מתאר תיבה")
        if col.isValid():
            self._card_border_color = col.name()
            self._card_border_btn.setStyleSheet(f"background:{self._card_border_color};border:1px solid #888;border-radius:5px;")
            self._card_border_lbl.setText(self._card_border_color)

    def _pick_clock_color(self):
        col = QColorDialog.getColor(QColor(self._clock_color or "#ffffff"), self, "בחר צבע שעה ותאריך")
        if col.isValid():
            self._clock_color = col.name()
            self._clock_color_btn.setStyleSheet(
                f"background:{self._clock_color};border:1px solid #888;border-radius:5px;"
            )
            self._clock_color_lbl.setText(self._clock_color)

    def _reset_clock_color(self):
        self._clock_color = ""
        self._clock_color_btn.setStyleSheet("background:#ffffff;border:1px solid #888;border-radius:5px;")
        self._clock_color_lbl.setText("(ברירת מחדל)")

    def _pick_color(self):
        col = QColorDialog.getColor(QColor(self._bg_color), self, "בחר צבע רקע")
        if col.isValid():
            self._bg_color = col.name()
            self._bg_color_btn.setStyleSheet(f"background:{self._bg_color};border:1px solid #888;border-radius:5px;")
            if hasattr(self, "_bg_color_lbl"):
                self._bg_color_lbl.setText(self._bg_color)

    def _browse_bg(self):
        path, _ = QFileDialog.getOpenFileName(self, "בחר תמונת רקע","",
                                               "Images (*.png *.jpg *.jpeg *.bmp *.webp)")
        if path: self._bg_img.setText(path)

    def _add_ad_file(self):
        """בחירת תמונות ו/או PDF מרובים בבת אחת"""
        paths, _ = QFileDialog.getOpenFileNames(
            self, "בחר קבצי פרסומות", "",
            "תמונות ו-PDF (*.png *.jpg *.jpeg *.bmp *.webp *.gif *.pdf)"
        )
        for path in paths:
            self._ads_list.addItem(path)

    def _save(self):
        try:
            hk_vals = ["F5","F6","F7","F8","F9","F10"]
            fit_vals = ["fill","fit","stretch","center"]
            ls = self.cm.config["lock_screen"]
            ls["admin_hotkey"]          = hk_vals[self._hotkey.currentIndex()]
            ls["admin_password"]        = self._admin_pwd.text()
            ls["bg_color"]              = self._bg_color
            ls["bg_image"]              = self._bg_img.text()
            ls["bg_fit"]                = fit_vals[self._bg_fit.currentIndex()]
            # הגדרות שעה ותאריך
            ls["clock_time_format"]     = "12" if self._time_fmt.currentIndex() == 1 else "24"
            date_mode_vals = ["both", "hebrew", "gregorian"]
            ls["clock_date_mode"]       = date_mode_vals[self._date_mode.currentIndex()]
            ls["clock_text_color"]      = self._clock_color
            # עיצוב תיבת כניסה
            ls["card_bg_transparent"]   = self._card_bg_transparent.isChecked()
            ls["card_bg_color"]         = self._card_bg_color
            ls["card_border_color"]     = self._card_border_color
            ls["card_border_width"]     = self._card_border_width.value()
            # מיקום תיבת כניסה
            def _pos_val(spin):
                v = spin.value(); return None if v < 0 else v
            ls["login_margin_top"]    = _pos_val(self._pos_top)
            ls["login_margin_bottom"] = _pos_val(self._pos_bottom)
            ls["login_margin_right"]  = _pos_val(self._pos_right)
            ls["login_margin_left"]   = _pos_val(self._pos_left)
            # פרסומות
            ls["show_ads"]              = self._show_ads.isChecked()
            ls["ads_width"]             = self._ads_width.value()
            ls["ads_height"]            = self._ads_height.value()
            ls["ads_margin_top"]        = self._ads_margin_top.value()
            ls["ads_margin_bottom"]     = self._ads_margin_bottom.value()
            ls["ads_margin_left"]       = self._ads_margin_left.value()
            ls["ads_margin_right"]      = self._ads_margin_right.value()
            ls["ads_interval"]          = self._ads_interval.value()
            ls["ads_show_arrows"]       = self._ads_show_arrows.isChecked()
            fit_vals2 = ["fit","fill","stretch"]
            ls["ads_img_fit"]           = fit_vals2[self._ads_img_fit.currentIndex()]
            ls["ads_images"]            = [self._ads_list.item(i).text() for i in range(self._ads_list.count())]
            self.cm.save()
            QMessageBox.information(self,"שמירה","הגדרות מסך הנעילה נשמרו ✓")


        except Exception as _save_err:
            import traceback, logging
            logging.getLogger(__name__).error(f'שמירה נכשלה: {traceback.format_exc()}')
            QMessageBox.critical(self, 'שגיאה', f'פעולה נכשלה: {_save_err}')
# ══════════════════════════════════════════════════════════════════
# מסך יציאה
# ══════════════════════════════════════════════════════════════════
class ExitScreenPage(BasePage):
    def __init__(self, cm, dark, _=None):
        super().__init__(cm, dark); self._build()

    def _build(self):
        l = QVBoxLayout(self); l.setContentsMargins(28,28,28,28); l.setSpacing(14)
        l.addWidget(self._title("הגדרות מסך יציאה"))
        cfg = self.cm.get_exit_screen_cfg()

        card = self._card(); cl = QFormLayout(card)
        cl.setContentsMargins(22,18,22,18); cl.setSpacing(12)
        cl.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._enabled_cb = QCheckBox("הפעל מסך יציאה"); self._enabled_cb.setChecked(cfg.get("enabled",True))
        cl.addRow("", self._enabled_cb)
        self._duration = QSpinBox(); self._duration.setRange(2,30); self._duration.setSuffix(" שניות")
        self._duration.setValue(cfg.get("duration_seconds",5)); cl.addRow("משך הצגה:", self._duration)
        self._close_apps = QCheckBox("סגור תוכנות פתוחות של המשתמש")
        self._close_apps.setChecked(cfg.get("close_user_apps",True)); cl.addRow("", self._close_apps)
        self._clean_temp = QCheckBox("נקה קבצים זמניים (%TEMP%)")
        self._clean_temp.setChecked(cfg.get("clean_temp",False)); cl.addRow("", self._clean_temp)
        l.addWidget(card)

        l.addWidget(QLabel("הודעות מותאמות אישית (מוצגות במסך היציאה):"))
        self._msgs_table = QTableWidget(0,3)
        self._msgs_table.setHorizontalHeaderLabels(["טקסט הודעה","צבע","גודל"])
        self._msgs_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._msgs_table.verticalHeader().setVisible(False)
        self._msgs_table.setMaximumHeight(200)
        for msg_cfg in cfg.get("custom_messages",[]):
            self._add_msg_row(msg_cfg.get("text",""), msg_cfg.get("style",""))
        l.addWidget(self._msgs_table)

        add_row = QHBoxLayout()
        self._new_msg = QLineEdit(); self._new_msg.setPlaceholderText("הודעה חדשה...")
        add_row.addWidget(self._new_msg)
        add_btn = QPushButton("+ הוסף"); add_btn.setObjectName("PrimaryBtn")
        add_btn.clicked.connect(self._add_msg); add_row.addWidget(add_btn)
        del_btn = QPushButton("מחק נבחר"); del_btn.setObjectName("DangerBtn")
        del_btn.clicked.connect(lambda: self._msgs_table.removeRow(self._msgs_table.currentRow()))
        add_row.addWidget(del_btn); l.addLayout(add_row)

        # ── USB ──
        usb_card = self._card(); ul2 = QVBoxLayout(usb_card)
        ul2.setContentsMargins(20,14,20,14); ul2.setSpacing(8)
        ul2.addWidget(QLabel("🔌  זיהוי כונן USB ביציאה"))
        self._detect_usb = QCheckBox("הצג אזהרה אם מחובר כונן USB (אוּן-קי)")
        cfg2 = self.cm.get_exit_screen_cfg()
        self._detect_usb.setChecked(cfg2.get("detect_usb", True)); ul2.addWidget(self._detect_usb)
        self._excluded_drives = QLineEdit(",".join(cfg2.get("excluded_drives",[])))
        self._excluded_drives.setPlaceholderText("אותיות כוננים קבועים להחרגה, לדוגמה: D,E")
        ul2.addWidget(QLabel("כוננים להחרגה (מופרדים בפסיק):"))
        ul2.addWidget(self._excluded_drives)
        l.addWidget(usb_card)

        save = QPushButton("💾  שמור"); save.setObjectName("PrimaryBtn")
        save.clicked.connect(self._save); l.addWidget(save)
        l.addStretch()

    def _add_msg_row(self, text, style):
        r = self._msgs_table.rowCount(); self._msgs_table.insertRow(r)
        self._msgs_table.setItem(r,0,QTableWidgetItem(text))
        self._msgs_table.setItem(r,1,QTableWidgetItem("#0d1b2a"))
        self._msgs_table.setItem(r,2,QTableWidgetItem("16"))

    def _add_msg(self):
        t = self._new_msg.text().strip()
        if t: self._add_msg_row(t,""); self._new_msg.clear()

    def _save(self):
        try:
            msgs = []
            for r in range(self._msgs_table.rowCount()):
                t = self._msgs_table.item(r,0)
                c = self._msgs_table.item(r,1)
                s = self._msgs_table.item(r,2)
                if t: msgs.append({"text":t.text(),"style":f"color:{c.text() if c else '#000'};font-size:{s.text() if s else '14'}px;"})
            cfg = self.cm.config["exit_screen"]
            cfg["enabled"]          = self._enabled_cb.isChecked()
            cfg["duration_seconds"] = self._duration.value()
            cfg["close_user_apps"]  = self._close_apps.isChecked()
            cfg["clean_temp"]       = self._clean_temp.isChecked()
            cfg["custom_messages"]  = msgs
            if hasattr(self,"_detect_usb"):
                cfg["detect_usb"] = self._detect_usb.isChecked()
                cfg["excluded_drives"] = [d.strip().upper() for d in self._excluded_drives.text().split(",") if d.strip()]
            self.cm.save()
            QMessageBox.information(self,"שמירה","הגדרות מסך יציאה נשמרו ✓")


        except Exception as _save_err:
            import traceback, logging
            logging.getLogger(__name__).error(f'שמירה נכשלה: {traceback.format_exc()}')
            QMessageBox.critical(self, 'שגיאה', f'פעולה נכשלה: {_save_err}')
# ══════════════════════════════════════════════════════════════════
# משתמשים
# ══════════════════════════════════════════════════════════════════
class UsersPage(BasePage):
    def __init__(self, cm, dark, _=None):
        super().__init__(cm, dark); self._build()

    def _build(self):
        l = QVBoxLayout(self); l.setContentsMargins(28,28,28,28); l.setSpacing(14)
        top = QHBoxLayout()
        top.addWidget(self._title("ניהול משתמשים"))
        top.addStretch()

        # כפתור הגדרות רישום
        reg_btn = QPushButton("📋  הגדרות רישום"); reg_btn.setObjectName("SecondaryBtn")
        reg_btn.clicked.connect(self._open_reg_settings); top.addWidget(reg_btn)

        add = QPushButton("+ משתמש חדש"); add.setObjectName("PrimaryBtn")
        add.clicked.connect(self._add_user); top.addWidget(add)
        exp = QPushButton("⬆ ייצא"); exp.setObjectName("SecondaryBtn")
        exp.clicked.connect(self._export); top.addWidget(exp)
        imp = QPushButton("⬇ ייבא"); imp.setObjectName("SecondaryBtn")
        imp.clicked.connect(self._import); top.addWidget(imp)
        l.addLayout(top)

        self._table = QTableWidget(0,8)
        self._table.setHorizontalHeaderLabels(["☐","שם משתמש","שם תצוגה","סיסמה","טלפון","זמן יומי","סטטוס","פעולות"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setColumnWidth(0,36)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        l.addWidget(self._table)

        bulk_row = QHBoxLayout()
        blk = QPushButton("🚫 חסום נבחרים"); blk.setObjectName("DangerBtn")
        blk.clicked.connect(self._bulk_block); bulk_row.addWidget(blk)
        enable = QPushButton("✓ הפעל נבחרים"); enable.setObjectName("GreenBtn")
        enable.clicked.connect(self._bulk_enable); bulk_row.addWidget(enable)
        delete = QPushButton("🗑 מחק נבחרים"); delete.setObjectName("DangerBtn")
        delete.clicked.connect(self._bulk_delete); bulk_row.addWidget(delete)
        bulk_row.addStretch(); l.addLayout(bulk_row)

        self._fill_table()

    def _fill_table(self):
        self._table.setRowCount(0)
        for uname, ud in self.cm.get_all_users().items():
            r = self._table.rowCount(); self._table.insertRow(r)
            self._table.setRowHeight(r,46)

            cb = QCheckBox(); cb.setProperty("username", uname)
            cb_w = QWidget(); cbl = QHBoxLayout(cb_w); cbl.setContentsMargins(4,0,4,0)
            cbl.addWidget(cb); self._table.setCellWidget(r,0,cb_w)

            self._table.setItem(r,1,QTableWidgetItem(uname))
            self._table.setItem(r,2,QTableWidgetItem(ud.get("display_name","")))
            self._table.setItem(r,3,QTableWidgetItem(ud.get("password","")))  # מוצגת
            self._table.setItem(r,4,QTableWidgetItem(ud.get("phone","")))
            daily = ud.get("time_limit_daily")
            self._table.setItem(r,5,QTableWidgetItem(f"{daily} דקות" if daily else "ללא"))
            blocked, _ = self.cm.is_user_blocked_now(uname)
            self._table.setItem(r,6,QTableWidgetItem("🔴 חסום" if blocked else "🟢 פעיל"))

            btns_w = QWidget(); btns_l = QHBoxLayout(btns_w)
            btns_l.setContentsMargins(4,4,4,4); btns_l.setSpacing(4)

            edit = QPushButton("✏️"); edit.setFixedSize(30,30)
            edit.setStyleSheet("border:none;background:transparent;font-size:15px;")
            edit.setToolTip("ערוך"); edit.clicked.connect(lambda _,u=uname: self._edit_user(u))
            btns_l.addWidget(edit)

            pkg = QPushButton("📦"); pkg.setFixedSize(30,30)
            pkg.setStyleSheet("border:none;background:transparent;font-size:15px;")
            pkg.setToolTip("הוסף חבילה"); pkg.clicked.connect(lambda _,u=uname: self._add_package(u))
            btns_l.addWidget(pkg)

            if not ud.get("is_admin"):
                delbtn = QPushButton("🗑️"); delbtn.setFixedSize(30,30)
                delbtn.setStyleSheet("border:none;background:transparent;font-size:15px;")
                delbtn.clicked.connect(lambda _,u=uname: self._delete_user(u))
                btns_l.addWidget(delbtn)

            self._table.setCellWidget(r,7,btns_w)

    def _add_user(self):
        dlg = UserDialog(self.cm, self.dark, parent=self)
        if dlg.exec(): self._fill_table()

    def _open_reg_settings(self):
        """חלונית הגדרות רישום עצמאי"""
        from PyQt6.QtWidgets import QDialog, QDialogButtonBox
        dlg = QDialog(self)
        dlg.setWindowTitle("הגדרות רישום עצמאי")
        dlg.setMinimumWidth(340)
        dlg.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        dlg.setStyleSheet(get_panel_style(self.dark))
        vl = QVBoxLayout(dlg); vl.setContentsMargins(20,20,20,20); vl.setSpacing(12)

        ls = self.cm.get_lock_screen_cfg()
        show_reg = QCheckBox("אפשר הרשמה עצמאית של משתמשים")
        show_reg.setChecked(ls.get("show_self_register", False))
        vl.addWidget(show_reg)

        # שדות חובה
        phone_cb = QCheckBox("טלפון — שדה חובה")
        phone_cb.setChecked(ls.get("register_phone_required", False))
        email_cb = QCheckBox("אימייל — שדה חובה")
        email_cb.setChecked(ls.get("register_email_required", False))

        fields_frame = QFrame(); fields_frame.setObjectName("Card")
        fl = QVBoxLayout(fields_frame); fl.setContentsMargins(12,10,12,10); fl.setSpacing(8)
        fl.addWidget(QLabel("שדות חובה ברישום:")); fl.addWidget(phone_cb); fl.addWidget(email_cb)
        vl.addWidget(fields_frame)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(dlg.accept); btns.rejected.connect(dlg.reject)
        vl.addWidget(btns)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            ls["show_self_register"]      = show_reg.isChecked()
            ls["register_phone_required"] = phone_cb.isChecked()
            ls["register_email_required"] = email_cb.isChecked()
            self.cm.save()
            QMessageBox.information(self, "שמירה", "הגדרות רישום נשמרו ✓")

    def _edit_user(self, username):
        dlg = UserDialog(self.cm, self.dark, username=username, parent=self)
        if dlg.exec(): self._fill_table()

    def _delete_user(self, username):
        if QMessageBox.question(self,"מחיקה",f"למחוק את '{username}'?",
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self.cm.delete_user(username); self._fill_table()

    def _add_package(self, username):
        pkgs = self.cm.get_packages()
        if not pkgs:
            QMessageBox.information(self,"חבילות","אין חבילות מוגדרות. הוסף חבילות בלשונית 'חבילות' תחילה."); return
        dlg = AddPackageDialog(pkgs, self.dark, self)
        if dlg.exec():
            self.cm.add_package_to_user(username, dlg.selected_id)
            QMessageBox.information(self,"הצלחה","החבילה נוספה ✓")

    def _get_selected_users(self):
        selected = []
        for r in range(self._table.rowCount()):
            cb_w = self._table.cellWidget(r,0)
            if cb_w:
                for child in cb_w.children():
                    if isinstance(child, QCheckBox) and child.isChecked():
                        uname_item = self._table.item(r,1)
                        if uname_item: selected.append(uname_item.text())
        return selected

    def _bulk_block(self):
        for u in self._get_selected_users(): self.cm.update_user(u, enabled=False)
        self._fill_table()

    def _bulk_enable(self):
        for u in self._get_selected_users(): self.cm.update_user(u, enabled=True)
        self._fill_table()

    def _bulk_delete(self):
        sel = self._get_selected_users()
        if not sel: return
        if QMessageBox.question(self,"מחיקה",f"למחוק {len(sel)} משתמשים?",
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            for u in sel: self.cm.delete_user(u)
            self._fill_table()

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self,"ייצא משתמשים","users_export.json","JSON (*.json)")
        if path:
            ok = self.cm.export_users(path)
            QMessageBox.information(self,"ייצוא","ייצוא הצליח ✓" if ok else "ייצוא נכשל ✗")

    def _import(self):
        path, _ = QFileDialog.getOpenFileName(self,"ייבא משתמשים","","JSON (*.json)")
        if path:
            ok = self.cm.import_users(path)
            if ok: self._fill_table(); QMessageBox.information(self,"ייבוא","ייבוא הצליח ✓")
            else: QMessageBox.critical(self,"שגיאה","ייבוא נכשל ✗")

    def refresh(self): self._fill_table()


class AddPackageDialog(QDialog):
    def __init__(self, packages, dark, parent):
        super().__init__(parent); self.selected_id = None
        self.setWindowTitle("בחר חבילה"); self.setFixedSize(360,300)
        self.setStyleSheet(get_panel_style(dark))
        l = QVBoxLayout(self); l.addWidget(QLabel("בחר חבילה להוסיף:"))
        self._list = QListWidget()
        for p in packages:
            item = QListWidgetItem(f"{p.get('name','')} – {p.get('value',0)} {'דקות' if p.get('type')=='time' else 'הדפסות'}")
            item.setData(Qt.ItemDataRole.UserRole, p.get("id")); self._list.addItem(item)
        l.addWidget(self._list)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._ok); btns.rejected.connect(self.reject); l.addWidget(btns)

    def _ok(self):
        item = self._list.currentItem()
        if item: self.selected_id = item.data(Qt.ItemDataRole.UserRole); self.accept()


class UserDialog(QDialog):
    def __init__(self, cm, dark, username=None, parent=None):
        super().__init__(parent)
        self.cm = cm; self.dark = dark; self.username = username
        self.editing = username is not None
        self.user = cm.get_user(username) if username else {}
        self.setWindowTitle("עריכת משתמש" if self.editing else "משתמש חדש")
        self.setMinimumWidth(480); self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setStyleSheet(get_panel_style(dark))
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        tabs = QTabWidget(); tabs.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        root.addWidget(tabs)

        is_admin_user = self.user.get("is_admin", False)

        # ── לשונית פרטים ──
        basic = QWidget(); bl = QFormLayout(basic)
        bl.setContentsMargins(18,14,18,14); bl.setSpacing(12)
        bl.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._uname = QLineEdit(self.username or "")
        self._uname.setReadOnly(self.editing)
        bl.addRow("שם משתמש:", self._uname)

        self._pwd = QLineEdit(self.user.get("password",""))
        bl.addRow("סיסמה:", self._pwd)

        self._phone = QLineEdit(self.user.get("phone",""))
        bl.addRow("טלפון:", self._phone)

        self._email = QLineEdit(self.user.get("email",""))
        bl.addRow("אימייל:", self._email)

        self._admin = QCheckBox("מנהל מערכת")
        self._admin.setChecked(self.user.get("is_admin",False))
        bl.addRow("", self._admin)

        self._enabled = QCheckBox("חשבון פעיל")
        self._enabled.setChecked(self.user.get("enabled",True))
        bl.addRow("", self._enabled)

        tabs.addTab(basic, "פרטים")

        # ── לשונית הגבלות ──
        rest_tab = QWidget(); rl = QVBoxLayout(rest_tab)
        rl.setContentsMargins(16,14,16,14); rl.setSpacing(10)

        # הגבלת זמן
        time_grp = QGroupBox("הגבלת זמן"); time_grp.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        tl = QFormLayout(time_grp); tl.setSpacing(8)

        self._daily_cb = QCheckBox("הגבלת זמן יומי")
        self._daily_cb.setChecked(self.user.get("time_limit_daily") is not None)
        self._daily_spin = QSpinBox(); self._daily_spin.setRange(1,1440); self._daily_spin.setSuffix(" דקות")
        self._daily_spin.setValue(self.user.get("time_limit_daily") or 60)
        tl.addRow("", self._daily_cb); tl.addRow("דקות ליום:", self._daily_spin)

        self._session_cb = QCheckBox("הגבלת זמן ברצף (max שימוש רצוף)")
        self._session_cb.setChecked(self.user.get("time_limit_session") is not None)
        self._session_spin = QSpinBox(); self._session_spin.setRange(1,480); self._session_spin.setSuffix(" דקות")
        self._session_spin.setValue(self.user.get("time_limit_session") or 60)
        self._cooldown_spin = QSpinBox(); self._cooldown_spin.setRange(1,120); self._cooldown_spin.setSuffix(" דקות")
        self._cooldown_spin.setValue(self.user.get("time_cooldown") or 30)
        tl.addRow("", self._session_cb)
        tl.addRow("מקסימום ברצף:", self._session_spin)
        tl.addRow("זמן המתנה:", self._cooldown_spin)
        rl.addWidget(time_grp)

        # הגבלות נוספות
        misc_grp = QGroupBox("הגבלות נוספות"); misc_grp.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        ml = QVBoxLayout(misc_grp); ml.setSpacing(6)

        self._is_app_r = QCheckBox("הגבל לתוכנות מסוימות (מוגדר בלשונית תוכנות)")
        self._is_app_r.setChecked(self.user.get("is_app_restricted",False))
        ml.addWidget(self._is_app_r)

        self._is_print_r = QCheckBox("הגבל הדפסות")
        self._is_print_r.setChecked(self.user.get("is_print_restricted",False))
        ml.addWidget(self._is_print_r)

        self._print_lim = QSpinBox(); self._print_lim.setRange(0,9999); self._print_lim.setSuffix(" עמודים")
        self._print_lim.setValue(self.user.get("print_limit") or 0)
        ml.addWidget(self._print_lim)

        self._msg_blocked = QCheckBox("חסום משליחת הודעות")
        self._msg_blocked.setChecked(self.user.get("messages_blocked",False))
        ml.addWidget(self._msg_blocked)
        rl.addWidget(misc_grp)
        rl.addStretch()

        tabs.addTab(rest_tab, "הגבלות")

        # ── כפתורים ──
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._save); btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def _save(self):
        try:
            uname = self._uname.text().strip()
            if not uname:
                QMessageBox.warning(self,"שגיאה","נדרש שם משתמש"); return
            pwd = self._pwd.text()
            if not self.editing and not pwd:
                QMessageBox.warning(self,"שגיאה","נדרשת סיסמה"); return

            is_admin = self._admin.isChecked()
            data = dict(
                display_name=uname,
                phone=self._phone.text(),
                email=self._email.text(),
                is_admin=is_admin,
                enabled=self._enabled.isChecked(),
                is_limited=not is_admin,
                is_app_restricted=self._is_app_r.isChecked(),
                is_print_restricted=self._is_print_r.isChecked(),
                messages_blocked=self._msg_blocked.isChecked(),
                time_limit_daily=self._daily_spin.value() if self._daily_cb.isChecked() else None,
                time_limit_session=self._session_spin.value() if self._session_cb.isChecked() else None,
                time_cooldown=self._cooldown_spin.value() if self._session_cb.isChecked() else None,
                print_limit=self._print_lim.value() if self._is_print_r.isChecked() else None,
            )
            if pwd: data["password"] = pwd
            if is_admin:
                data["is_limited"] = False
                data["time_limit_daily"] = None

            if self.editing:
                self.cm.update_user(uname, **data)
            else:
                ok = self.cm.create_user(uname, data.pop("password",""), **data)
                if not ok:
                    QMessageBox.warning(self,"שגיאה","שם משתמש כבר קיים"); return
            self.accept()


        except Exception as _save_err:
            import traceback, logging
            logging.getLogger(__name__).error(f'שמירה נכשלה: {traceback.format_exc()}')
            QMessageBox.critical(self, 'שגיאה', f'פעולה נכשלה: {_save_err}')
class PackagesPage(BasePage):
    def __init__(self, cm, dark, _=None):
        super().__init__(cm, dark); self._build()

    def _build(self):
        l = QVBoxLayout(self); l.setContentsMargins(28,28,28,28); l.setSpacing(14)
        top = QHBoxLayout(); top.addWidget(self._title("חבילות")); top.addStretch()
        add = QPushButton("+ חבילה חדשה"); add.setObjectName("PrimaryBtn")
        add.clicked.connect(self._add); top.addWidget(add); l.addLayout(top)

        self._table = QTableWidget(0,6)
        self._table.setHorizontalHeaderLabels(["שם","סוג","ערך","זמן יומי","מחיר","פעולות"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        l.addWidget(self._table)
        self._fill()
        l.addStretch()

    def _fill(self):
        self._table.setRowCount(0)
        for pkg in self.cm.get_packages():
            r = self._table.rowCount(); self._table.insertRow(r); self._table.setRowHeight(r,44)
            self._table.setItem(r,0,QTableWidgetItem(pkg.get("name","")))
            self._table.setItem(r,1,QTableWidgetItem("⏱ זמן" if pkg.get("type")=="time" else "🖨 הדפסות"))
            val = pkg.get("value",0)
            val_str = f"{val} דקות" if pkg.get("type")=="time" else f"{val} הדפסות"
            self._table.setItem(r,2,QTableWidgetItem(val_str))
            daily = pkg.get("daily_limit")
            self._table.setItem(r,3,QTableWidgetItem(f"{daily} דקות/יום" if daily else "—"))
            price = f"₪{pkg.get('price',0):.2f}" if pkg.get("has_price") else "—"
            self._table.setItem(r,4,QTableWidgetItem(price))
            btns_w = QWidget(); btns_l = QHBoxLayout(btns_w); btns_l.setContentsMargins(4,4,4,4)
            edit = QPushButton("✏️"); edit.setFixedSize(28,28)
            edit.setStyleSheet("border:none;background:transparent;font-size:14px;")
            edit.clicked.connect(lambda _,p=pkg: self._edit(p)); btns_l.addWidget(edit)
            delb = QPushButton("🗑️"); delb.setFixedSize(28,28)
            delb.setStyleSheet("border:none;background:transparent;font-size:14px;")
            delb.clicked.connect(lambda _,p=pkg: self._delete(p.get("id"))); btns_l.addWidget(delb)
            self._table.setCellWidget(r,5,btns_w)

    def _add(self):
        dlg = PackageDialog(self.dark, parent=self)
        if dlg.exec(): self.cm.add_package(dlg.get_data()); self._fill()

    def _edit(self, pkg):
        dlg = PackageDialog(self.dark, pkg=pkg, parent=self)
        if dlg.exec():
            data = dlg.get_data(); self.cm.update_package(pkg["id"], **data); self._fill()

    def _delete(self, pkg_id):
        if QMessageBox.question(self,"מחיקה","למחוק חבילה זו?",
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self.cm.delete_package(pkg_id); self._fill()

    def refresh(self): self._fill()


class PackageDialog(QDialog):
    def __init__(self, dark, pkg=None, parent=None):
        super().__init__(parent); self.pkg = pkg or {}
        self.setWindowTitle("חבילה חדשה" if not pkg else "עריכת חבילה")
        self.setMinimumSize(400,370); self.resize(400,370); self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setStyleSheet(get_panel_style(dark)); self._build()

    def _build(self):
        self.setStyleSheet(self.styleSheet() + "QSpinBox,QDoubleSpinBox,QLineEdit,QComboBox{min-height:34px;font-size:14px;}")
        l = QFormLayout(self); l.setContentsMargins(22,22,22,22); l.setSpacing(12)
        l.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self._name = QLineEdit(self.pkg.get("name","")); l.addRow("שם חבילה:", self._name)
        self._type = QComboBox(); self._type.addItems(["⏱ זמן","🖨 הדפסות"])
        self._type.setCurrentIndex(0 if self.pkg.get("type","time")=="time" else 1)
        l.addRow("סוג:", self._type)
        self._value = QSpinBox(); self._value.setRange(1,10000)
        self._value.setValue(self.pkg.get("value",60)); l.addRow("ערך:", self._value)
        self._daily_cb = QCheckBox("הגבל לדקות ביום")
        self._daily_cb.setChecked(self.pkg.get("daily_limit") is not None); l.addRow("",self._daily_cb)
        self._daily = QSpinBox(); self._daily.setRange(1,1440); self._daily.setSuffix(" דקות")
        self._daily.setValue(self.pkg.get("daily_limit") or 60); l.addRow("דקות ביום:", self._daily)
        self._price_cb = QCheckBox("יש מחיר"); self._price_cb.setChecked(self.pkg.get("has_price",False))
        l.addRow("",self._price_cb)
        self._price = QDoubleSpinBox(); self._price.setRange(0,9999); self._price.setSuffix(" ₪")
        self._price.setValue(self.pkg.get("price",0)); l.addRow("מחיר:", self._price)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject); l.addRow(btns)

    def get_data(self):
        return {
            "name": self._name.text(),
            "type": "time" if self._type.currentIndex()==0 else "print",
            "value": self._value.value(),
            "daily_limit": self._daily.value() if self._daily_cb.isChecked() else None,
            "has_price": self._price_cb.isChecked(),
            "price": self._price.value(),
        }


# ══════════════════════════════════════════════════════════════════
# מדפסות
# ══════════════════════════════════════════════════════════════════
class PrintersPage(BasePage):
    def __init__(self, cm, dark, _=None):
        super().__init__(cm, dark); self._build()

    def _build(self):
        l = QVBoxLayout(self); l.setContentsMargins(28,28,28,28); l.setSpacing(14)
        l.addWidget(self._title("ניטור מדפסות","הגדרת מגבלות הדפסה למדפסות"))

        refresh_btn = QPushButton("🔄 רענן רשימת מדפסות"); refresh_btn.setObjectName("SecondaryBtn")
        refresh_btn.clicked.connect(self._load_printers); l.addWidget(refresh_btn)

        self._table = QTableWidget(0,4)
        self._table.setHorizontalHeaderLabels(["שם מדפסת","מנוטר","תעריפים","סה\"כ הדפסות"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.setColumnWidth(1,70); self._table.setColumnWidth(2,130); self._table.setColumnWidth(3,90)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setVisible(False)
        l.addWidget(self._table)
        self._load_printers()

        save = QPushButton("💾  שמור"); save.setObjectName("PrimaryBtn")
        save.clicked.connect(self._save); l.addWidget(save)
        l.addStretch()

    def _get_real_printers(self):
        """מחזיר רשימת מדפסות אמיתיות מ-Windows"""
        printers = []
        try:
            import win32print
            for flags in [win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS]:
                for p in win32print.EnumPrinters(flags, None, 1):
                    name = p[2]
                    if name and name not in printers:
                        printers.append(name)
        except Exception:
            try:
                import subprocess
                out = subprocess.check_output(
                    ["wmic","printer","get","name"],
                    text=True, creationflags=0x08000000, timeout=5
                )
                for line in out.strip().split("\n")[1:]:
                    name = line.strip()
                    if name and name != "Name": printers.append(name)
            except Exception:
                printers = ["(לא נמצאו מדפסות — בדוק חיבור)"]
        return printers

    def _load_printers(self):
        self._table.setRowCount(0)
        printers = self._get_real_printers()
        cfg = self.cm.get_printers()

        for name in printers:
            r = self._table.rowCount(); self._table.insertRow(r); self._table.setRowHeight(r,48)
            self._table.setItem(r,0,QTableWidgetItem(name))

            p_cfg = cfg.get(name, {})

            # מנוטר
            cb = QCheckBox(); cb.setChecked(p_cfg.get("limited",False))
            self._table.setCellWidget(r,1,cb)

            # תעריפים לפי סוג (A4/A3 × שח"ל/צבע)
            rates = p_cfg.get("rates",{})
            rate_summary = "  |  ".join(
                f"{lbl}: ₪{rates.get(k,0):.1f}"
                for k,lbl in [("a4_bw","A4 שחל"),("a4_color","A4 צבע"),("a3_bw","A3 שחל"),("a3_color","A3 צבע")]
                if rates.get(k,0) > 0
            ) or "לא הוגדר"
            rate_btn = QPushButton(f"✏ הגדר תעריפים"); rate_btn.setObjectName("SecondaryBtn")
            rate_btn.setToolTip(rate_summary)
            rate_btn.clicked.connect(lambda _, n=name, pc=p_cfg: self._edit_rates(n, pc))
            self._table.setCellWidget(r,2,rate_btn)
            self._table.setItem(r,3,QTableWidgetItem(str(p_cfg.get("total_prints",0))))

    def _edit_rates(self, printer_name: str, p_cfg: dict):
        try:
            dlg = PrinterRateDialog(printer_name, p_cfg.get("rates",{}), self.dark, self)
            if dlg.exec():
                printers = self.cm.config.setdefault("printers",{})
                if printer_name not in printers:
                    printers[printer_name] = {}
                printers[printer_name]["rates"] = dlg.get_rates()
                self.cm.save()
                self._load_printers()   # רענן תצוגה
                QMessageBox.information(self,"שמירה","תעריפים נשמרו ✓")
        except Exception as e:
            import traceback, logging
            logging.getLogger(__name__).error(f"_edit_rates קרסה: {traceback.format_exc()}")
            QMessageBox.critical(self, "שגיאה", f"שגיאה בפתיחת דיאלוג תעריפים:\n{e}")

    def _save(self):
        try:
            printers = self.cm.config.get("printers",{})
            rate_spins = getattr(self,"_rate_spins",{})
            for r in range(self._table.rowCount()):
                name_item = self._table.item(r,0)
                if not name_item: continue
                name = name_item.text()
                cb_w = self._table.cellWidget(r,1)
                limited = cb_w.isChecked() if isinstance(cb_w,QCheckBox) else False
                rates = {}
                if name in rate_spins:
                    for k,sp in rate_spins[name].items():
                        rates[k] = sp.value()
                existing = printers.get(name,{})
                printers[name] = {
                    "limited": limited,
                    "rates": rates,
                    "total_prints": existing.get("total_prints",0),
                }
            self.cm.config["printers"] = printers; self.cm.save()
            QMessageBox.information(self,"שמירה","הגדרות מדפסות נשמרו ✓")


        except Exception as _save_err:
            import traceback, logging
            logging.getLogger(__name__).error(f'שמירה נכשלה: {traceback.format_exc()}')
            QMessageBox.critical(self, 'שגיאה', f'פעולה נכשלה: {_save_err}')
# ══════════════════════════════════════════════════════════════════
# תוכנות
# ══════════════════════════════════════════════════════════════════
class AppsPage(BasePage):
    def __init__(self, cm, dark, _=None):
        super().__init__(cm, dark); self._build()

    def _build(self):
        l = QVBoxLayout(self); l.setContentsMargins(28,28,28,28); l.setSpacing(14)
        l.addWidget(self._title("ניהול תוכנות"))
        tabs = QTabWidget(); tabs.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        # ── חסימה כללית ──
        global_tab = QWidget(); gl = QVBoxLayout(global_tab)
        gl.setContentsMargins(14,14,14,14); gl.setSpacing(10)
        gl.addWidget(QLabel("תוכנות חסומות לכלל המשתמשים:"))
        self._global_list = QListWidget(); self._global_list.setMaximumHeight(180)
        for app in self.cm.config.get("blocked_apps_global",[]): self._global_list.addItem(app)
        gl.addWidget(self._global_list)
        add_row = QHBoxLayout()
        self._global_input = QLineEdit(); self._global_input.setPlaceholderText("שם תוכנה (לדוגמה: notepad.exe)")
        add_row.addWidget(self._global_input)
        browse = QPushButton("עיון"); browse.setObjectName("SecondaryBtn")
        browse.clicked.connect(lambda: self._browse_app(self._global_input)); add_row.addWidget(browse)
        add_g = QPushButton("+ הוסף"); add_g.setObjectName("PrimaryBtn")
        add_g.clicked.connect(lambda: (self._global_list.addItem(self._global_input.text()) or self._global_input.clear()) if self._global_input.text().strip() else None)
        add_row.addWidget(add_g)
        del_g = QPushButton("מחק"); del_g.setObjectName("DangerBtn")
        del_g.clicked.connect(lambda: self._global_list.takeItem(self._global_list.currentRow()))
        add_row.addWidget(del_g); gl.addLayout(add_row)
        tabs.addTab(global_tab, "⛔ חסימה כללית")

        # ── חסימה למוגבלים ──
        lim_tab = QWidget(); ll = QVBoxLayout(lim_tab)
        ll.setContentsMargins(14,14,14,14); ll.setSpacing(10)
        ll.addWidget(QLabel("תוכנות חסומות למשתמשים שסומנו כ'מוגבל לתוכנות':"))
        self._lim_list = QListWidget(); self._lim_list.setMaximumHeight(180)
        for app in self.cm.config.get("blocked_apps_limited",[]): self._lim_list.addItem(app)
        ll.addWidget(self._lim_list)
        add_row2 = QHBoxLayout()
        self._lim_input = QLineEdit(); self._lim_input.setPlaceholderText("שם תוכנה")
        add_row2.addWidget(self._lim_input)
        browse2 = QPushButton("עיון"); browse2.setObjectName("SecondaryBtn")
        browse2.clicked.connect(lambda: self._browse_app(self._lim_input)); add_row2.addWidget(browse2)
        add_l = QPushButton("+ הוסף"); add_l.setObjectName("PrimaryBtn")
        add_l.clicked.connect(lambda: (self._lim_list.addItem(self._lim_input.text()) or self._lim_input.clear()) if self._lim_input.text().strip() else None)
        add_row2.addWidget(add_l)
        del_l = QPushButton("מחק"); del_l.setObjectName("DangerBtn")
        del_l.clicked.connect(lambda: self._lim_list.takeItem(self._lim_list.currentRow()))
        add_row2.addWidget(del_l); ll.addLayout(add_row2)
        tabs.addTab(lim_tab, "🔒 חסימה למוגבלים")

        l.addWidget(tabs)
        save = QPushButton("💾  שמור"); save.setObjectName("PrimaryBtn")
        save.clicked.connect(self._save); l.addWidget(save)
        l.addStretch()

    def _browse_app(self, line_edit):
        path, _ = QFileDialog.getOpenFileName(self,"בחר קובץ תוכנה","C:\\Program Files",
                                               "Programs (*.exe)")
        if path:
            line_edit.setText(os.path.basename(path))

    def _save(self):
        try:
            self.cm.config["blocked_apps_global"] = [self._global_list.item(i).text() for i in range(self._global_list.count())]
            self.cm.config["blocked_apps_limited"] = [self._lim_list.item(i).text() for i in range(self._lim_list.count())]
            self.cm.save()
            QMessageBox.information(self,"שמירה","הגדרות תוכנות נשמרו ✓")


        except Exception as _save_err:
            import traceback, logging
            logging.getLogger(__name__).error(f'שמירה נכשלה: {traceback.format_exc()}')
            QMessageBox.critical(self, 'שגיאה', f'פעולה נכשלה: {_save_err}')
# ══════════════════════════════════════════════════════════════════
# חסימות כלליות
# ══════════════════════════════════════════════════════════════════
class BlocksPage(BasePage):
    def __init__(self, cm, dark, _=None):
        super().__init__(cm, dark); self._build()

    def _build(self):
        l = QVBoxLayout(self); l.setContentsMargins(28,28,28,28); l.setSpacing(14)
        l.addWidget(self._title("חסימות כלליות","חסימת כניסה למחשב לכלל המשתמשים (מלבד מנהל)"))

        top = QHBoxLayout(); top.addWidget(QLabel("רשימת חסימות פעילות:")); top.addStretch()
        add = QPushButton("+ הוסף חסימה"); add.setObjectName("PrimaryBtn")
        add.clicked.connect(self._add); top.addWidget(add); l.addLayout(top)

        self._list = QListWidget()
        self._fill_list()
        l.addWidget(self._list)

        del_btn = QPushButton("🗑 מחק נבחר"); del_btn.setObjectName("DangerBtn")
        del_btn.clicked.connect(self._delete); l.addWidget(del_btn)

        # ── חסימת שבת וחגים ──
        shabbat_card = self._card(); sl2 = QVBoxLayout(shabbat_card)
        sl2.setContentsMargins(18,14,18,14); sl2.setSpacing(10)
        sl2.addWidget(QLabel("✡️  חסימה בשבת וחגים יהודיים"))

        gen = self.cm.get_general_cfg()
        self._block_shabbat = QCheckBox("הפעל חסימה בשבת וחגים לפי הלוח העברי")
        self._block_shabbat.setChecked(gen.get("block_shabbat_chag", False))
        sl2.addWidget(self._block_shabbat)

        shab_form = QFormLayout(); shab_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight); shab_form.setSpacing(8)
        self._shab_before = QSpinBox(); self._shab_before.setRange(0,120); self._shab_before.setSuffix(" דקות")
        self._shab_before.setValue(gen.get("shabbat_mins_before", 40))
        shab_form.addRow("חסום לפני שקיעה:", self._shab_before)

        self._shab_after = QSpinBox(); self._shab_after.setRange(0,120); self._shab_after.setSuffix(" דקות")
        self._shab_after.setValue(gen.get("shabbat_mins_after", 40))
        shab_form.addRow("שחרר אחרי שקיעה:", self._shab_after)

        self._shab_lat = QLineEdit(str(gen.get("location_lat", 31.7683)))
        shab_form.addRow("קו רוחב (lat):", self._shab_lat)
        self._shab_lon = QLineEdit(str(gen.get("location_lon", 35.2137)))
        shab_form.addRow("קו אורך (lon):", self._shab_lon)

        coord_hint = QLabel("💡 הזן קו רוחב/אורך ידנית, או בחר עיר:")
        coord_hint.setObjectName("PanelSub")
        shab_form.addRow("", coord_hint)
        city_btn = QPushButton("🏙 בחר עיר..."); city_btn.setObjectName("SecondaryBtn")
        city_btn.clicked.connect(self._pick_city); shab_form.addRow("", city_btn)
        holidays_btn = QPushButton("📅 הצג / ערוך רשימת חגים"); holidays_btn.setObjectName("SecondaryBtn")
        holidays_btn.clicked.connect(self._show_holidays); shab_form.addRow("", holidays_btn)

        dep_note = QLabel("📦 לחגים נוספים: pip install hdate  (שבת עובד ללא תלויות)")
        dep_note.setObjectName("PanelSub"); dep_note.setWordWrap(True)
        sl2.addLayout(shab_form); sl2.addWidget(dep_note)

        shab_save = QPushButton("💾  שמור הגדרות שבת"); shab_save.setObjectName("PrimaryBtn")
        shab_save.clicked.connect(self._save_shabbat); sl2.addWidget(shab_save)
        l.addWidget(shabbat_card)
        l.addStretch()

    CITIES = [
        ("ירושלים",         31.7683, 35.2137),
        ("תל אביב",          32.0853, 34.7818),
        ("חיפה",             32.7940, 34.9896),
        ("באר שבע",          31.2530, 34.7915),
        ("אשדוד",            31.8040, 34.6550),
        ("אשקלון",           31.6688, 34.5743),
        ("פתח תקווה",        32.0872, 34.8867),
        ("בני ברק",          32.0833, 34.8333),
        ("ביתר עילית",       31.6996, 35.1213),
        ("מודיעין עילית",    31.9285, 35.0445),
        ("מודיעין-מכבים",    31.8967, 35.0100),
        ("נתניה",            32.3215, 34.8532),
        ("ראשון לציון",      31.9730, 34.7925),
        ("רחובות",           31.8928, 34.8115),
        ("חולון",            32.0114, 34.7795),
        ("בת ים",            32.0236, 34.7502),
        ("קריית שמונה",      33.2073, 35.5695),
        ("טבריה",            32.7958, 35.5302),
        ("צפת",              32.9647, 35.4960),
        ("נצרת",             32.6993, 35.2960),
        ("אילת",             29.5577, 34.9519),
        ("רמת גן",           32.0684, 34.8248),
        ("גבעתיים",          32.0683, 34.8122),
        ("קריית ביאליק",     32.8381, 35.0930),
        ("לוד",              31.9530, 34.8953),
        ("רמלה",             31.9298, 34.8710),
        ("נס ציונה",         31.9305, 34.7990),
        ("ירוחם",            30.9882, 34.9295),
        ("קריית גת",         31.6087, 34.7673),
        ("אופקים",           31.3122, 34.6225),
        ("דימונה",           31.0688, 35.0327),
        ("עפולה",            32.6074, 35.2895),
        ("חדרה",             32.4338, 34.9196),
        ("כפר סבא",          32.1773, 34.9077),
        ("הרצליה",           32.1651, 34.8439),
        ("רעננה",            32.1840, 34.8730),
        ("גן יבנה",          31.7891, 34.7061),
        ("אריאל",            32.1052, 35.1680),
        ("מעלה אדומים",      31.7711, 35.2976),
        ("בית שמש",          31.7457, 35.0063),
        ("טלזסטון",         31.7583, 35.1138),
        ("קריית ארבע",       31.5302, 35.1122),
    ]

    JEWISH_HOLIDAYS = [
        ("ראש השנה",      "rosh_hashana"),
        ("יום כיפור",     "yom_kippur"),
        ("סוכות",         "sukkot"),
        ("שמחת תורה",    "simchat_torah"),
        ("חנוכה",         "chanukah"),
        ("טו בשבט",     "tu_bishvat"),
        ("פורים",         "purim"),
        ("פסח",           "pesach"),
        ("יום העצמאות",   "yom_haatzmaut"),
        ("לג בעומר",    "lag_baomer"),
        ("שבועות",        "shavuot"),
        ("תשעה באב",     "tisha_beav"),
    ]

    def _pick_city(self):
        from PyQt6.QtWidgets import QInputDialog
        names = [c[0] for c in self.CITIES]
        name, ok = QInputDialog.getItem(self, "בחר עיר", "עיר:", names, 0, False)
        if ok and name:
            for cname, lat, lon in self.CITIES:
                if cname == name:
                    self._shab_lat.setText(str(lat))
                    self._shab_lon.setText(str(lon))
                    break

    def _show_holidays(self):
        dlg = HolidayListDialog(
            self.cm.config.get("general",{}).get("blocked_holidays", [h[1] for h in self.JEWISH_HOLIDAYS]),
            self.JEWISH_HOLIDAYS, self.dark, self
        )
        if dlg.exec():
            self.cm.config["general"]["blocked_holidays"] = dlg.get_selected()
            self.cm.save()
            QMessageBox.information(self,"שמירה","רשימת חגים עודכנה ✓")

    def _save_shabbat(self):
        try:
            lat = float(self._shab_lat.text())
            lon = float(self._shab_lon.text())
        except ValueError:
            QMessageBox.warning(self,"שגיאה","קו רוחב/אורך חייב להיות מספר"); return
        cfg = self.cm.config["general"]
        cfg["block_shabbat_chag"]    = self._block_shabbat.isChecked()
        cfg["shabbat_mins_before"]   = self._shab_before.value()
        cfg["shabbat_mins_after"]    = self._shab_after.value()
        cfg["location_lat"]          = lat
        cfg["location_lon"]          = lon
        self.cm.save()
        QMessageBox.information(self,"שמירה","הגדרות שבת נשמרו ✓")

    def _fill_list(self):
        self._list.clear()
        for block in self.cm.get_global_blocks():
            btype = block.get("type","")
            name  = block.get("name","")
            tf    = block.get("time_from", block.get("from",""))
            tt    = block.get("time_to",   block.get("to",""))
            hours = f" | {tf}–{tt}" if tf and tt else ""
            if btype == "weekday":
                days_heb = ["א׳","ב׳","ג׳","ד׳","ה׳","ו׳","שב׳"]
                day_names = ",".join(days_heb[d] for d in block.get("days",[]) if d < 7)
                desc = f"📅 {name} | ימים: {day_names}{hours}"
            elif btype == "daterange":
                desc = f"📆 {name} | {block.get('date_from','')}–{block.get('date_to','')}{hours}"
            elif btype == "hours":
                desc = f"🕐 {name} | {tf}–{tt}"
            elif btype == "date":
                desc = f"📆 {name} | {block.get('date','')}"
            else:
                desc = name
            item = QListWidgetItem(desc)
            item.setData(Qt.ItemDataRole.UserRole, block)
            self._list.addItem(item)

    def _add(self):
        dlg = BlockDialog(self.dark, self)
        if dlg.exec():
            self.cm.config.setdefault("global_blocks",[]).append(dlg.get_data())
            self.cm.save(); self._fill_list()

    def _delete(self):
        item = self._list.currentItem()
        if not item: return
        block = item.data(Qt.ItemDataRole.UserRole)
        blocks = self.cm.config.get("global_blocks",[])
        self.cm.config["global_blocks"] = [b for b in blocks if b != block]
        self.cm.save(); self._fill_list()

    def refresh(self): self._fill_list()


class BlockDialog(QDialog):
    """
    דיאלוג הוספת חסימה מחודש:
    - סוג 'ימים בשבוע': שעות (משעה/עד שעה) + בחירת ימים א-שבת
    - סוג 'תאריכים': שעות + טווח תאריכים מ-X עד Y
    ניתן להוסיף כמה תרחישים בבת אחת.
    """
    def __init__(self, dark, parent):
        super().__init__(parent)
        self.setWindowTitle("הוסף חסימה")
        self.setMinimumWidth(460)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setStyleSheet(get_panel_style(dark))
        self._build()

    def _build(self):
        l = QVBoxLayout(self); l.setContentsMargins(22,20,22,20); l.setSpacing(14)

        # שם
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("שם חסימה:"))
        self._name = QLineEdit(); self._name.setPlaceholderText("לדוגמה: לילה, שישי ערב...")
        name_row.addWidget(self._name); l.addLayout(name_row)

        # סוג
        type_row = QHBoxLayout()
        type_row.addWidget(QLabel("סוג:"))
        self._type = QComboBox()
        self._type.addItems(["ימים בשבוע", "טווח תאריכים"])
        self._type.currentIndexChanged.connect(self._update_form)
        type_row.addWidget(self._type); l.addLayout(type_row)

        # שעות (משותף לשני הסוגים)
        hours_frame = QFrame(); hours_frame.setObjectName("Card")
        hfl = QFormLayout(hours_frame); hfl.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        hfl.setContentsMargins(14,10,14,10); hfl.setSpacing(8)
        hfl.addRow(QLabel("⏰  שעות חסימה:"))
        self._from = QTimeEdit(QTime(22,0)); self._from.setDisplayFormat("HH:mm")
        self._to   = QTimeEdit(QTime(8,0));  self._to.setDisplayFormat("HH:mm")
        hfl.addRow("משעה:", self._from)
        hfl.addRow("עד שעה:", self._to)
        l.addWidget(hours_frame)

        # ימים בשבוע
        self._days_frame = QFrame(); self._days_frame.setObjectName("Card")
        dfl = QVBoxLayout(self._days_frame)
        dfl.setContentsMargins(14,10,14,10); dfl.setSpacing(6)
        dfl.addWidget(QLabel("📅  ימים פעילים:"))
        days_row = QHBoxLayout(); days_row.setSpacing(4)
        days_heb = ["א׳","ב׳","ג׳","ד׳","ה׳","ו׳","שב׳"]
        self._day_cbs = []
        for d in days_heb:
            cb = QCheckBox(d); cb.setChecked(True)
            self._day_cbs.append(cb); days_row.addWidget(cb)
        days_row.addStretch()
        # כפתור "בחר הכל"
        all_btn = QPushButton("הכל"); all_btn.setObjectName("SecondaryBtn")
        all_btn.setFixedHeight(26)
        all_btn.clicked.connect(lambda: [cb.setChecked(True) for cb in self._day_cbs])
        days_row.addWidget(all_btn)
        dfl.addLayout(days_row)
        l.addWidget(self._days_frame)

        # טווח תאריכים
        self._dates_frame = QFrame(); self._dates_frame.setObjectName("Card")
        dtfl = QFormLayout(self._dates_frame)
        dtfl.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        dtfl.setContentsMargins(14,10,14,10); dtfl.setSpacing(8)
        dtfl.addRow(QLabel("📆  טווח תאריכים:"))
        self._date_from = QDateEdit(QDate.currentDate()); self._date_from.setCalendarPopup(True)
        self._date_from.setDisplayFormat("dd/MM/yyyy")
        self._date_to = QDateEdit(QDate.currentDate().addDays(1)); self._date_to.setCalendarPopup(True)
        self._date_to.setDisplayFormat("dd/MM/yyyy")
        dtfl.addRow("מתאריך:", self._date_from)
        dtfl.addRow("עד תאריך:", self._date_to)
        l.addWidget(self._dates_frame)

        # הצג הודעת חסימה
        self._show_msg = QCheckBox("הצג הודעה על מסך הנעילה שהמחשב חסום")
        self._show_msg.setChecked(True)
        l.addWidget(self._show_msg)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        l.addWidget(btns)

        self._update_form(0)

    def _update_form(self, idx):
        self._days_frame.setVisible(idx == 0)
        self._dates_frame.setVisible(idx == 1)

    def get_data(self) -> dict:
        idx = self._type.currentIndex()
        base = {
            "name": self._name.text() or "חסימה",
            "time_from": self._from.time().toString("HH:mm"),
            "time_to":   self._to.time().toString("HH:mm"),
            "show_msg":  self._show_msg.isChecked(),
        }
        if idx == 0:
            base["type"] = "weekday"
            base["days"] = [i for i, cb in enumerate(self._day_cbs) if cb.isChecked()]
        else:
            base["type"]      = "daterange"
            base["date_from"] = self._date_from.date().toString("yyyy-MM-dd")
            base["date_to"]   = self._date_to.date().toString("yyyy-MM-dd")
        return base


# ══════════════════════════════════════════════════════════════════
# דיאלוג רשימת חגים
# ══════════════════════════════════════════════════════════════════
# ימים בתוך כל חג (מיפוי key → רשימת ימים)
HOLIDAY_DAYS = {
    "rosh_hashana":  ["א׳ תשרי", "ב׳ תשרי"],
    "yom_kippur":    ["י׳ תשרי"],
    "sukkot":        ["טו תשרי", "טז תשרי", "חול המועד סוכות (5 ימים)", "הושענא רבה"],
    "simchat_torah": ["שמיני עצרת", "שמחת תורה"],
    "chanukah":      [f"יום {i+1} דחנוכה" for i in range(8)],
    "tu_bishvat":    ["טו בשבט"],
    "purim":         ["פורים", "שושן פורים"],
    "pesach":        ["א׳ פסח", "ב׳ פסח", "חול המועד פסח (4 ימים)", "ז׳ פסח", "ח׳ פסח"],
    "lag_baomer":    ["לג בעומר"],
    "shavuot":       ["א׳ שבועות", "ב׳ שבועות"],
    "tisha_beav":    ["תשעה באב"],
}


class HolidayListDialog(QDialog):
    """
    רשימת חגים עם תיבות סימון ואפשרות פתיחת ימים בתוך כל חג.
    """
    def __init__(self, selected: list, holidays: list, dark: bool, parent=None):
        super().__init__(parent)
        self.setWindowTitle("הגדרת חגים לחסימה")
        self.setMinimumSize(460, 540)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setStyleSheet(get_panel_style(dark))
        self._selected   = set(selected)
        self._holidays   = [(name, key) for name, key in holidays if key != "yom_haatzmaut"]
        self._day_checks: dict = {}
        self._build()

    def _build(self):
        vl = QVBoxLayout(self); vl.setContentsMargins(18,18,18,14); vl.setSpacing(10)
        vl.addWidget(QLabel("סמן חגים לחסימה. לחץ ← להצגת הימים הספציפיים:"))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(4, 4, 4, 4)
        cl.setSpacing(2)

        for hname, hkey in self._holidays:
            # מיכל כולל לחג — QWidget עם VBoxLayout
            holiday_widget = QWidget()
            hwl = QVBoxLayout(holiday_widget)
            hwl.setContentsMargins(0, 0, 0, 0)
            hwl.setSpacing(0)

            # שורת כותרת החג
            row_widget = QWidget()
            row_l = QHBoxLayout(row_widget)
            row_l.setContentsMargins(2, 3, 2, 3)
            row_l.setSpacing(6)

            cb = QCheckBox(hname)
            cb.setChecked(hkey in self._selected)
            cb.stateChanged.connect(lambda s, k=hkey, c=cb: self._toggle_holiday(k, c.isChecked()))
            row_l.addWidget(cb)

            days_list = HOLIDAY_DAYS.get(hkey, [])
            if days_list:
                expand_btn = QPushButton("◀")
                expand_btn.setFixedSize(24, 24)
                expand_btn.setStyleSheet(
                    "QPushButton{background:transparent;border:1px solid #bbb;"
                    "border-radius:4px;font-size:11px;color:#444;}"
                    "QPushButton:hover{background:#e8f0fe;border-color:#2563eb;color:#2563eb;}"
                )
                row_l.addWidget(expand_btn)

                # מיכל הימים — מוסתר בהתחלה
                days_widget = QWidget()
                days_widget.setVisible(False)
                dwl = QVBoxLayout(days_widget)
                dwl.setContentsMargins(28, 2, 4, 6)
                dwl.setSpacing(3)

                self._day_checks[hkey] = {}
                for day_lbl in days_list:
                    dcb = QCheckBox(day_lbl)
                    dcb.setChecked(True)
                    self._day_checks[hkey][day_lbl] = dcb
                    dwl.addWidget(dcb)

                # closure בטוח — ללא use של לולאה משתנה
                def _make_toggle(btn, widget):
                    def _do_toggle():
                        is_open = widget.isVisible()
                        widget.setVisible(not is_open)
                        btn.setText("▼" if not is_open else "◀")
                    return _do_toggle

                expand_btn.clicked.connect(_make_toggle(expand_btn, days_widget))
                hwl.addWidget(row_widget)
                hwl.addWidget(days_widget)
            else:
                hwl.addWidget(row_widget)

            row_l.addStretch()
            cl.addWidget(holiday_widget)

        cl.addStretch()
        scroll.setWidget(content)
        vl.addWidget(scroll)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        vl.addWidget(btns)

    def _toggle_holiday(self, key: str, checked: bool):
        if checked:
            self._selected.add(key)
        else:
            self._selected.discard(key)

    def get_selected(self) -> list:
        return list(self._selected)


# ══════════════════════════════════════════════════════════════════
# כיבוי תאורת מסך
# ══════════════════════════════════════════════════════════════════
class ScreenOffPage(BasePage):
    """לשונית לניהול כיבוי תאורת המסך לפי תרחישים"""

    def __init__(self, cm, dark, _=None):
        super().__init__(cm, dark); self._build()

    def _build(self):
        l = QVBoxLayout(self); l.setContentsMargins(28,28,28,28); l.setSpacing(14)
        l.addWidget(self._title("כיבוי תאורת מסך",
                                "כיבוי בלבד — המחשב ממשיך לפעול. המסך ידלק כשיגיע הזמן המוגדר."))

        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget(); cl = QVBoxLayout(content); cl.setContentsMargins(0,0,0,8); cl.setSpacing(14)

        # ── תרחישים ──
        scenarios_card = self._card(); sl = QVBoxLayout(scenarios_card)
        sl.setContentsMargins(20,16,20,16); sl.setSpacing(10)
        hdr_row = QHBoxLayout()
        hdr_row.addWidget(QLabel("📋  תרחישי כיבוי מסך:"))
        hdr_row.addStretch()
        add_btn = QPushButton("+ הוסף זמן כיבוי"); add_btn.setObjectName("PrimaryBtn")
        add_btn.clicked.connect(self._add_scenario); hdr_row.addWidget(add_btn)
        sl.addLayout(hdr_row)
        self._scenario_list = QListWidget(); self._scenario_list.setMaximumHeight(160)
        self._fill_scenarios()
        sl.addWidget(self._scenario_list)
        del_btn = QPushButton("🗑 מחק נבחר"); del_btn.setObjectName("DangerBtn")
        del_btn.clicked.connect(self._del_scenario); sl.addWidget(del_btn)
        cl.addWidget(scenarios_card)

        # ── כיבוי בחסימה ──
        block_card = self._card(); bl = QVBoxLayout(block_card)
        bl.setContentsMargins(20,16,20,16); bl.setSpacing(8)
        bl.addWidget(QLabel("🔗  חיבור לחסימות"))
        cfg = self.cm.config.get("screen_off", {})
        self._off_when_blocked = QCheckBox(
            "כבה מסך בכל זמן שהמחשב חסום (לפי הגדרות לשונית 'חסימות')"
        )
        self._off_when_blocked.setChecked(cfg.get("off_when_blocked", False))
        bl.addWidget(self._off_when_blocked)
        cl.addWidget(block_card)

        # ── אפשרות כיבוי מחדש אוטומטי ──
        reoff_card = self._card(); rl = QVBoxLayout(reoff_card)
        rl.setContentsMargins(20,16,20,16); rl.setSpacing(10)
        rl.addWidget(QLabel("🔄  כיבוי מחדש אוטומטי (כשהמסך נדלק ע\"י משתמש)"))

        self._reoff_enabled = QCheckBox(
            "כבה מסך מחדש לאחר חידוש פעילות, כשהזמן עדיין מוגדר לכיבוי"
        )
        self._reoff_enabled.setChecked(cfg.get("reoff_enabled", False))
        rl.addWidget(self._reoff_enabled)

        reoff_form = QFormLayout(); reoff_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self._reoff_delay = QSpinBox()
        self._reoff_delay.setRange(5, 300); self._reoff_delay.setSuffix(" שניות")
        self._reoff_delay.setValue(cfg.get("reoff_delay_secs", 30))
        reoff_form.addRow("כבה מחדש אחרי:", self._reoff_delay)
        rl.addLayout(reoff_form)

        reoff_note = QLabel(
            "💡  כאשר המסך ידלק, תוצג הודעה 'מסך המחשב מוגדר להיות כבוי — יכבה בעוד X שניות' "
            "עם טיימר לאחור. הטיימר מתאפס בכל פעילות."
        )
        reoff_note.setObjectName("CardSub"); reoff_note.setWordWrap(True)
        rl.addWidget(reoff_note)
        cl.addWidget(reoff_card)

        cl.addStretch()
        scroll.setWidget(content); l.addWidget(scroll)

        save_btn = QPushButton("💾  שמור הגדרות כיבוי מסך"); save_btn.setObjectName("PrimaryBtn")
        save_btn.clicked.connect(self._save); l.addWidget(save_btn)

    def _fill_scenarios(self):
        self._scenario_list.clear()
        for s in self.cm.config.get("screen_off", {}).get("scenarios", []):
            tf   = s.get("time_from", "")
            tt   = s.get("time_to",   "")
            stype = s.get("type", "weekday")
            name = s.get("name", "")
            if stype == "weekday":
                days_heb = ["א׳","ב׳","ג׳","ד׳","ה׳","ו׳","שב׳"]
                day_names = ",".join(days_heb[d] for d in s.get("days",[]) if d < 7)
                desc = f"🌑 {name} | ימים: {day_names} | {tf}–{tt}"
            else:
                desc = f"📆 {name} | {s.get('date_from','')}–{s.get('date_to','')} | {tf}–{tt}"
            item = QListWidgetItem(desc)
            item.setData(Qt.ItemDataRole.UserRole, s)
            self._scenario_list.addItem(item)

    def _add_scenario(self):
        dlg = ScreenOffDialog(self.dark, self)
        if dlg.exec():
            cfg = self.cm.config.setdefault("screen_off", {})
            cfg.setdefault("scenarios", []).append(dlg.get_data())
            self.cm.save(); self._fill_scenarios()

    def _del_scenario(self):
        item = self._scenario_list.currentItem()
        if not item: return
        s = item.data(Qt.ItemDataRole.UserRole)
        scenarios = self.cm.config.get("screen_off", {}).get("scenarios", [])
        self.cm.config["screen_off"]["scenarios"] = [x for x in scenarios if x != s]
        self.cm.save(); self._fill_scenarios()

    def _save(self):
        cfg = self.cm.config.setdefault("screen_off", {})
        cfg["off_when_blocked"]  = self._off_when_blocked.isChecked()
        cfg["reoff_enabled"]     = self._reoff_enabled.isChecked()
        cfg["reoff_delay_secs"]  = self._reoff_delay.value()
        self.cm.save()
        QMessageBox.information(self, "שמירה", "הגדרות כיבוי מסך נשמרו ✓")

    def refresh(self):
        self._fill_scenarios()


class ScreenOffDialog(QDialog):
    """דיאלוג הוספת תרחיש כיבוי מסך — זהה ל-BlockDialog"""
    def __init__(self, dark, parent):
        super().__init__(parent)
        self.setWindowTitle("הוסף זמן כיבוי מסך")
        self.setMinimumWidth(440)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setStyleSheet(get_panel_style(dark))
        self._build()

    def _build(self):
        l = QVBoxLayout(self); l.setContentsMargins(22,20,22,20); l.setSpacing(12)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("שם:"))
        self._name = QLineEdit(); self._name.setPlaceholderText("לדוגמה: לילה, שישי ערב...")
        name_row.addWidget(self._name); l.addLayout(name_row)

        type_row = QHBoxLayout()
        type_row.addWidget(QLabel("סוג:"))
        self._type = QComboBox(); self._type.addItems(["ימים בשבוע", "טווח תאריכים"])
        self._type.currentIndexChanged.connect(self._update_form)
        type_row.addWidget(self._type); l.addLayout(type_row)

        hours_frame = QFrame(); hours_frame.setObjectName("Card")
        hfl = QFormLayout(hours_frame); hfl.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        hfl.setContentsMargins(14,10,14,10); hfl.setSpacing(8)
        hfl.addRow(QLabel("⏰  שעות כיבוי:"))
        self._from = QTimeEdit(QTime(23,0)); self._from.setDisplayFormat("HH:mm")
        self._to   = QTimeEdit(QTime(7,0));  self._to.setDisplayFormat("HH:mm")
        hfl.addRow("כבה משעה:", self._from)
        hfl.addRow("הדלק עד שעה:", self._to)
        l.addWidget(hours_frame)

        self._days_frame = QFrame(); self._days_frame.setObjectName("Card")
        dfl = QVBoxLayout(self._days_frame)
        dfl.setContentsMargins(14,10,14,10); dfl.setSpacing(6)
        dfl.addWidget(QLabel("📅  ימים:"))
        days_row = QHBoxLayout(); days_row.setSpacing(4)
        days_heb = ["א׳","ב׳","ג׳","ד׳","ה׳","ו׳","שב׳"]
        self._day_cbs = []
        for d in days_heb:
            cb = QCheckBox(d); cb.setChecked(True)
            self._day_cbs.append(cb); days_row.addWidget(cb)
        days_row.addStretch()
        all_btn = QPushButton("הכל"); all_btn.setObjectName("SecondaryBtn"); all_btn.setFixedHeight(26)
        all_btn.clicked.connect(lambda: [cb.setChecked(True) for cb in self._day_cbs])
        days_row.addWidget(all_btn); dfl.addLayout(days_row)
        l.addWidget(self._days_frame)

        self._dates_frame = QFrame(); self._dates_frame.setObjectName("Card")
        dtfl = QFormLayout(self._dates_frame)
        dtfl.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        dtfl.setContentsMargins(14,10,14,10); dtfl.setSpacing(8)
        dtfl.addRow(QLabel("📆  טווח תאריכים:"))
        self._date_from = QDateEdit(QDate.currentDate()); self._date_from.setCalendarPopup(True)
        self._date_from.setDisplayFormat("dd/MM/yyyy")
        self._date_to = QDateEdit(QDate.currentDate().addDays(1)); self._date_to.setCalendarPopup(True)
        self._date_to.setDisplayFormat("dd/MM/yyyy")
        dtfl.addRow("מתאריך:", self._date_from); dtfl.addRow("עד תאריך:", self._date_to)
        l.addWidget(self._dates_frame)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        l.addWidget(btns)
        self._update_form(0)

    def _update_form(self, idx):
        self._days_frame.setVisible(idx == 0)
        self._dates_frame.setVisible(idx == 1)

    def get_data(self) -> dict:
        idx = self._type.currentIndex()
        base = {
            "name":      self._name.text() or "כיבוי מסך",
            "time_from": self._from.time().toString("HH:mm"),
            "time_to":   self._to.time().toString("HH:mm"),
        }
        if idx == 0:
            base["type"] = "weekday"
            base["days"] = [i for i, cb in enumerate(self._day_cbs) if cb.isChecked()]
        else:
            base["type"]      = "daterange"
            base["date_from"] = self._date_from.date().toString("yyyy-MM-dd")
            base["date_to"]   = self._date_to.date().toString("yyyy-MM-dd")
        return base


# ══════════════════════════════════════════════════════════════════
# מצב קיוסק
# ══════════════════════════════════════════════════════════════════
class KioskPage(BasePage):
    def __init__(self, cm, dark, _=None):
        super().__init__(cm, dark); self._build()

    def _build(self):
        l = QVBoxLayout(self); l.setContentsMargins(28,28,28,28); l.setSpacing(14)
        l.addWidget(self._title("מצב קיוסק","בכניסה למחשב יוצג מסך מוגבל עם תוכנות נבחרות בלבד"))
        kiosk = self.cm.config.get("kiosk",{})

        card = self._card(); cl = QVBoxLayout(card); cl.setContentsMargins(20,16,20,16); cl.setSpacing(10)
        self._enabled = QCheckBox("הפעל מצב קיוסק (לא חל על מנהל מערכת!)")
        self._enabled.setChecked(kiosk.get("enabled",False)); cl.addWidget(self._enabled)
        cl.addWidget(QLabel("תוכנות מאושרות (שם קובץ .exe):"))
        self._apps_list = QListWidget(); self._apps_list.setMaximumHeight(200)
        for app in kiosk.get("allowed_apps",[]): self._apps_list.addItem(app)
        cl.addWidget(self._apps_list)

        add_row = QHBoxLayout()
        self._app_input = QLineEdit(); self._app_input.setPlaceholderText("chrome.exe")
        add_row.addWidget(self._app_input)
        browse = QPushButton("עיון"); browse.setObjectName("SecondaryBtn")
        browse.clicked.connect(self._browse); add_row.addWidget(browse)
        add = QPushButton("+ הוסף"); add.setObjectName("PrimaryBtn")
        add.clicked.connect(self._add); add_row.addWidget(add)
        del_ = QPushButton("מחק"); del_.setObjectName("DangerBtn")
        del_.clicked.connect(lambda: self._apps_list.takeItem(self._apps_list.currentRow()))
        add_row.addWidget(del_); cl.addLayout(add_row)
        l.addWidget(card)

        save = QPushButton("💾  שמור"); save.setObjectName("PrimaryBtn")
        save.clicked.connect(self._save); l.addWidget(save)
        l.addStretch()

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(self,"בחר תוכנה","C:\\Program Files","Programs (*.exe)")
        if path: self._app_input.setText(os.path.basename(path))

    def _add(self):
        name = self._app_input.text().strip()
        if name: self._apps_list.addItem(name); self._app_input.clear()

    def _save(self):
        try:
            self.cm.config["kiosk"] = {
                "enabled": self._enabled.isChecked(),
                "allowed_apps": [self._apps_list.item(i).text() for i in range(self._apps_list.count())]
            }
            self.cm.save(); QMessageBox.information(self,"שמירה","הגדרות קיוסק נשמרו ✓")


        except Exception as _save_err:
            import traceback, logging
            logging.getLogger(__name__).error(f'שמירה נכשלה: {traceback.format_exc()}')
            QMessageBox.critical(self, 'שגיאה', f'פעולה נכשלה: {_save_err}')
# ══════════════════════════════════════════════════════════════════
# הודעות
# ══════════════════════════════════════════════════════════════════
class MessagesPage(BasePage):
    def __init__(self, cm, dark, _=None):
        super().__init__(cm, dark); self._current = None; self._build()

    def _build(self):
        root = QHBoxLayout(self); root.setContentsMargins(0,0,0,0); root.setSpacing(0)

        # רשימת משתמשים
        side = QFrame(); side.setFixedWidth(210)
        side.setStyleSheet(f"background:{'#0d1117' if self.dark else '#f5f7fb'};"
                           f"border-left:1px solid {'#30363d' if self.dark else '#e2e8f4'};")
        sl = QVBoxLayout(side); sl.setContentsMargins(10,14,10,14); sl.setSpacing(8)
        sl.addWidget(QLabel("💬  הודעות"))
        self._user_list = QListWidget()
        self._user_list.currentItemChanged.connect(self._load_convo)
        self._fill_users(); sl.addWidget(self._user_list)
        root.addWidget(side)

        # שיחה
        convo = QWidget(); cl = QVBoxLayout(convo)
        cl.setContentsMargins(18,18,18,18); cl.setSpacing(10)
        self._convo_title = QLabel("בחר משתמש לצפייה"); self._convo_title.setObjectName("PanelTitle")
        cl.addWidget(self._convo_title)

        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._msg_container = QWidget(); self._msg_layout = QVBoxLayout(self._msg_container)
        self._msg_layout.setAlignment(Qt.AlignmentFlag.AlignTop); self._msg_layout.setSpacing(8)
        scroll.setWidget(self._msg_container); cl.addWidget(scroll)

        row = QHBoxLayout(); row.setSpacing(8)
        self._reply_input = QLineEdit(); self._reply_input.setPlaceholderText("כתוב תשובה...")
        self._reply_input.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._reply_input.returnPressed.connect(self._send_reply); row.addWidget(self._reply_input)
        send = QPushButton("שלח ▶"); send.setObjectName("PrimaryBtn")
        send.clicked.connect(self._send_reply); row.addWidget(send)

        block_msg = QPushButton("🚫 חסום הודעות"); block_msg.setObjectName("DangerBtn")
        block_msg.clicked.connect(self._block_messages); row.addWidget(block_msg)
        del_convo = QPushButton("🗑 מחק שיחה"); del_convo.setObjectName("SecondaryBtn")
        del_convo.clicked.connect(self._delete_convo); row.addWidget(del_convo)
        cl.addLayout(row); root.addWidget(convo,1)

    def _fill_users(self):
        self._user_list.clear()
        for uname, ud in self.cm.get_all_users().items():
            msgs = ud.get("messages",[])
            unread = sum(1 for m in msgs if m.get("from")=="user" and not m.get("read"))
            dn = ud.get("display_name") or uname
            item = QListWidgetItem(f"{'🔴 ' if unread else ''}{dn}")
            item.setData(Qt.ItemDataRole.UserRole, uname)
            self._user_list.addItem(item)

    def _load_convo(self, item):
        if not item: return
        uname = item.data(Qt.ItemDataRole.UserRole)
        self._current = uname
        user = self.cm.get_user(uname) or {}
        self._convo_title.setText(f"שיחה עם: {user.get('display_name') or uname}")
        for i in reversed(range(self._msg_layout.count())):
            w = self._msg_layout.itemAt(i).widget()
            if w: w.deleteLater()
        for msg in user.get("messages",[]):
            self._add_bubble(msg)
            if msg.get("from")=="user": msg["read"]=True
        self.cm.save(); self._fill_users()

    def _add_bubble(self, msg):
        is_user = msg.get("from")=="user"
        bubble = QFrame()
        bubble.setStyleSheet(f"QFrame{{background:{'rgba(56,139,253,0.12)' if is_user else 'rgba(63,185,80,0.12)'};"
                             f"border:1px solid {'rgba(56,139,253,0.25)' if is_user else 'rgba(63,185,80,0.25)'};"
                             "border-radius:10px;}}")
        bl = QVBoxLayout(bubble); bl.setContentsMargins(12,8,12,8); bl.setSpacing(2)
        sender = QLabel("משתמש" if is_user else "מנהל")
        sender.setStyleSheet(f"color:{'#388bfd' if is_user else '#3fb950'};font-weight:600;font-size:11px;")
        bl.addWidget(sender)
        txt = QLabel(msg.get("text","")); txt.setWordWrap(True)
        txt.setLayoutDirection(Qt.LayoutDirection.RightToLeft); bl.addWidget(txt)
        ts = msg.get("time","")
        try: ts = datetime.fromisoformat(ts).strftime("%d/%m %H:%M")
        except: pass
        tl = QLabel(ts); tl.setStyleSheet("color:#8b949e;font-size:10px;"); bl.addWidget(tl)
        row = QHBoxLayout()
        if is_user: row.addWidget(bubble); row.addStretch()
        else:       row.addStretch(); row.addWidget(bubble)
        ctr = QWidget(); ctr.setLayout(row); self._msg_layout.addWidget(ctr)

    def _send_reply(self):
        text = self._reply_input.text().strip()
        if not text or not self._current: return
        self.cm.add_reply_from_admin(self._current, text)
        self._reply_input.clear()
        self._add_bubble({"from":"admin","text":text,"time":datetime.now().isoformat()})

    def _block_messages(self):
        if not self._current: return
        self.cm.update_user(self._current, messages_blocked=True)
        QMessageBox.information(self,"חסימה",f"המשתמש '{self._current}' חסום משליחת הודעות")

    def _delete_convo(self):
        if not self._current: return
        if QMessageBox.question(self,"מחיקה","למחוק את כל השיחה?",
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            self.cm.update_user(self._current, messages=[])
            self._load_convo(self._user_list.currentItem())

    def refresh(self): self._fill_users()


class PrinterRateDialog(QDialog):
    """דיאלוג הגדרת תעריפי הדפסה לפי סוג"""
    def __init__(self, printer_name: str, rates: dict, dark: bool, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"תעריפי הדפסה — {printer_name}")
        self.setMinimumWidth(380); self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setStyleSheet(get_panel_style(dark))
        self._build(rates)

    def _build(self, rates: dict):
        l = QFormLayout(self); l.setContentsMargins(22,18,22,18); l.setSpacing(10)
        l.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self._spins = {}
        fields = [
            ("a4_bw",    "A4 שחור-לבן (₪):"),
            ("a4_color", "A4 צבע (₪):"),
            ("a3_bw",    "A3 שחור-לבן (₪):"),
            ("a3_color", "A3 צבע (₪):"),
        ]
        for key, label in fields:
            sp = QDoubleSpinBox(); sp.setRange(0, 999); sp.setSuffix(" ₪")
            sp.setValue(rates.get(key, 0)); sp.setDecimals(2)
            self._spins[key] = sp; l.addRow(label, sp)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        l.addRow(btns)

    def get_rates(self) -> dict:
        return {k: sp.value() for k, sp in self._spins.items()}


# ══════════════════════════════════════════════════════════════════
# תשלום
# ══════════════════════════════════════════════════════════════════
class PaymentPage(BasePage):
    def __init__(self, cm, dark, _=None):
        super().__init__(cm, dark); self._build()

    def _build(self):
        l = QVBoxLayout(self); l.setContentsMargins(28,28,28,28); l.setSpacing(14)
        l.addWidget(self._title("הגדרות תשלום", "סליקת אשראי, שוברים וקבלות"))
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        cw = QWidget(); cl = QVBoxLayout(cw); cl.setContentsMargins(0,0,0,0); cl.setSpacing(14)

        cfg = self.cm.config.get("payment", {})

        # ── סליקת אשראי ──
        cc = self._card(); ccl = QVBoxLayout(cc)
        ccl.setContentsMargins(20,16,20,16); ccl.setSpacing(10)
        t1 = QLabel("💳  סליקת אשראי"); t1.setObjectName("CardTitle"); ccl.addWidget(t1)
        self._cc_enabled = QCheckBox("הפעל סליקת אשראי")
        self._cc_enabled.setChecked(cfg.get("cc_enabled", False)); ccl.addWidget(self._cc_enabled)
        f1 = QFormLayout(); f1.setLabelAlignment(Qt.AlignmentFlag.AlignRight); f1.setSpacing(8)
        self._cc_provider = QComboBox()
        self._cc_provider.addItems(["Cardcom", "Tranzila", "PayPlus", "Meshulam", "אחר"])
        prov_map = {"cardcom":0,"tranzila":1,"payplus":2,"meshulam":3,"other":4}
        self._cc_provider.setCurrentIndex(prov_map.get(cfg.get("cc_provider","cardcom"),0))
        f1.addRow("ספק סליקה:", self._cc_provider)
        self._cc_terminal = QLineEdit(cfg.get("cc_terminal",""))
        self._cc_terminal.setPlaceholderText("מספר טרמינל / מזהה"); f1.addRow("טרמינל:", self._cc_terminal)
        self._cc_api_key = QLineEdit(cfg.get("cc_api_key",""))
        self._cc_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._cc_api_key.setPlaceholderText("API Key"); f1.addRow("API Key:", self._cc_api_key)
        ccl.addLayout(f1)
        hint = QLabel("💡 ראה תיעוד ספק הסליקה לפרטי חיבור")
        hint.setObjectName("PanelSub"); hint.setWordWrap(True); ccl.addWidget(hint)
        cl.addWidget(cc)

        # ── שוברים ──
        vc = self._card(); vl = QVBoxLayout(vc)
        vl.setContentsMargins(20,16,20,16); vl.setSpacing(10)
        t2 = QLabel("🎟️  שוברים"); t2.setObjectName("CardTitle"); vl.addWidget(t2)
        self._vouchers_enabled = QCheckBox("אפשר רכישת חבילות בשובר")
        self._vouchers_enabled.setChecked(cfg.get("vouchers_enabled", False))
        vl.addWidget(self._vouchers_enabled)

        vl.addWidget(QLabel("הנפקת שובר:"))
        self._pkg_select = QComboBox()
        for p in self.cm.get_packages():
            self._pkg_select.addItem(p.get("name",""), p.get("id",""))
        vl.addWidget(self._pkg_select)
        gr = QHBoxLayout()
        gb = QPushButton("🎟 הנפק שובר"); gb.setObjectName("PrimaryBtn")
        gb.clicked.connect(self._generate_voucher); gr.addWidget(gb)
        eb = QPushButton("📊 ייצא לCSV"); eb.setObjectName("SecondaryBtn")
        eb.clicked.connect(self._export_vouchers); gr.addWidget(eb)
        gr.addStretch(); vl.addLayout(gr)
        self._voucher_list = QListWidget(); self._voucher_list.setMaximumHeight(130)
        self._load_vouchers(); vl.addWidget(self._voucher_list)
        cl.addWidget(vc)

        # ── קבלה במייל ──
        rc = self._card(); rl = QVBoxLayout(rc)
        rl.setContentsMargins(20,16,20,16); rl.setSpacing(10)
        t3 = QLabel("📧  קבלה במייל"); t3.setObjectName("CardTitle"); rl.addWidget(t3)
        self._email_receipt = QCheckBox("שלח קבלה במייל לאחר רכישה")
        self._email_receipt.setChecked(cfg.get("email_receipt", False)); rl.addWidget(self._email_receipt)
        f2 = QFormLayout(); f2.setLabelAlignment(Qt.AlignmentFlag.AlignRight); f2.setSpacing(8)
        self._smtp_server  = QLineEdit(cfg.get("smtp_server","smtp.gmail.com")); f2.addRow("SMTP Server:", self._smtp_server)
        self._smtp_port    = QSpinBox(); self._smtp_port.setRange(1,65535); self._smtp_port.setValue(cfg.get("smtp_port",587)); f2.addRow("פורט:", self._smtp_port)
        self._smtp_user    = QLineEdit(cfg.get("smtp_user","")); f2.addRow("משתמש:", self._smtp_user)
        self._smtp_pass    = QLineEdit(cfg.get("smtp_pass","")); self._smtp_pass.setEchoMode(QLineEdit.EchoMode.Password); f2.addRow("סיסמה:", self._smtp_pass)
        self._email_subj   = QLineEdit(cfg.get("email_subject","קבלה — שומר הפתח")); f2.addRow("נושא:", self._email_subj)
        rl.addLayout(f2)
        cl.addWidget(rc)

        cl.addStretch(); scroll.setWidget(cw); l.addWidget(scroll)
        save = QPushButton("💾  שמור"); save.setObjectName("PrimaryBtn")
        save.clicked.connect(self._save); l.addWidget(save)

    def _load_vouchers(self):
        self._voucher_list.clear()
        for v in reversed(self.cm.config.get("vouchers",[])[-30:]):
            used = "✓" if v.get("used") else "⬜"
            self._voucher_list.addItem(
                f"{v.get('code','')}  |  {v.get('package_name','')}  |  {used}  |  {v.get('created','')}")

    def _generate_voucher(self):
        import secrets
        from datetime import datetime as _dt
        pkg_id   = self._pkg_select.currentData()
        pkg_name = self._pkg_select.currentText()
        if not pkg_id:
            QMessageBox.warning(self,"שגיאה","בחר חבילה תחילה"); return

        # כמה שוברים?
        count, ok = QInputDialog.getInt(self,"כמות","כמה שוברים להנפיק?",100,1,500,1)
        if not ok: return

        created = _dt.now().strftime("%d/%m/%Y %H:%M")
        existing = self.cm.config.setdefault("vouchers",[])
        # בדוק אם כל הקיימים לחבילה זו מומשו — אם כן, אפס
        pkg_vouchers = [v for v in existing if v.get("package_id")==pkg_id]
        if pkg_vouchers and all(v.get("used") for v in pkg_vouchers):
            # מחק ישנים וצור מחדש
            self.cm.config["vouchers"] = [v for v in existing if v.get("package_id")!=pkg_id]
            existing = self.cm.config["vouchers"]

        # הנפק בסדר קבוע (מבוסס sequence)
        existing_codes = {v["code"] for v in existing if v.get("package_id")==pkg_id}
        new_vouchers = []
        while len(new_vouchers) < count:
            code = secrets.token_hex(4).upper()
            if code not in existing_codes:
                existing_codes.add(code)
                new_vouchers.append({
                    "code":code,"package_id":pkg_id,"package_name":pkg_name,
                    "used":False,"created":created,"sequence":len(existing)+len(new_vouchers)+1
                })
        existing.extend(new_vouchers)
        self.cm.save(); self._load_vouchers()
        QMessageBox.information(self,"הצלחה",
            f"הונפקו {count} שוברים לחבילה: {pkg_name}")

    def _export_vouchers(self):
        import csv
        pkg_id = self._pkg_select.currentData()
        # יצא רק שוברים של החבילה הנבחרת, ממוינים לפי sequence
        vouchers = sorted(
            [v for v in self.cm.config.get("vouchers",[]) if not pkg_id or v.get("package_id")==pkg_id],
            key=lambda v: v.get("sequence",0)
        )
        if not vouchers:
            QMessageBox.information(self,"ייצוא","אין שוברים לייצא"); return
        path, _ = QFileDialog.getSaveFileName(self,"שמור","vouchers.csv","CSV (*.csv)")
        if not path: return
        try:
            with open(path,"w",newline="",encoding="utf-8-sig") as fout:
                w = csv.writer(fout)
                w.writerow(["#","קוד שובר","חבילה","מומש","תאריך הנפקה"])
                for i,v in enumerate(vouchers,1):
                    w.writerow([i, v.get("code",""), v.get("package_name",""),
                                "כן" if v.get("used") else "לא", v.get("created","")])
            QMessageBox.information(self,"ייצוא",f"יוצאו {len(vouchers)} שוברים → {path}")
        except Exception as e:
            QMessageBox.critical(self,"שגיאה",str(e))

    def _save(self):
        try:
            prov = ["cardcom","tranzila","payplus","meshulam","other"]
            self.cm.config["payment"] = {
                "cc_enabled":       self._cc_enabled.isChecked(),
                "cc_provider":      prov[self._cc_provider.currentIndex()],
                "cc_terminal":      self._cc_terminal.text().strip(),
                "cc_api_key":       self._cc_api_key.text().strip(),
                "vouchers_enabled": self._vouchers_enabled.isChecked(),
                "email_receipt":    self._email_receipt.isChecked(),
                "smtp_server":      self._smtp_server.text().strip(),
                "smtp_port":        self._smtp_port.value(),
                "smtp_user":        self._smtp_user.text().strip(),
                "smtp_pass":        self._smtp_pass.text().strip(),
                "email_subject":    self._email_subj.text().strip(),
            }
            self.cm.save()
            QMessageBox.information(self,"שמירה","הגדרות תשלום נשמרו ✓")

        except Exception as _save_err:
            import traceback, logging
            logging.getLogger(__name__).error(f'שמירה נכשלה: {traceback.format_exc()}')
            QMessageBox.critical(self, 'שגיאה', f'פעולה נכשלה: {_save_err}')
# ══════════════════════════════════════════════════════════════════
# הגדרות
# ══════════════════════════════════════════════════════════════════
class SettingsPage(BasePage):
    def __init__(self, cm, dark, toggle_dark=None):
        super().__init__(cm, dark); self._toggle_dark = toggle_dark; self._build()

    def _build(self):
        l = QVBoxLayout(self); l.setContentsMargins(28,28,28,28); l.setSpacing(16)
        l.addWidget(self._title("הגדרות מערכת"))
        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget(); cl = QVBoxLayout(content); cl.setContentsMargins(0,0,0,0); cl.setSpacing(14)
        cfg = self.cm.get_general_cfg()

        # ── הפעלה עם Windows ──
        startup_card = self._card(); sl = QVBoxLayout(startup_card)
        sl.setContentsMargins(20,16,20,16); sl.setSpacing(10)
        sl.addWidget(QLabel("🚀  הפעלה אוטומטית"))
        self._startup = QCheckBox("הפעל שומר הפתח עם הפעלת Windows (דרך הרג'סטרי)")
        self._startup.setChecked(cfg.get("startup_enabled",True)); sl.addWidget(self._startup)
        startup_row = QHBoxLayout()
        apply_startup = QPushButton("החל כעת"); apply_startup.setObjectName("PrimaryBtn")
        apply_startup.clicked.connect(self._apply_startup); startup_row.addWidget(apply_startup)
        startup_row.addStretch(); sl.addLayout(startup_row)
        cl.addWidget(startup_card)

        # ── Ctrl+Alt+Del ──
        cad_card = self._card(); cadl = QVBoxLayout(cad_card)
        cadl.setContentsMargins(20,16,20,16); cadl.setSpacing(10)
        cadl.addWidget(QLabel("🛡️  חסימת Ctrl+Alt+Del"))
        self._block_cad = QCheckBox("חסום Ctrl+Alt+Del (ו-Task Manager, Lock Screen, וכו')")
        self._block_cad.setChecked(cfg.get("block_ctrl_alt_del",True)); cadl.addWidget(self._block_cad)
        cad_row = QHBoxLayout()
        apply_cad = QPushButton("החל כעת"); apply_cad.setObjectName("PrimaryBtn")
        apply_cad.clicked.connect(self._apply_cad); cad_row.addWidget(apply_cad)
        cad_row.addStretch(); cadl.addLayout(cad_row)
        cl.addWidget(cad_card)

        # ── מצב לילה ──
        night_card = self._card(); nl = QHBoxLayout(night_card); nl.setContentsMargins(20,16,20,16)
        nl.addWidget(QLabel("🌙  מצב לילה")); nl.addStretch()
        night_btn = QPushButton("החלף מצב"); night_btn.setObjectName("SecondaryBtn")
        if self._toggle_dark: night_btn.clicked.connect(self._toggle_dark)
        nl.addWidget(night_btn); cl.addWidget(night_card)

        # ── הגדרות כלליות ──
        gen_card = self._card(); gl = QFormLayout(gen_card)
        gl.setContentsMargins(20,16,20,16); gl.setSpacing(10)
        gl.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self._show_pkgs = QCheckBox("הצג לשונית 'קנה חבילות' במסך הכניסה")
        self._show_pkgs.setChecked(cfg.get("show_packages_tab",True)); gl.addRow("",self._show_pkgs)
        self._show_msgs = QCheckBox("אפשר הודעות בין משתמשים ומנהל")
        self._show_msgs.setChecked(cfg.get("show_messages",True)); gl.addRow("",self._show_msgs)
        self._reset_time = QTimeEdit(); self._reset_time.setDisplayFormat("HH:mm")
        rt = cfg.get("reset_time","00:00").split(":")
        self._reset_time.setTime(QTime(int(rt[0]),int(rt[1]))); gl.addRow("שעת איפוס יומי:",self._reset_time)
        self._warn_input = QLineEdit(",".join(str(i) for i in self.cm.get_warning_intervals()))
        self._warn_input.setPlaceholderText("דקות קודם להתראה, מופרדות בפסיקים (לדוגמה: 10,5,1)")
        gl.addRow("התראות לפני סיום (דקות):",self._warn_input)
        cl.addWidget(gen_card)

        # ── גיבוי ──
        backup_card = self._card(); bl = QVBoxLayout(backup_card)
        bl.setContentsMargins(20,16,20,16); bl.setSpacing(10)
        bl.addWidget(QLabel("📦  גיבוי ושחזור"))
        br = QHBoxLayout()
        exp = QPushButton("⬆ ייצא הכל"); exp.setObjectName("SecondaryBtn"); exp.clicked.connect(self._export_all); br.addWidget(exp)
        imp = QPushButton("⬇ ייבא הכל"); imp.setObjectName("SecondaryBtn"); imp.clicked.connect(self._import_all); br.addWidget(imp)
        br.addStretch(); bl.addLayout(br); cl.addWidget(backup_card)

        cl.addStretch(); scroll.setWidget(content); l.addWidget(scroll)
        save = QPushButton("💾  שמור הגדרות"); save.setObjectName("PrimaryBtn")
        save.clicked.connect(self._save); l.addWidget(save)

    def _apply_startup(self):
        from registry_manager import add_to_startup, remove_from_startup
        if self._startup.isChecked(): ok = add_to_startup()
        else: ok = remove_from_startup(); ok = True
        QMessageBox.information(self,"הפעלה אוטומטית","הוגדר בהצלחה ✓" if ok else "נדרשת הרצה כמנהל")

    def _apply_cad(self):
        from registry_manager import block_ctrl_alt_del, unblock_ctrl_alt_del
        if self._block_cad.isChecked(): ok = block_ctrl_alt_del()
        else: ok = unblock_ctrl_alt_del()
        QMessageBox.information(self,"Ctrl+Alt+Del","הוגדר בהצלחה ✓" if ok else "נדרשת הרצה כמנהל")

    def _export_reg(self):
        block = self._block_cad.isChecked()
        name  = "BlockACD.reg" if block else "UnblockACD.reg"
        path, _ = QFileDialog.getSaveFileName(self,"שמור קובץ רג'סטרי",name,"REG files (*.reg)")
        if path:
            from registry_manager import export_reg_file
            export_reg_file(block, path)
            QMessageBox.information(self,"ייצוא",f"הקובץ נשמר: {path}")

    def _export_all(self):
        path,_ = QFileDialog.getSaveFileName(self,"ייצא הגדרות","shomer_hapetach_backup.json","JSON (*.json)")
        if path:
            ok = self.cm.export_all(path)
            QMessageBox.information(self,"ייצוא","ייצוא הצליח ✓" if ok else "ייצוא נכשל ✗")

    def _import_all(self):
        path,_ = QFileDialog.getOpenFileName(self,"ייבא הגדרות","","JSON (*.json)")
        if path:
            if QMessageBox.question(self,"ייבוא","פעולה זו תחליף את כל ההגדרות. להמשיך?",
                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                ok = self.cm.import_all(path)
                QMessageBox.information(self,"ייבוא","ייבוא הצליח – אנא הפעל מחדש ✓" if ok else "ייבוא נכשל ✗")

    def _save(self):
        cfg = self.cm.config["general"]
        cfg["startup_enabled"]    = self._startup.isChecked()
        cfg["block_ctrl_alt_del"] = self._block_cad.isChecked()
        cfg["show_packages_tab"]  = self._show_pkgs.isChecked()
        cfg["show_messages"]      = self._show_msgs.isChecked()
        t = self._reset_time.time()
        cfg["reset_time"] = f"{t.hour():02d}:{t.minute():02d}"
        try:
            cfg["warning_intervals"] = [int(x.strip()) for x in self._warn_input.text().split(",") if x.strip()]
        except: pass
        self.cm.save()
        QMessageBox.information(self,"שמירה","הגדרות נשמרו ✓")


# ══════════════════════════════════════════════════════════════════
# אודות
# ══════════════════════════════════════════════════════════════════
class AboutPage(BasePage):
    """לשונית אודות התוכנה"""
    VERSION = "0.0.10"

    def __init__(self, cm, dark, _=None):
        super().__init__(cm, dark)
        self._build()

    def _build(self):
        l = QVBoxLayout(self)
        l.setContentsMargins(28, 28, 28, 28)
        l.setSpacing(20)
        l.addWidget(self._title("אודות שומר הפתח", f"גרסה {self.VERSION}"))

        # ── כרטיס ראשי ──
        main_card = self._card()
        ml = QVBoxLayout(main_card)
        ml.setContentsMargins(32, 28, 32, 28)
        ml.setSpacing(14)

        logo_lbl = QLabel("🔐")
        logo_lbl.setStyleSheet("font-size:52px;")
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ml.addWidget(logo_lbl)

        name_lbl = QLabel("שומר הפתח")
        name_lbl.setStyleSheet(
            "font-size:26px;font-weight:700;"
            "font-family:'Segoe UI','Arial Hebrew',sans-serif;"
        )
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ml.addWidget(name_lbl)

        ver_lbl = QLabel(f"גרסה {self.VERSION}")
        ver_lbl.setStyleSheet("font-size:16px;font-weight:600;color:#2563eb;")
        ver_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ml.addWidget(ver_lbl)

        ml.addSpacing(8)

        desc_lbl = QLabel(
            "כלי בקרה וניהול זמן שימוש במחשב\n"
            "לבתי כנסת, ספריות, מרכזי קהילה וארגונים"
        )
        desc_lbl.setObjectName("PanelSub")
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_lbl.setWordWrap(True)
        ml.addWidget(desc_lbl)
        l.addWidget(main_card)

        # ── כרטיס מאפיינים (ללא מידע טכני — הוסר לפינוי מקום) ──
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        feat_card = self._card()
        fl = QVBoxLayout(feat_card)
        fl.setContentsMargins(24, 18, 24, 18)
        fl.setSpacing(12)
        fl.addWidget(QLabel("⚡  מאפיינים עיקריים", objectName="CardTitle"))

        features = [
            ("🔒", "מסך נעילה עם תמונת רקע וקוד כניסה אישי"),
            ("⏱", "הגבלת זמן שימוש יומי ובקרת חבילות"),
            ("🖨", "ניטור מדפסות וחיוב אוטומטי לפי תעריפים"),
            ("🎟", "הנפקת שוברים לרכישת חבילות"),
            ("⌨", "חסימת מקשי מערכת (Win, Alt+Tab, Ctrl+Alt+Del)"),
            ("🏪", "מצב קיוסק עם תוכנות מאושרות בלבד"),
            ("💬", "מערכת הודעות בין משתמשים למנהל"),
            ("🌐", "ניהול כמה מחשבים מתיקייה שיתופית"),
            ("✡", "חסימה אוטומטית בשבת וחגים יהודיים"),
        ]

        for icon, text in features:
            row = QHBoxLayout()
            icon_l = QLabel(icon)
            icon_l.setStyleSheet("font-size:16px;")
            icon_l.setFixedWidth(30)
            txt_l = QLabel(text)
            txt_l.setObjectName("PanelSub")
            txt_l.setWordWrap(True)
            row.addWidget(icon_l)
            row.addWidget(txt_l, 1)
            fl.addLayout(row)

        scroll.setWidget(feat_card)
        l.addWidget(scroll, 1)
