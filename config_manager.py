"""
config_manager.py - ניהול הגדרות מלא
שומר הפתח v0.0.9
"""
import json, os, logging, copy
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "version": "2.0.0",
    "lock_screen": {
        "admin_hotkey": "F8",
        "admin_password": "admin",
        "bg_color": "#e8f0fe",
        "bg_image": "",
        "bg_fit": "fill",
        "show_ads": False,
        "ads_images": [],
        "ads_interval": 5,
        "ads_width": 300,
        "clock_time_format": "24",
        "clock_date_mode": "both",
        "clock_text_color": "",
        "show_self_register": False,
        "register_phone_required": False,
        "register_email_required": False,
    },
    "exit_screen": {
        "enabled": True,
        "duration_seconds": 5,
        "custom_messages": [],
        "close_user_apps": False,   # ⚠️ False כברירת מחדל — True עלול לגרום ל-Windows logoff
        "clean_user_files": False,
        "clean_temp": True,
    },
    "general": {
        "startup_enabled": True,
        "block_ctrl_alt_del": True,
        "dark_mode": False,
        "reset_time": "00:00",
        "warning_intervals": [10, 5, 1],
        "show_packages_tab": True,
        "show_messages": True,
        "network_sync_enabled": False,
        "network_role": "standalone",
        "primary_host": "",
        "primary_port": 5765,
        "network_secret": "",
        # ── כיבוי זמני / קבוע ──
        "software_paused": False,      # כיבוי קבוע
        "paused_until": None,          # ISO timestamp — כיבוי זמני עד לשעה זו
    },
    "users": {},
    "packages": [],
    "blocked_apps_global": [],
    "blocked_apps_limited": [],
    "global_blocks": [],
    "kiosk": {"enabled": False, "allowed_apps": []},
    "printers": {},
}

DEFAULT_USER = {
    "password": "1234",
    "is_admin": False,
    "display_name": "",
    "phone": "",
    "email": "",
    "enabled": True,
    "is_limited": True,
    "time_limit_daily": None,
    "time_limit_total": None,
    "is_app_restricted": False,
    "app_limits": {},
    "is_print_restricted": False,
    "print_limit": None,
    "prints_used": 0,
    "messages_blocked": False,
    "blocked_dates": [],
    "blocked_hours": [],
    "blocked_days_of_week": [],
    "packages": [],
    "time_used_today": 0,
    "time_used_today_date": "",
    "time_used_total": 0,
    "session_history": [],
    "messages": [],
}


class ConfigManager:
    def __init__(self, config_path=None):
        if config_path:
            self.config_dir = Path(config_path)
        else:
            app_data = os.environ.get("APPDATA", os.path.expanduser("~"))
            self.config_dir = Path(app_data) / "ShomerHaPetach"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "config.json"
        self.config = self._load()

    def _load(self):
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return self._deep_merge(copy.deepcopy(DEFAULT_CONFIG), data)
            except Exception as e:
                logger.error(f"טעינה נכשלה: {e}")
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg["users"]["מנהל מערכת"] = {
            **copy.deepcopy(DEFAULT_USER),
            "password": "admin", "is_admin": True,
            "display_name": "מנהל מערכת", "is_limited": False,
        }
        self.config = cfg
        self._save()
        return cfg

    def _save(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"שמירה נכשלה: {e}")

    def save(self): self._save()

    def _deep_merge(self, base, override):
        result = base.copy()
        for k, v in override.items():
            if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                result[k] = self._deep_merge(result[k], v)
            else:
                result[k] = v
        return result

    # ── אימות ────────────────────────────────────────────────────
    def verify_user(self, username, password):
        users = self.config.get("users", {})
        if username not in users: return None
        user = users[username]
        if not user.get("enabled", True): return None
        return user if user.get("password") == password else None

    def verify_admin_password(self, password):
        return password == self.config["lock_screen"].get("admin_password", "admin")

    # ── משתמשים ──────────────────────────────────────────────────
    def get_user(self, username): return self.config["users"].get(username)
    def get_all_users(self): return self.config.get("users", {})
    def get_admin_users(self): return [u for u,d in self.config["users"].items() if d.get("is_admin")]

    def create_user(self, username, password, display_name="", is_admin=False, phone="", email="", **kwargs):
        if username in self.config["users"]: return False
        user = copy.deepcopy(DEFAULT_USER)
        user.update({
            "password": password, "is_admin": is_admin,
            "display_name": display_name or username,
            "phone": phone, "email": email,
            "is_limited": False,
            "time_limit_daily": None,
            "time_limit_total": None,
            "print_limit": None,
        })
        user.update(kwargs)
        if is_admin:
            user["is_limited"] = False
        self.config["users"][username] = user
        self._save(); return True

    def update_user(self, username, **kwargs):
        if username not in self.config["users"]: return False
        self.config["users"][username].update(kwargs)
        self._save(); return True

    def delete_user(self, username):
        admins = self.get_admin_users()
        if username in admins and len(admins) <= 1: return False
        if username in self.config["users"]:
            del self.config["users"][username]; self._save(); return True
        return False

    def export_users(self, path):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"users": self.config["users"]}, f, ensure_ascii=False, indent=2)
            return True
        except: return False

    def import_users(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for uname, udata in data.get("users", {}).items():
                self.config["users"][uname] = {**copy.deepcopy(DEFAULT_USER), **udata}
            self._save(); return True
        except: return False

    # ── חבילות ───────────────────────────────────────────────────
    def get_packages(self): return self.config.get("packages", [])

    def add_package(self, pkg):
        import uuid
        pkg["id"] = str(uuid.uuid4())[:8]
        self.config.setdefault("packages", []).append(pkg)
        self._save(); return pkg["id"]

    def update_package(self, pkg_id, **kwargs):
        for p in self.config.get("packages", []):
            if p.get("id") == pkg_id:
                p.update(kwargs); self._save(); return True
        return False

    def delete_package(self, pkg_id):
        pkgs = self.config.get("packages", [])
        self.config["packages"] = [p for p in pkgs if p.get("id") != pkg_id]
        self._save(); return True

    def add_package_to_user(self, username, pkg_id):
        user = self.get_user(username)
        pkg = next((p for p in self.get_packages() if p.get("id")==pkg_id), None)
        if not user or not pkg: return False
        if pkg["type"] == "time":
            mins = pkg.get("value", 0)
            daily = pkg.get("daily_limit")
            if daily:
                user["time_limit_daily"] = (user.get("time_limit_daily") or 0) + daily
            else:
                user["time_limit_total"] = (user.get("time_limit_total") or 0) + mins
        elif pkg["type"] == "print":
            user["print_limit"] = (user.get("print_limit") or 0) + pkg.get("value", 0)
        user.setdefault("packages", []).append(pkg_id)
        self._save(); return True

    # ── זמן ──────────────────────────────────────────────────────
    def get_time_used_today(self, username):
        user = self.get_user(username)
        if not user: return 0
        today = datetime.now().strftime("%Y-%m-%d")
        if user.get("time_used_today_date") != today: return 0
        return user.get("time_used_today", 0)

    def add_time_used(self, username, seconds):
        user = self.get_user(username)
        if not user: return
        today = datetime.now().strftime("%Y-%m-%d")
        if user.get("time_used_today_date") != today:
            user["time_used_today"] = 0; user["time_used_today_date"] = today
        user["time_used_today"] = user.get("time_used_today", 0) + seconds
        user["time_used_total"] = user.get("time_used_total", 0) + seconds
        self._save()

    def get_remaining_time_today(self, username):
        user = self.get_user(username)
        if not user or not user.get("is_limited"): return None
        daily = user.get("time_limit_daily")
        if daily is None: return None
        return max(0, daily * 60 - self.get_time_used_today(username))

    # ── חסימות ───────────────────────────────────────────────────
    def is_user_blocked_now(self, username):
        user = self.get_user(username)
        if not user: return True, "משתמש לא קיים"
        if not user.get("enabled", True): return True, "חשבון מושבת"
        if user.get("is_admin"): return False, ""
        now = datetime.now()
        for block in self.config.get("global_blocks", []):
            if self._matches_block(block, now):
                return True, f"חסימה כללית: {block.get('name','')}"
        today_str = now.strftime("%Y-%m-%d")
        if today_str in user.get("blocked_dates", []):
            return True, f"חסומ/ה בתאריך {today_str}"
        py_to_il = {6:0,0:1,1:2,2:3,3:4,4:5,5:6}
        il_day = py_to_il.get(now.weekday(), now.weekday())
        if il_day in user.get("blocked_days_of_week", []):
            return True, "חסומ/ה ביום זה"
        cur = now.strftime("%H:%M")
        for bh in user.get("blocked_hours", []):
            frm, to = bh.get("from",""), bh.get("to","")
            if frm and to:
                if frm <= to:
                    if frm <= cur <= to: return True, f"חסומ/ה {frm}–{to}"
                else:
                    if cur >= frm or cur <= to: return True, f"חסומ/ה {frm}–{to}"
        rem = self.get_remaining_time_today(username)
        if rem is not None and rem <= 0: return True, "נגמר זמן השימוש"
        gen = self.get_general_cfg()
        if gen.get("block_shabbat_chag", False):
            try:
                from hebrew_calendar import is_blocked_shabbat_chag
                lat = gen.get("location_lat", 31.7683)
                lon = gen.get("location_lon", 35.2137)
                mins_before = gen.get("shabbat_mins_before", 40)
                mins_after  = gen.get("shabbat_mins_after",  40)
                blocked, reason = is_blocked_shabbat_chag(lat, lon, mins_before, mins_after)
                if blocked:
                    return True, reason
            except Exception:
                pass
        return False, ""

    def _matches_block(self, block, now):
        btype = block.get("type","")
        # שעות (תמיכה בשדות ישנים ובחדשים)
        time_from = block.get("time_from") or block.get("from","")
        time_to   = block.get("time_to")   or block.get("to","")

        def _time_matches():
            if not time_from or not time_to:
                return True   # ללא הגבלת שעות
            cur = now.strftime("%H:%M")
            if time_from <= time_to:
                return time_from <= cur <= time_to
            return cur >= time_from or cur <= time_to

        if btype == "weekday":
            # ימים: 0=ראשון...6=שבת (IL convention)
            py_to_il = {6:0,0:1,1:2,2:3,3:4,4:5,5:6}
            il_day = py_to_il.get(now.weekday(), now.weekday())
            if il_day not in block.get("days",[]):
                return False
            return _time_matches()

        if btype == "daterange":
            date_str  = now.strftime("%Y-%m-%d")
            date_from = block.get("date_from","")
            date_to   = block.get("date_to","")
            if date_from and date_to:
                if not (date_from <= date_str <= date_to):
                    return False
            return _time_matches()

        if btype == "hours":
            return _time_matches()

        if btype == "date":
            return now.strftime("%Y-%m-%d") == block.get("date","")

        return False

    # ── כיבוי זמני / קבוע ────────────────────────────────────────
    def is_software_paused(self) -> tuple[bool, str]:
        """
        בדיקה אם התוכנה כבויה כרגע.
        מחזיר (is_paused, reason_text).
        מטפל גם בכיבוי זמני שפג תוקפו.
        """
        gen = self.config.get("general", {})

        # כיבוי קבוע
        if gen.get("software_paused", False):
            # בדוק אם יש גם תאריך סיום (כיבוי זמני שהוגדר כקבוע בטעות)
            paused_until = gen.get("paused_until")
            if paused_until:
                try:
                    until_dt = datetime.fromisoformat(paused_until)
                    if datetime.now() >= until_dt:
                        # פג תוקפו — הפעל מחדש
                        gen["software_paused"] = False
                        gen["paused_until"] = None
                        self._save()
                        return False, ""
                    mins_left = int((until_dt - datetime.now()).total_seconds() / 60)
                    return True, f"כבוי זמנית עוד {mins_left} דקות"
                except Exception:
                    pass
            return True, "כבוי ידנית"

        # כיבוי זמני (paused_until בלבד)
        paused_until = gen.get("paused_until")
        if paused_until:
            try:
                until_dt = datetime.fromisoformat(paused_until)
                if datetime.now() < until_dt:
                    mins_left = int((until_dt - datetime.now()).total_seconds() / 60)
                    return True, f"כבוי זמנית עוד {mins_left} דקות"
                else:
                    # פג תוקפו
                    gen["paused_until"] = None
                    self._save()
            except Exception:
                gen["paused_until"] = None
                self._save()

        return False, ""

    def pause_software_permanent(self):
        """כיבוי קבוע של התוכנה"""
        gen = self.config.setdefault("general", {})
        gen["software_paused"] = True
        gen["paused_until"] = None
        self._save()

    def pause_software_temp(self, minutes: int):
        """כיבוי זמני לפרק זמן מוגדר (בדקות)"""
        from datetime import timedelta
        gen = self.config.setdefault("general", {})
        until = datetime.now() + timedelta(minutes=minutes)
        gen["software_paused"] = True
        gen["paused_until"] = until.isoformat()
        self._save()

    def resume_software(self):
        """הפעלה מחדש של התוכנה"""
        gen = self.config.setdefault("general", {})
        gen["software_paused"] = False
        gen["paused_until"] = None
        self._save()

    # ── הודעות ───────────────────────────────────────────────────
    def add_message_from_user(self, username, text):
        user = self.get_user(username)
        if not user: return
        user.setdefault("messages",[]).append({"from":"user","text":text,"time":datetime.now().isoformat(),"read":False})
        self._save()

    def add_reply_from_admin(self, username, text):
        user = self.get_user(username)
        if not user: return
        user.setdefault("messages",[]).append({"from":"admin","text":text,"time":datetime.now().isoformat(),"read":False})
        self._save()

    def unread_messages_count(self):
        return sum(1 for u in self.config["users"].values()
                   for m in u.get("messages",[]) if m.get("from")=="user" and not m.get("read"))

    # ── ייצוא / ייבוא ────────────────────────────────────────────
    def export_all(self, path):
        try:
            import shutil; shutil.copy2(self.config_file, path); return True
        except: return False

    def import_all(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.config = self._deep_merge(copy.deepcopy(DEFAULT_CONFIG), data)
            self._save(); return True
        except: return False

    # ── נוחות ────────────────────────────────────────────────────
    def is_dark_mode(self): return self.config["general"].get("dark_mode", False)
    def set_dark_mode(self, v): self.config["general"]["dark_mode"]=v; self._save()
    def get_lock_screen_cfg(self): return self.config.get("lock_screen",{})
    def get_exit_screen_cfg(self): return self.config.get("exit_screen",{})
    def get_general_cfg(self): return self.config.get("general",{})
    def get_warning_intervals(self): return self.config["general"].get("warning_intervals",[10,5,1])
    def get_printers(self): return self.config.get("printers",{})
    def get_global_blocks(self): return self.config.get("global_blocks",[])
    def add_session_history(self, username, entry):
        user = self.get_user(username)
        if not user: return
        h = user.setdefault("session_history",[])
        h.append(entry)
        if len(h) > 200: user["session_history"] = h[-200:]
        self._save()

    def get_total_stats(self):
        users = self.config["users"]
        return {
            "total_users": len(users),
            "admin_users": len(self.get_admin_users()),
            "total_usage_seconds": sum(u.get("time_used_total",0) for u in users.values()),
            "total_prints": sum(u.get("prints_used",0) for u in users.values()),
            "active_today": sum(1 for u in users.values()
                if u.get("time_used_today_date")==datetime.now().strftime("%Y-%m-%d")
                and u.get("time_used_today",0)>0),
        }
