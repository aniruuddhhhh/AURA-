import sqlite3
import pandas as pd
import os
import time

DB_NAME = "gemini_aura_health.db"
FILES_TO_LOAD = {
    "heart_rate":       "AURA_Final_Combined_HR (1).csv",
    "daily_activity":   "dailyActivity_merged.csv",
    "sleep_logs":       "sleepDay_merged.csv",
    "hrv":              "hrv5mins_session.csv",
    "steps_5min":       "Steps_5min_sessions.csv",
    "mets_5min":        "METs_5min_sessions.csv",
    "calories_5min":    "calories_5min_sessions.csv",
    "intensities_5min": "Intensities_5min_sessions.csv",
    "hourly_summary":   "hourly_activity_combined.csv",
}
TIME_COLS = ["Time", "ActivityDate", "SleepDay", "ActivityMinute", "ActivityHour"]

def build_numerical_vault() -> None:
    start = time.time()
    print(f" Gemini AURA: Numerical DB ({DB_NAME}) ---")
    conn = sqlite3.connect(DB_NAME)

    for table_name, file_path in FILES_TO_LOAD.items():
        if not os.path.exists(file_path):
            print(f" Skipping missing: {file_path}")
            continue
        print(f"  Loading {table_name}...")
        df = pd.read_csv(file_path)
        date_col = next((c for c in TIME_COLS if c in df.columns), None)
        if date_col:
            df[date_col] = pd.to_datetime(df[date_col]).dt.strftime("%Y-%m-%d %H:%M:%S")
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        print(f" Yes {len(df):,} records → '{table_name}'")

    cursor = conn.cursor()
    for cmd in [
        "CREATE INDEX IF NOT EXISTS idx_hr_time   ON heart_rate     (Time);",
        "CREATE INDEX IF NOT EXISTS idx_hr_id     ON heart_rate     (Id, Time);",
        "CREATE INDEX IF NOT EXISTS idx_sleep_day ON sleep_logs     (SleepDay);",
        "CREATE INDEX IF NOT EXISTS idx_act_date  ON daily_activity (ActivityDate);",
    ]:
        try:
            cursor.execute(cmd)
        except sqlite3.OperationalError as e:
            print(f" Index skipped: {e}")
    conn.commit()
    try:
        test_user = 1503960366
        cursor.execute("SELECT MAX(Value) FROM heart_rate WHERE Id = ?", (test_user,))
        row = cursor.fetchone()
        if row and row[0]:
            print(f"\n Verification: User {test_user} max HR = {row[0]:.1f} BPM Yes")
    except Exception as e:
        print(f"\n  Verification failed: {e}")

    conn.close()
    print(f"\n Gemini AURA database done, Time: {time.time() - start:.2f}s")
    
if __name__ == "__main__":
    build_numerical_vault()
