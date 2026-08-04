"""
registry_manager.py - ניהול רג'סטרי Windows
שומר הפתח
"""

import os
import subprocess
import logging
import sys

logger = logging.getLogger(__name__)

# נתיבי רג'סטרי
REG_EXPLORER  = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer"
REG_SYSTEM_CU = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\System"
REG_SYSTEM_LM = r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System"
REG_RUN_LM    = r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
REG_RUN_CU    = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run"

APP_NAME = "ShomerHaPetach"


def _reg_run(args: list) -> bool:
    """מריץ פקודת reg.exe"""
    try:
        result = subprocess.run(
            ["reg"] + args,
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        return result.returncode == 0
    except Exception as e:
        logger.error(f"reg.exe שגיאה: {e}")
        return False


def _reg_write(hive_str: str, key_path: str, value_name: str, value: int) -> bool:
    """כותב ערך DWORD לרג'סטרי ישירות דרך winreg (ללא reg.exe)"""
    try:
        import winreg
        hive_map = {
            "HKCU": winreg.HKEY_CURRENT_USER,
            "HKLM": winreg.HKEY_LOCAL_MACHINE,
        }
        hive = hive_map.get(hive_str, winreg.HKEY_CURRENT_USER)
        with winreg.CreateKeyEx(hive, key_path, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, value_name, 0, winreg.REG_DWORD, value)
        return True
    except Exception as e:
        logger.warning(f"winreg כתיבה נכשלה ({key_path}\\{value_name}): {e}")
        return False


def _reg_delete(hive_str: str, key_path: str, value_name: str) -> bool:
    """מוחק ערך מהרג'סטרי דרך winreg"""
    try:
        import winreg
        hive_map = {
            "HKCU": winreg.HKEY_CURRENT_USER,
            "HKLM": winreg.HKEY_LOCAL_MACHINE,
        }
        hive = hive_map.get(hive_str, winreg.HKEY_CURRENT_USER)
        with winreg.OpenKey(hive, key_path, 0, winreg.KEY_SET_VALUE) as k:
            winreg.DeleteValue(k, value_name)
        return True
    except FileNotFoundError:
        return True   # הערך לא קיים — זה בסדר
    except Exception as e:
        logger.warning(f"winreg מחיקה נכשלה: {e}")
        return False


def _reg_import(filepath: str) -> bool:
    """מייבא קובץ .reg"""
    try:
        result = subprocess.run(
            ["reg", "import", filepath],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        return result.returncode == 0
    except Exception as e:
        logger.error(f"reg import שגיאה: {e}")
        return False


# ── Ctrl+Alt+Del ─────────────────────────────────────────────────

def block_ctrl_alt_del() -> bool:
    """חוסם Ctrl+Alt+Del, מקש Windows ופעולות מערכת — ישירות דרך winreg (ללא קבצי .reg)"""
    ok = True
    # HKCU Explorer policies
    for val_name in ["NoLogoff", "NoClose", "NoWinKeys"]:
        ok &= _reg_write("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer", val_name, 1)
    # HKCU System policies
    for val_name in ["DisableLockWorkstation", "DisableTaskMgr", "DisableChangePassword"]:
        ok &= _reg_write("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Policies\System", val_name, 1)
    # HKLM System policies (דורש מנהל)
    ok &= _reg_write("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System", "HideFastUserSwitching", 1)
    logger.info(f"חסימת מקשי מערכת: {'הצליחה' if ok else 'נכשלה חלקית'}")
    return ok


def unblock_ctrl_alt_del() -> bool:
    """משחרר חסימת Ctrl+Alt+Del ומקש Windows"""
    for val_name in ["NoLogoff", "NoClose", "NoWinKeys"]:
        _reg_delete("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer", val_name)
    for val_name in ["DisableLockWorkstation", "DisableTaskMgr", "DisableChangePassword"]:
        _reg_delete("HKCU", r"Software\Microsoft\Windows\CurrentVersion\Policies\System", val_name)
    _reg_delete("HKLM", r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System", "HideFastUserSwitching")
    logger.info("שחרור חסימות מקשי מערכת")
    return True


# ── הפעלה אוטומטית ───────────────────────────────────────────────

def add_to_startup(exe_path: str = None) -> bool:
    """
    מוסיף את שומר הפתח להפעלה אוטומטית עם Windows.
    משתמש ב-HKLM Run לטעינה מהירה ככל האפשר.
    """
    if exe_path is None:
        # נסה למצוא pythonw.exe עם main.py
        script = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "main.py")
        )
        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        if not os.path.exists(pythonw):
            pythonw = sys.executable
        exe_path = f'"{pythonw}" "{script}"'

    ok = _reg_run([
        "add", REG_RUN_LM,
        "/v", APP_NAME,
        "/t", "REG_SZ",
        "/d", exe_path,
        "/f"
    ])
    # גיבוי ב-HKCU אם HKLM נכשל (ללא הרשאות מנהל)
    if not ok:
        ok = _reg_run([
            "add", REG_RUN_CU,
            "/v", APP_NAME,
            "/t", "REG_SZ",
            "/d", exe_path,
            "/f"
        ])
    logger.info(f"הוספה להפעלה אוטומטית: {'הצליחה' if ok else 'נכשלה'}")
    return ok


def remove_from_startup() -> bool:
    """מסיר מהפעלה אוטומטית"""
    _reg_run(["delete", REG_RUN_LM, "/v", APP_NAME, "/f"])
    _reg_run(["delete", REG_RUN_CU, "/v", APP_NAME, "/f"])
    logger.info("הוסר מהפעלה אוטומטית")
    return True


def is_in_startup() -> bool:
    """בודק אם רשום להפעלה אוטומטית"""
    result = subprocess.run(
        ["reg", "query", REG_RUN_LM, "/v", APP_NAME],
        capture_output=True,
        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
    )
    if result.returncode == 0:
        return True
    result2 = subprocess.run(
        ["reg", "query", REG_RUN_CU, "/v", APP_NAME],
        capture_output=True,
        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
    )
    return result2.returncode == 0


# ── ייצוא / ייבוא ────────────────────────────────────────────────

def export_reg_file(block: bool, output_path: str) -> bool:
    """
    כותב קובץ .reg לחסימה או שחרור.
    block=True → BlockACD.reg | block=False → UnblockACD.reg
    """
    src = os.path.join(os.path.dirname(__file__),
                       "BlockACD.reg" if block else "UnblockACD.reg")
    if os.path.exists(src):
        import shutil
        shutil.copy2(src, output_path)
        return True
    # יצור דינמית
    content = _build_reg_content(block)
    try:
        with open(output_path, "w", encoding="utf-16") as f:
            f.write(content)
        return True
    except Exception as e:
        logger.error(f"כתיבת reg נכשלה: {e}")
        return False


def _build_reg_content(block: bool) -> str:
    if block:
        return """Windows Registry Editor Version 5.00

[HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\Explorer]
"NoLogoff"=dword:00000001
"NoClose"=dword:00000001

[HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\System]
"DisableLockWorkstation"=dword:00000001
"DisableTaskMgr"=dword:00000001
"DisableChangePassword"=dword:00000001

[HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System]
"HideFastUserSwitching"=dword:00000001
"""
    else:
        return """Windows Registry Editor Version 5.00

[HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\Explorer]
"NoLogoff"=-
"NoClose"=-

[HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Policies\\System]
"DisableLockWorkstation"=-
"DisableTaskMgr"=-
"DisableChangePassword"=-

[HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System]
"HideFastUserSwitching"=-
"""
