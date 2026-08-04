"""styles.py - עיצוב שומר הפתח v2"""

def _vars(dark):
    if dark:
        return dict(
            bg1="#0d1117", bg2="#161b22", bg3="#1a1f2e",
            text="#e6edf3", sub="#8b949e",
            card="rgba(22,27,34,0.93)", border="rgba(48,54,61,0.8)",
            inp_bg="rgba(13,17,23,0.9)", inp_border="#30363d", inp_focus="#388bfd",
            btn_bg="qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1f6feb,stop:1 #388bfd)",
            btn_h="qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #388bfd,stop:1 #58a6ff)",
            accent="#58a6ff", green="#3fb950", danger="#da3633", danger_h="#f85149",
            sep="#21262d", side="#161b22", panel_bg="#0d1117",
            card2="#1c2128", btn2="#21262d", btn2_h="#30363d",
        )
    return dict(
        bg1="#e8f0fe", bg2="#f0f4ff", bg3="#dce8ff",
        text="#0d1b2a", sub="#4a5568",
        card="rgba(255,255,255,0.93)", border="rgba(200,215,240,0.9)",
        inp_bg="rgba(248,250,255,0.95)", inp_border="#b8cce8", inp_focus="#3d7bd6",
        btn_bg="qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #2563eb,stop:1 #3d7bd6)",
        btn_h="qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #3d7bd6,stop:1 #4a90e2)",
        accent="#2563eb", green="#16a34a", danger="#ef4444", danger_h="#dc2626",
        sep="#e2e8f4", side="#ffffff", panel_bg="#f5f7fb",
        card2="#ffffff", btn2="#f0f4ff", btn2_h="#dce8ff",
    )


def get_lockscreen_style(dark=False):
    v = _vars(dark)
    return f"""
QWidget#LockScreen {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
        stop:0 {v['bg1']},stop:0.5 {v['bg2']},stop:1 {v['bg3']});
}}
QFrame#LoginCard {{
    background: {v['card']};
    border: 1.5px solid {v['border']};
    border-radius: 20px;
}}
QLabel#LockTitle {{
    color: {v['text']};
    font-family:'Segoe UI','Arial Hebrew',sans-serif;
    font-size:26px; font-weight:700;
}}
QLabel#LockClock {{
    color: {v['text']};
    font-family:'Segoe UI',sans-serif;
    font-size:52px; font-weight:200; letter-spacing:2px;
}}
QLabel#LockDate {{
    color:{v['sub']};
    font-family:'Segoe UI','Arial Hebrew',sans-serif;
    font-size:15px;
}}
QLabel#InputLabel {{
    color:{v['sub']};
    font-family:'Segoe UI','Arial Hebrew',sans-serif;
    font-size:12px; font-weight:500;
}}
QLineEdit#LoginInput {{
    background:{v['inp_bg']};
    border:1.5px solid {v['inp_border']};
    border-radius:10px;
    color:{v['text']};
    font-family:'Segoe UI','Arial Hebrew',sans-serif;
    font-size:15px; padding:10px 16px;
}}
QLineEdit#LoginInput:focus {{ border-color:{v['inp_focus']}; }}
QPushButton#LoginBtn {{
    background:{v['btn_bg']};
    color:white; border:none; border-radius:10px;
    font-family:'Segoe UI','Arial Hebrew',sans-serif;
    font-size:15px; font-weight:600; padding:12px 0;
}}
QPushButton#LoginBtn:hover {{ background:{v['btn_h']}; }}
QPushButton#SecondaryBtn {{
    background:transparent;
    border:1.5px solid {v['inp_border']};
    border-radius:10px; color:{v['sub']};
    font-family:'Segoe UI','Arial Hebrew',sans-serif;
    font-size:14px; padding:11px 0;
}}
QPushButton#SecondaryBtn:hover {{ color:{v['text']}; border-color:{v['inp_focus']}; }}
QLabel#ErrorLabel {{
    color:#ef4444;
    font-family:'Segoe UI','Arial Hebrew',sans-serif;
    font-size:12px; font-weight:500;
    background:rgba(239,68,68,0.10);
    border:1px solid rgba(239,68,68,0.25);
    border-radius:7px; padding:6px 12px;
}}
QPushButton#NightBtn {{
    background:transparent;
    border:1px solid {v['border']};
    border-radius:8px; color:{v['sub']};
    font-size:16px; padding:5px 10px;
}}
QPushButton#NightBtn:hover {{ background:rgba(128,128,128,0.1); color:{v['text']}; }}
QLabel#FooterLabel {{
    color:{v['sub']};
    font-family:'Segoe UI',sans-serif; font-size:11px;
}}
"""


def get_panel_style(dark=False):
    v = _vars(dark)
    acc_bg = "rgba(56,139,253,0.15)" if dark else "rgba(37,99,235,0.10)"
    sel_color = "#388bfd" if dark else "#2563eb"
    return f"""
QMainWindow,QDialog {{ background:{v['panel_bg']}; }}
QWidget {{ font-family:'Segoe UI','Arial Hebrew',sans-serif; color:{v['text']}; }}
QFrame#Sidebar {{ background:{v['side']}; border-left:1px solid {v['sep']}; }}
QPushButton#SideBtn {{
    background:transparent; border:none; border-radius:10px;
    color:{v['sub']}; font-size:14px; font-weight:500;
    padding:11px 16px; text-align:right;
}}
QPushButton#SideBtn:hover {{ background:{v['btn2_h']}; color:{v['text']}; }}
QPushButton#SideBtn[selected="true"] {{
    background:{acc_bg}; color:{sel_color}; font-weight:600;
}}
QLabel#PanelTitle {{ color:{v['text']}; font-size:22px; font-weight:700; }}
QLabel#PanelSub   {{ color:{v['sub']};  font-size:13px; }}
QFrame#Card {{
    background:{v['card2']}; border:1px solid {v['sep']};
    border-radius:14px; padding:4px;
}}
QLabel#CardTitle {{ color:{v['text']}; font-size:15px; font-weight:600; }}
QLabel#CardSub   {{ color:{v['sub']};  font-size:12px; }}
QLineEdit,QSpinBox,QTimeEdit,QDateEdit,QTextEdit {{
    background:{v['inp_bg']}; border:1.5px solid {v['sep']};
    border-radius:8px; color:{v['text']}; font-size:14px; padding:8px 12px;
}}
QLineEdit:focus,QSpinBox:focus,QTimeEdit:focus,QDateEdit:focus {{ border-color:{v['accent']}; }}
QComboBox {{
    background:{v['inp_bg']}; border:1.5px solid {v['sep']};
    border-radius:8px; color:{v['text']}; font-size:14px; padding:7px 12px;
}}
QComboBox:focus {{ border-color:{v['accent']}; }}
QComboBox::drop-down {{ border:none; width:24px; }}
QComboBox QAbstractItemView {{
    background:{v['card2']}; border:1px solid {v['sep']};
    color:{v['text']}; selection-background-color:{v['accent']}; selection-color:white;
}}
QPushButton#PrimaryBtn {{
    background:{v['accent']}; color:white; border:none;
    border-radius:9px; font-size:14px; font-weight:600; padding:9px 22px;
}}
QPushButton#PrimaryBtn:hover {{ opacity:0.88; }}
QPushButton#SecondaryBtn {{
    background:{v['btn2']}; color:{v['text']};
    border:1px solid {v['sep']}; border-radius:9px; font-size:14px; padding:9px 18px;
}}
QPushButton#SecondaryBtn:hover {{ background:{v['btn2_h']}; }}
QPushButton#DangerBtn {{
    background:{v['danger']}; color:white; border:none;
    border-radius:9px; font-size:14px; font-weight:600; padding:9px 18px;
}}
QPushButton#DangerBtn:hover {{ background:{v['danger_h']}; }}
QPushButton#GreenBtn {{
    background:{v['green']}; color:white; border:none;
    border-radius:9px; font-size:14px; font-weight:600; padding:9px 18px;
}}
QTableWidget {{
    background:{v['card2']}; border:1px solid {v['sep']};
    border-radius:10px; gridline-color:{v['sep']};
    color:{v['text']}; font-size:13px; outline:0;
}}
QTableWidget::item {{ padding:8px 12px; }}
QHeaderView::section {{
    background:{v['btn2']}; color:{v['sub']};
    font-size:12px; font-weight:600;
    padding:8px 12px; border:none; border-bottom:1px solid {v['sep']};
}}
QListWidget {{
    background:{v['card2']}; border:1px solid {v['sep']};
    border-radius:10px; color:{v['text']}; font-size:13px; outline:0;
}}
QListWidget::item {{ padding:9px 12px; border-bottom:1px solid {v['sep']}; }}
QListWidget::item:selected {{ background:{acc_bg}; color:{v['text']}; }}
QListWidget::item:hover {{ background:{v['btn2']}; }}
QScrollBar:vertical {{ background:transparent; width:6px; margin:0; }}
QScrollBar::handle:vertical {{ background:{v['sep']}; border-radius:3px; min-height:30px; }}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {{ height:0; }}
QCheckBox {{ color:{v['text']}; font-size:13px; spacing:8px; }}
QCheckBox::indicator {{
    width:18px; height:18px; border:1.5px solid {v['sep']};
    border-radius:5px; background:{v['inp_bg']};
}}
QCheckBox::indicator:checked {{ background:{v['accent']}; border-color:{v['accent']}; }}
QLabel {{ color:{v['text']}; font-size:13px; }}
QTabWidget::pane {{
    border:1px solid {v['sep']}; border-radius:10px; background:{v['card2']};
}}
QTabBar::tab {{ background:transparent; color:{v['sub']}; padding:8px 18px; font-size:13px; border:none; }}
QTabBar::tab:selected {{ color:{sel_color}; border-bottom:2px solid {sel_color}; font-weight:600; }}
QTabBar::tab:hover:!selected {{ color:{v['text']}; }}
QGroupBox {{
    font-size:13px; font-weight:600; color:{v['sub']};
    border:1px solid {v['sep']}; border-radius:10px; margin-top:16px; padding-top:8px;
}}
QGroupBox::title {{ subcontrol-origin:margin; left:12px; top:-8px; background:{v['card2']}; padding:0 6px; }}
QToolTip {{
    background:{v['card2']}; color:{v['text']};
    border:1px solid {v['sep']}; border-radius:6px; padding:5px 10px; font-size:12px;
}}
"""


def get_welcome_style(dark=False):
    v = _vars(dark)
    return f"""
QWidget#WelcomeScreen {{ background:{v['panel_bg']}; }}
QLabel#WelcomeName {{
    color:{v['text']}; font-size:30px; font-weight:700;
    font-family:'Segoe UI','Arial Hebrew',sans-serif;
}}
QLabel#WelcomeSub {{
    color:{v['sub']}; font-size:14px;
    font-family:'Segoe UI','Arial Hebrew',sans-serif;
}}
QFrame#WelcomeCard {{
    background:{v['card2']}; border:1px solid {v['sep']}; border-radius:14px;
}}
QTabWidget::pane {{ background:{v['card2']}; border:1px solid {v['sep']}; border-radius:10px; }}
QTabBar::tab {{ background:transparent; color:{v['sub']}; padding:9px 18px; font-size:13px; border:none; }}
QTabBar::tab:selected {{
    color:{'#388bfd' if dark else '#2563eb'};
    border-bottom:2px solid {'#388bfd' if dark else '#2563eb'}; font-weight:600;
}}
QFrame#MsgUser {{
    background:{'rgba(56,139,253,0.12)' if dark else 'rgba(37,99,235,0.08)'};
    border:1px solid {'rgba(56,139,253,0.2)' if dark else 'rgba(37,99,235,0.15)'};
    border-radius:10px;
}}
QFrame#MsgAdmin {{
    background:{'rgba(63,185,80,0.12)' if dark else 'rgba(22,163,74,0.08)'};
    border:1px solid {'rgba(63,185,80,0.2)' if dark else 'rgba(22,163,74,0.15)'};
    border-radius:10px;
}}
QLineEdit#MsgInput {{
    background:{v['inp_bg']}; border:1.5px solid {v['sep']};
    border-radius:9px; color:{v['text']}; font-size:14px; padding:9px 14px;
}}
QLineEdit#MsgInput:focus {{ border-color:{v['accent']}; }}
QPushButton#SendBtn {{
    background:{v['accent']}; color:white; border:none;
    border-radius:9px; font-size:14px; font-weight:600; padding:9px 18px;
}}
QPushButton#EnterBtn {{
    background:{v['green']}; color:white; border:none;
    border-radius:11px; font-size:16px; font-weight:700; padding:13px 40px;
}}
QPushButton#SettingsBtn {{
    background:{v['accent']}; color:white; border:none;
    border-radius:11px; font-size:15px; font-weight:600; padding:12px 30px;
}}
QPushButton#ExitBtn {{
    background:transparent; color:{v['sub']};
    border:1.5px solid {v['sep']}; border-radius:11px;
    font-size:14px; padding:12px 28px;
}}
QPushButton#ExitBtn:hover {{ color:{v['danger']}; border-color:{v['danger']}; }}
QScrollBar:vertical {{ background:transparent; width:6px; }}
QScrollBar::handle:vertical {{ background:{v['sep']}; border-radius:3px; min-height:20px; }}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {{ height:0; }}
QLabel {{ color:{v['text']}; font-size:13px; }}
"""


def get_session_widget_style(dark=False):
    v = _vars(dark)
    border = "rgba(56,139,253,0.35)" if dark else "rgba(37,99,235,0.25)"
    bg     = "rgba(13,17,23,0.93)"   if dark else "rgba(255,255,255,0.94)"
    return f"""
QFrame#SessionWidget {{
    background:{bg}; border:1.5px solid {border}; border-radius:14px;
}}
QLabel#SwTitle {{ color:{v['sub']}; font-size:10px; font-weight:600; letter-spacing:1px; }}
QLabel#SwTime  {{ color:{v['text']}; font-size:20px; font-weight:700; }}
QLabel#SwSub   {{ color:{v['sub']}; font-size:11px; }}
QLabel#SwApp   {{ color:{v['accent']}; font-size:11px; font-weight:600; }}
QPushButton#SwLogout {{
    background:{v['danger']}; color:white; border:none;
    border-radius:8px; font-size:12px; font-weight:600; padding:5px 10px;
}}
QPushButton#SwLogout:hover {{ background:{v['danger_h']}; }}
QPushButton#SwMinimize {{
    background:{v['btn2']}; color:{v['sub']}; border:none;
    border-radius:6px; font-size:12px; padding:3px 7px;
}}
QPushButton#SwMinimize:hover {{ background:{v['btn2_h']}; color:{v['text']}; }}
"""


def get_exit_screen_style(dark=False):
    v = _vars(dark)
    return f"""
QWidget#ExitScreen {{
    background:qlineargradient(x1:0,y1:0,x2:1,y2:1,
        stop:0 {v['bg1']},stop:1 {v['bg3']});
}}
QFrame#ExitCard {{
    background:{v['card']}; border:1.5px solid {v['border']}; border-radius:20px;
}}
QLabel#ExitTitle {{
    color:{v['text']}; font-size:28px; font-weight:700;
    font-family:'Segoe UI','Arial Hebrew',sans-serif;
}}
QLabel#ExitSub {{
    color:{v['sub']}; font-size:15px;
    font-family:'Segoe UI','Arial Hebrew',sans-serif;
}}
QLabel#ExitTime {{
    color:{v['green']}; font-size:36px; font-weight:200;
    font-family:'Segoe UI',sans-serif; letter-spacing:2px;
}}
QLabel#ExitMsg {{
    color:{v['text']}; font-size:14px; font-style:italic;
    font-family:'Segoe UI','Arial Hebrew',sans-serif;
}}
"""
