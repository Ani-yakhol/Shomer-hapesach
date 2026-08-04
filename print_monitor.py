"""
print_monitor.py - ניטור עבודות הדפסה ברקע וחיוב אוטומטי
שומר הפתח v0.0.8

מזהה הדפסות בכל תוכנה ברמת מערכת ההפעלה,
חייב את המשתמש לפי תעריפים מוגדרים.
"""
import threading
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ── קבועי DEVMODE ───────────────────────────────────────────────
DMPAPER_A3       = 8
DMPAPER_A3_EXTRA = 63
DMCOLOR_COLOR    = 2


class PrintMonitor:
    """
    ניטור עבודות הדפסה בשורת ההדפסה של Windows.

    אלגוריתם:
    1. כל 3 שניות — סורק את תורי ההדפסה של כל מדפסת מנוטרת.
    2. שומר snapshot של job-IDs.
    3. כשJob נעלם מהתור (הודפס) → חייב את המשתמש הנוכחי.
    4. שולח callback ל-main.py שמציג Toast notification.

    שינויים v0.0.8:
    - מציג הודעה גם כשאין משתמש מחובר
    - התאמה רגישה לאות קטנה/גדולה בשם המדפסת
    - ניסיון ראשוני בכל ההפעלה כדי לאתחל snapshot
    - logging מפורט יותר לאיתור תקלות
    """

    POLL_INTERVAL = 3   # שניות בין סריקות

    def __init__(self, config_manager, get_current_user_fn, on_print_charged_fn=None):
        """
        :param config_manager:         ConfigManager
        :param get_current_user_fn:    () -> str | None  (שם המשתמש הנוכחי)
        :param on_print_charged_fn:    (msg: str, pages: int, type_label: str,
                                        cost: float) -> None
        """
        self.cm                  = config_manager
        self.get_current_user    = get_current_user_fn
        self.on_print_charged    = on_print_charged_fn

        self._running            = False
        self._thread: threading.Thread | None = None
        self._seen: dict         = {}   # printer_name -> {job_id -> job_snapshot}
        self._charged_jobs: set  = set()  # job IDs שכבר חויבו (מניעת כפילות)
        self._initialized        = False   # האם ה-snapshot הראשוני נלקח

    # ── הפעלה / עצירה ─────────────────────────────────────────────

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(
            target=self._loop, name="PrintMonitor", daemon=True
        )
        self._thread.start()
        logger.info("PrintMonitor הופעל")

    def stop(self):
        self._running = False
        logger.info("PrintMonitor עצר")

    # ── לולאה ראשית ───────────────────────────────────────────────

    def _loop(self):
        while self._running:
            try:
                self._scan_printers()
            except Exception as e:
                logger.debug(f"PrintMonitor שגיאה: {e}")
            time.sleep(self.POLL_INTERVAL)

    # ── סריקה ─────────────────────────────────────────────────────

    def _scan_printers(self):
        try:
            import win32print
        except ImportError:
            logger.debug("win32print לא מותקן — ניטור הדפסות לא פעיל. הרץ: pip install pywin32")
            return

        username = self.get_current_user()

        # קבל הגדרות מדפסות — כולל אלו שמסומנות כ-limited
        printers_cfg = self.cm.get_printers() if hasattr(self.cm, 'get_printers') else {}
        monitored = {n.lower(): (n, c) for n, c in printers_cfg.items() if c.get("limited")}

        # אם אין מדפסות מנוטרות — נטר את כולן (ניטור ברירת מחדל)
        monitor_all = len(monitored) == 0

        # רשימת מדפסות זמינות במערכת
        try:
            avail_printers = []
            for p in win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS,
                None, 1
            ):
                avail_printers.append(p[2])
        except Exception as e:
            logger.debug(f"EnumPrinters שגיאה: {e}")
            return

        if not avail_printers:
            logger.debug("לא נמצאו מדפסות במערכת")
            return

        for pname in avail_printers:
            pname_lower = pname.lower()

            # בדוק אם מדפסת זו מנוטרת
            if not monitor_all:
                # השוואה גמישה (כולל אם שם המדפסת מכיל את שם הקונפיג)
                pcfg = None
                for key_lower, (orig_name, cfg_val) in monitored.items():
                    if key_lower in pname_lower or pname_lower in key_lower:
                        pcfg = cfg_val
                        break
                if pcfg is None:
                    continue
            else:
                # ניטור כולל — חייב עם תעריף ברירת מחדל 0
                pcfg = {}

            try:
                self._scan_one_printer(pname, username, pcfg)
            except Exception as e:
                logger.debug(f"שגיאה במדפסת {pname}: {e}")

    # סטטוסים המעידים על הדפסה שהושלמה
    JOB_STATUS_PRINTED  = 0x0080
    JOB_STATUS_DELETED  = 0x0100
    JOB_STATUS_DELETING = 0x0004
    JOB_STATUS_COMPLETE = 0x1000

    def _scan_one_printer(self, pname: str, username: str | None, pcfg: dict):
        import win32print

        try:
            handle = win32print.OpenPrinter(pname)
        except Exception as e:
            logger.debug(f"OpenPrinter נכשל עבור {pname}: {e}")
            return

        try:
            try:
                jobs = win32print.EnumJobs(handle, 0, 100, 1)   # עד 100 עבודות
            except Exception as e:
                logger.debug(f"EnumJobs נכשל עבור {pname}: {e}")
                return

            current = {}
            just_printed = []   # עבודות שסטטוסן מעיד על הדפסה שהסתיימה

            for j in jobs:
                jid   = j.get("JobId", 0)
                if not jid:
                    continue
                pages  = j.get("TotalPages") or j.get("PagesPrinted") or 1
                status = j.get("Status", 0)
                snap = {
                    "pages": max(1, pages),
                    "paper": self._paper_from_job(j),
                    "color": self._color_from_job(j),
                    "owner": j.get("pUserName", "") or "",
                }
                # זיהוי לפי סטטוס (מהיר ואמין יותר מהיעלמות)
                if status & (self.JOB_STATUS_PRINTED | self.JOB_STATUS_DELETED |
                             self.JOB_STATUS_DELETING | self.JOB_STATUS_COMPLETE):
                    if jid not in self._charged_jobs:
                        just_printed.append((jid, snap))
                else:
                    current[jid] = snap

            prev = self._seen.get(pname)

            if prev is None:
                # סריקה ראשונה — שמור snapshot, אל תחייב עבודות שכבר הושלמו
                logger.info(f"PrintMonitor: snapshot ראשוני עבור {pname} — {len(current)} עבודות")
                self._seen[pname] = current
                # סמן עבודות שכבר הושלמו כ"כבר טופלו"
                for jid, _ in just_printed:
                    self._charged_jobs.add(jid)
                return

            # זיהוי לפי סטטוס
            for jid, snap in just_printed:
                self._charged_jobs.add(jid)
                logger.info(f"הדפסה הושלמה (סטטוס): {pname} | job {jid} | {snap}")
                self._charge(username, pname, snap, pcfg)

            # זיהוי לפי היעלמות (עבור מדפסות שלא מעדכנות סטטוס)
            disappeared = set(prev.keys()) - set(current.keys())
            for jid in disappeared:
                if jid not in self._charged_jobs:
                    snap = prev[jid]
                    self._charged_jobs.add(jid)
                    logger.info(f"הדפסה הושלמה (היעלמות): {pname} | job {jid} | {snap}")
                    self._charge(username, pname, snap, pcfg)

            self._seen[pname] = current

            # נקה charged_jobs ישנים (מניעת גידול בלתי מוגבל)
            if len(self._charged_jobs) > 500:
                self._charged_jobs.clear()

        finally:
            try:
                win32print.ClosePrinter(handle)
            except Exception:
                pass

    # ── זיהוי סוג הדפסה ────────────────────────────────────────────

    @staticmethod
    def _paper_from_job(job) -> str:
        """מחזיר 'a3' או 'a4' לפי DEVMODE"""
        try:
            dm = job.get("pDevMode")
            if dm:
                ps = getattr(dm, "PaperSize", 0)
                if ps in (DMPAPER_A3, DMPAPER_A3_EXTRA, 67, 68):
                    return "a3"
                pl = getattr(dm, "PaperLength", 0)
                pw = getattr(dm, "PaperWidth",  0)
                if max(pl, pw) > 3500:
                    return "a3"
        except Exception:
            pass
        return "a4"

    @staticmethod
    def _color_from_job(job) -> bool:
        """מחזיר True אם הדפסת צבע"""
        try:
            dm = job.get("pDevMode")
            if dm:
                return getattr(dm, "Color", 1) == DMCOLOR_COLOR
        except Exception:
            pass
        return False

    # ── חיוב ─────────────────────────────────────────────────────

    def _charge(self, username: str | None, pname: str, snap: dict, pcfg: dict):
        pages      = max(1, snap.get("pages", 1))
        paper      = snap.get("paper", "a4")
        is_color   = snap.get("color", False)
        job_owner  = snap.get("owner", "")

        rate_key   = f"{paper}_{'color' if is_color else 'bw'}"
        rates      = pcfg.get("rates", {})
        rate       = rates.get(rate_key, 0.0)

        type_label = ("A3" if paper == "a3" else "A4") + (" צבע" if is_color else " שחל")
        total_cost = rate * pages

        logger.info(
            f"הדפסה: user={username or job_owner or '?'} | {pname} | "
            f"{pages}p | {type_label} | ₪{total_cost:.2f}"
        )

        # ── הצגת Toast תמיד — גם בלי משתמש מחובר ──
        if rate <= 0:
            msg = f"הדפסה: {pages} {'עמוד' if pages == 1 else 'עמודים'} {type_label}"
        else:
            msg = (f"הדפסה: {pages} {'עמוד' if pages == 1 else 'עמודים'} "
                   f"{type_label} | ₪{total_cost:.2f}")

        if self.on_print_charged:
            self.on_print_charged(msg, pages, type_label, total_cost)

        # ── עדכון סטטיסטיקות (רק אם יש משתמש מחובר) ──
        effective_user = username or job_owner
        if not effective_user:
            return

        user = self.cm.get_user(effective_user)
        if not user:
            return

        # עדכון מונה הדפסות
        new_prints = user.get("prints_used", 0) + pages
        self.cm.update_user(effective_user, prints_used=new_prints)

        # עדכון מונה מדפסת
        printers = self.cm.config.setdefault("printers", {})
        printers.setdefault(pname, {})
        printers[pname]["total_prints"] = printers[pname].get("total_prints", 0) + pages
        self.cm.save()

        if rate <= 0:
            return

        # ── ניכוי עלות ──────────────────────────────────────────
        if user.get("print_limit") is not None:
            new_limit = max(0, user["print_limit"] - pages)
            self.cm.update_user(effective_user, print_limit=new_limit)
