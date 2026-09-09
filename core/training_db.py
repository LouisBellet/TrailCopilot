import sqlite3
import json
import os
import sys

def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(".")

DB_PATH = os.path.join(get_app_dir(), "user_data.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=15.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            height_cm REAL DEFAULT 178.0,
            weight_kg REAL DEFAULT 70.0,
            age INTEGER DEFAULT 30,
            hr_rest INTEGER DEFAULT 50,
            hr_max INTEGER DEFAULT 185,
            vma REAL DEFAULT 15.0,
            lactate_threshold_hr INTEGER DEFAULT 165
        )
        """)

        cursor.execute("PRAGMA table_info(profile)")
        cols = [r["name"] for r in cursor.fetchall()]
        if "height_cm" not in cols:
            cursor.execute("ALTER TABLE profile ADD COLUMN height_cm REAL DEFAULT 178.0")
        if "weight_kg" not in cols:
            cursor.execute("ALTER TABLE profile ADD COLUMN weight_kg REAL DEFAULT 70.0")
        if "age" not in cols:
            cursor.execute("ALTER TABLE profile ADD COLUMN age INTEGER DEFAULT 30")
        if "lactate_threshold_hr" not in cols:
            cursor.execute("ALTER TABLE profile ADD COLUMN lactate_threshold_hr INTEGER DEFAULT 165")

        cursor.execute("""
        INSERT OR IGNORE INTO profile (id, height_cm, weight_kg, age, hr_rest, hr_max, vma, lactate_threshold_hr)
        VALUES (1, 178.0, 70.0, 30, 50, 185, 15.0, 165)
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE,
            start_time TEXT,
            name TEXT,
            sport TEXT,
            distance_km REAL,
            d_plus REAL,
            d_minus REAL,
            duration_min REAL,
            avg_hr INTEGER,
            max_hr INTEGER,
            trimp REAL,
            records_json TEXT
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_health (
            date TEXT PRIMARY KEY,
            resting_hr INTEGER,
            hrv_rmssd REAL,
            sleep_hours REAL,
            recovery_score INTEGER
        )
        """)
        conn.commit()

def get_user_profile() -> dict:
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT height_cm, weight_kg, age, hr_rest, hr_max, vma, lactate_threshold_hr FROM profile WHERE id = 1")
        row = cursor.fetchone()
        if row:
            return dict(row)
        return {"height_cm": 178.0, "weight_kg": 70.0, "age": 30, "hr_rest": 50, "hr_max": 185, "vma": 15.0, "lactate_threshold_hr": 165}

def update_user_profile(height_cm: float, weight_kg: float, age: int, hr_rest: int, hr_max: int, vma: float, lactate_threshold_hr: int):
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE profile SET
            height_cm = ?, weight_kg = ?, age = ?, hr_rest = ?, hr_max = ?, vma = ?, lactate_threshold_hr = ?
        WHERE id = 1
        """, (height_cm, weight_kg, age, hr_rest, hr_max, vma, lactate_threshold_hr))
        conn.commit()

def save_daily_health(date_str: str, rhr: int, rmssd: float, sleep_h: float, score: int):
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO daily_health (date, resting_hr, hrv_rmssd, sleep_hours, recovery_score)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(date) DO UPDATE SET
            resting_hr=excluded.resting_hr,
            hrv_rmssd=excluded.hrv_rmssd,
            sleep_hours=excluded.sleep_hours,
            recovery_score=excluded.recovery_score
        """, (date_str, rhr, rmssd, sleep_h, score))
        conn.commit()

def get_all_daily_health() -> list:
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT date, resting_hr, hrv_rmssd, sleep_hours, recovery_score FROM daily_health ORDER BY date DESC")
        return [dict(r) for r in cursor.fetchall()]

def get_latest_health():
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM daily_health ORDER BY date DESC LIMIT 1")
        row = cursor.fetchone()
        return dict(row) if row else None

def get_health_baselines(days=30) -> dict:
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT resting_hr, hrv_rmssd FROM daily_health ORDER BY date DESC LIMIT ?", (days,))
        rows = cursor.fetchall()
        if not rows:
            return {"baseline_rhr": 50, "baseline_rmssd": 60.0}
        rhrs = [r["resting_hr"] for r in rows if r["resting_hr"]]
        rmssds = [r["hrv_rmssd"] for r in rows if r["hrv_rmssd"]]
        return {
            "baseline_rhr": round(sum(rhrs)/len(rhrs), 1) if rhrs else 50,
            "baseline_rmssd": round(sum(rmssds)/len(rmssds), 1) if rmssds else 60.0
        }

def save_activity(act: dict) -> bool:
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
            INSERT INTO activities (
                filename, start_time, name, sport, distance_km, 
                d_plus, d_minus, duration_min, avg_hr, max_hr, trimp, records_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(filename) DO UPDATE SET
                start_time=excluded.start_time,
                distance_km=excluded.distance_km,
                d_plus=excluded.d_plus,
                d_minus=excluded.d_minus,
                duration_min=excluded.duration_min,
                avg_hr=excluded.avg_hr,
                max_hr=excluded.max_hr,
                trimp=excluded.trimp,
                records_json=excluded.records_json
            """, (
                act["filename"], act["start_time"], act["name"], act["sport"],
                act["distance_km"], act["d_plus"], act["d_minus"], act["duration_min"],
                act["avg_hr"], act["max_hr"], act["trimp"], json.dumps(act.get("records", []))
            ))
            conn.commit()
            return True
        except Exception:
            return False

def get_all_activities() -> list:
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, filename, start_time, name, sport, distance_km, d_plus, d_minus, duration_min, avg_hr, max_hr, trimp FROM activities ORDER BY start_time DESC")
        return [dict(row) for row in cursor.fetchall()]

def get_activity_details(activity_id: int) -> dict:
    init_db()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM activities WHERE id = ?", (activity_id,))
        row = cursor.fetchone()
        if not row:
            return {}
        data = dict(row)
        data["records"] = json.loads(data["records_json"]) if data.get("records_json") else []
        return data