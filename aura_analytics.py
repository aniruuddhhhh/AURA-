import sqlite3
import re
import pandas as pd
from sentence_transformers import SentenceTransformer
from langchain_chroma import Chroma

CURRENT_USER_ID = 1503960366
SQL_DB_PATH = "aura_health.db"
VECTOR_DB_DIR = "./aura_vector_db_hf"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

print(" Starting AURA ")

class DirectEmbeddings:
    def __init__(self, model_name):
        self.model = SentenceTransformer(model_name)
    
    def embed_documents(self, texts):
        return self.model.encode(texts).tolist()
    
    def embed_query(self, text):
        return self.model.encode([text])[0].tolist()    
try:
    _embeddings = DirectEmbeddings(EMBED_MODEL)
    _vector_db = Chroma(persist_directory=VECTOR_DB_DIR, embedding_function=_embeddings)
    print(" Vector DB loaded")
except Exception as e:
    print(f" Vector DB error: {e}")
    _vector_db = None

def get_sql(query: str, date: str) -> str:
    q = query.lower()
    if "sleep" in q:
        if "compare" in q or " to " in q:
            dates = re.findall(r'(april|may)\s+(\d+)', q)
            if len(dates) >= 2:
                m1 = 4 if dates[0][0] == "april" else 5
                d1 = int(dates[0][1])
                m2 = 4 if dates[1][0] == "april" else 5
                d2 = int(dates[1][1])
                return f"SELECT SleepDay, TotalMinutesAsleep, TotalTimeInBed FROM sleep_logs WHERE Id = {CURRENT_USER_ID} AND SleepDay >= '2016-{m1:02d}-{d1:02d}' AND SleepDay <= '2016-{m2:02d}-{d2:02d}' ORDER BY SleepDay"
        if date:
            return f"SELECT SleepDay, TotalMinutesAsleep, TotalTimeInBed FROM sleep_logs WHERE Id = {CURRENT_USER_ID} AND SleepDay LIKE '{date}%'"    
    if "heart" in q or "hr" in q:
        if date:
            return f"SELECT Time, Value FROM heart_rate WHERE Id = {CURRENT_USER_ID} AND Time LIKE '{date}%' ORDER BY Value DESC LIMIT 10"    
    return None

def execute_sql(sql: str) -> str:
    conn = sqlite3.connect(SQL_DB_PATH)
    try:
        df = pd.read_sql_query(sql, conn)
        conn.close()
        if df.empty:
            return "No data found"
        return df.to_string(index=False)
    except Exception as e:
        conn.close()
        return f"Error: {e}"

def search_journals(query: str, date: str = None) -> str:
    if not _vector_db:
        return ""
    try:
        if date:
            parts = date.split('-')
            month = "april" if parts[1] == "04" else "may"
            day = int(parts[2])
            sq = f"{month} {day} 2016"
        else:
            sq = query
        results = _vector_db.similarity_search(sq, k=50, filter={"user_id": str(CURRENT_USER_ID)})
        if date:
            results = [r for r in results if r.metadata.get('timestamp', '')[:10] == date]
        if not results:
            return ""
        return "\n".join([f"[{r.metadata.get('timestamp', '')[:10]}] {r.page_content[:150]}" for r in results[:3]])
    except:
        return ""

def parse_date(query: str) -> str:
    m = re.search(r'(april|may)\s+(\d+)', query.lower())
    if m:
        month = 4 if m.group(1) == "april" else 5
        return f"2016-{month:02d}-{int(m.group(2)):02d}"
    return None

def run_query(user_input: str, chat_history: list[dict] | None = None) -> str: 
    date = parse_date(user_input)
    sql = get_sql(user_input, date)
    
    if not sql:
        return "Try: 'sleep on April 12' or 'heart rate on May 2'"
    data = execute_sql(sql)
    journal = search_journals(user_input, date)
    
    result = f" Data for {date if date else 'query'}:\n\n{data}"
    if journal:
        result += f"\n\n Journal Entries:\n{journal}"
    return result
print(" AURA Online")