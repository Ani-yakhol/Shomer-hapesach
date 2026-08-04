"""
register_dialog.py - הרשמה עצמאית למשתמש חדש
שומר הפתח v2.0
"""
from PyQt6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QFormLayout, QFrame, QMessageBox,
    QApplication
)
from PyQt6.QtCore import Qt, QTimer
from styles import get_lockscreen_style


class RegisterDialog(QDialog):
    """חלונית הרשמה עצמאית – מופיעה ממסך הנעילה"""

    def __init__(self, config_manager, dark=False, parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.WindowStaysOnTopHint)
        self.cm   = config_manager
        self.dark = dark
        self.setStyleSheet(get_lockscreen_style(dark))
        self.setMinimumSize(420, 520); self.resize(420,520)
        self._center()
        self._build()

    def _center(self):
        s = QApplication.primaryScreen().geometry()
        self.move((s.width()-400)//2, (s.height()-420)//2)

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0,0,0,0)

        card = QFrame(); card.setObjectName("LoginCard")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(32,26,32,26); cl.setSpacing(12)

        ttl = QLabel("📝  פתיחת חשבון חדש")
        ttl.setObjectName("LockTitle")
        ttl.setStyleSheet("font-size:19px;")
        ttl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cl.addWidget(ttl)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(14)   # רווח גדול יותר בין שורות

        ls = self.cm.get_lock_screen_cfg()
        phone_req = ls.get("register_phone_required", False)
        email_req = ls.get("register_email_required", False)

        for_all_inputs = "QLineEdit{min-height:40px;font-size:14px;padding:9px 14px;}"
        self.setStyleSheet(self.styleSheet() + for_all_inputs)

        self._uname = QLineEdit()
        self._uname.setObjectName("LoginInput")
        self._uname.setPlaceholderText("בחר שם משתמש")
        self._uname.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._uname.setAlignment(Qt.AlignmentFlag.AlignAbsolute | Qt.AlignmentFlag.AlignRight)
        form.addRow("שם משתמש *:", self._uname)

        # שם תצוגה הוסר — שם המשתמש ישמש גם כשם תצוגה

        self._pwd = QLineEdit()
        self._pwd.setObjectName("LoginInput")
        self._pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self._pwd.setPlaceholderText("בחר סיסמה")
        self._pwd.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._pwd.setAlignment(Qt.AlignmentFlag.AlignAbsolute | Qt.AlignmentFlag.AlignRight)
        form.addRow("סיסמה *:", self._pwd)

        self._pwd2 = QLineEdit()
        self._pwd2.setObjectName("LoginInput")
        self._pwd2.setEchoMode(QLineEdit.EchoMode.Password)
        self._pwd2.setPlaceholderText("אמת סיסמה")
        self._pwd2.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._pwd2.setAlignment(Qt.AlignmentFlag.AlignAbsolute | Qt.AlignmentFlag.AlignRight)
        form.addRow("אמת סיסמה *:", self._pwd2)

        phone_lbl = f"טלפון {'*' if phone_req else '(אופציונלי)'}:"
        self._phone = QLineEdit()
        self._phone.setObjectName("LoginInput")
        self._phone.setPlaceholderText("050-0000000")
        self._phone.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self._phone.setAlignment(Qt.AlignmentFlag.AlignAbsolute | Qt.AlignmentFlag.AlignRight)
        form.addRow(phone_lbl, self._phone)

        email_lbl = f"אימייל {'*' if email_req else '(אופציונלי)'}:"
        self._email = QLineEdit()
        self._email.setObjectName("LoginInput")
        self._email.setPlaceholderText("example@email.com")
        self._email.setAlignment(Qt.AlignmentFlag.AlignLeft)
        form.addRow(email_lbl, self._email)

        cl.addLayout(form)

        self._err = QLabel("")
        self._err.setObjectName("ErrorLabel")
        self._err.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._err.setWordWrap(True)
        self._err.hide()
        cl.addWidget(self._err)

        self._reg_btn = QPushButton("✓  צור חשבון")
        self._reg_btn.setObjectName("LoginBtn")
        self._reg_btn.clicked.connect(self._register)
        cl.addWidget(self._reg_btn)

        cancel = QPushButton("ביטול")
        cancel.setObjectName("NightBtn")
        cancel.clicked.connect(self.reject)
        cl.addWidget(cancel)

        root.addWidget(card)
        QTimer.singleShot(100, self._uname.setFocus)

    def _register(self):
        ls  = self.cm.get_lock_screen_cfg()
        uname   = self._uname.text().strip()
        pwd     = self._pwd.text()
        pwd2    = self._pwd2.text()
        phone   = self._phone.text().strip()
        email   = self._email.text().strip()

        # ולידציות
        if not uname:
            self._show_err("נא להזין שם משתמש"); return
        if len(pwd) < 3:
            self._show_err("הסיסמה חייבת להכיל לפחות 3 תווים"); return
        if pwd != pwd2:
            self._show_err("הסיסמאות אינן תואמות"); return
        if ls.get("register_phone_required") and not phone:
            self._show_err("שדה טלפון הוא חובה"); return
        if ls.get("register_email_required") and not email:
            self._show_err("שדה אימייל הוא חובה"); return

        ok = self.cm.create_user(
            uname, pwd,
            display_name=uname,   # שם תצוגה = שם משתמש
            phone=phone,
            email=email,
            is_admin=False,
        )
        if not ok:
            self._show_err("שם משתמש כבר קיים, בחר שם אחר"); return

        self.accept()

    def _show_err(self, msg):
        self._err.setText(msg); self._err.show()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape: self.reject()
        else: super().keyPressEvent(event)
