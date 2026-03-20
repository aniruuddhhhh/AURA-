
import sqlite3
import re
import pandas as pd
from datetime import datetime

from langchain_ollama import ChatOllama
from sentence_transformers import SentenceTransformer
from langchain_chroma import Chroma

CURRENT_USER_ID = 1503960366
SQL_DB_PATH = "aura_health.db"
VECTOR_DB_DIR = "./aura_vector_db_hf"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
LLM_MODEL = "llama3.2"

import sys
DEBUG_MODE = not any('streamlit' in arg.lower() for arg in sys.argv)

print(" Starting AURA...")

class DirectEmbeddings:
    def __init__(self, model_name):
        self.model = SentenceTransformer(model_name)
    
    def embed_documents(self, texts):
        return self.model.encode(texts).tolist()
    
    def embed_query(self, text):
        return self.model.encode([text])[0].tolist()

_embeddings = None
_vector_db = None

try:
    print(" Step 1/3: Loading embedding model...")
    _embeddings = DirectEmbeddings(EMBED_MODEL)
    print(" Step 1/3: Embeddings loaded")
    
    print(" Step 2/3: Initializing vector database...")
    import sys
    sys.stdout.flush()     
    _vector_db = Chroma(
        persist_directory=VECTOR_DB_DIR, 
        embedding_function=_embeddings
    )
    
    print(" Step 2/3: Vector DB object created - Done")
    print(" Step 3/3: Vector DB ready")
        
except KeyboardInterrupt:
    print("AURA will run without vector DB ")
    _vector_db = None
    _embeddings = None
    
except Exception as e:
    print(f"Vector DB initialization failed: {e}")
    print(f" Error type: {type(e).__name__}")
    import traceback
    print("   Full traceback:")
    traceback.print_exc()
    print("\n AURA will run without vector DB ")
    _vector_db = None
    _embeddings = None


def get_template_sql(user_query: str, date: str) -> str:
    user_lower = user_query.lower()
    if "sleep" in user_lower:
        if "compare" in user_lower or "to" in user_lower:
            dates = re.findall(r'(april|may)\s+(\d+)', user_lower)
            if len(dates) >= 2:
                month1 = 4 if dates[0][0] == "april" else 5
                day1 = int(dates[0][1])
                month2 = 4 if dates[1][0] == "april" else 5
                day2 = int(dates[1][1])
                
                return f"""SELECT SleepDay, TotalMinutesAsleep, TotalTimeInBed 
                          FROM sleep_logs 
                          WHERE Id = {CURRENT_USER_ID} 
                          AND SleepDay >= '2016-{month1:02d}-{day1:02d}' 
                          AND SleepDay <= '2016-{month2:02d}-{day2:02d}' 
                          ORDER BY SleepDay"""
        
        elif "less than" in user_lower or "under" in user_lower:
            hours = re.search(r'(\d+)\s*hour', user_lower)
            if hours:
                minutes = int(hours.group(1)) * 60
                return f"""SELECT SleepDay, TotalMinutesAsleep 
                          FROM sleep_logs 
                          WHERE Id = {CURRENT_USER_ID} 
                          AND TotalMinutesAsleep < {minutes} 
                          ORDER BY TotalMinutesAsleep"""
        
        elif date:
            return f"""SELECT SleepDay, TotalMinutesAsleep, TotalTimeInBed 
                      FROM sleep_logs 
                      WHERE Id = {CURRENT_USER_ID} 
                      AND SleepDay LIKE '{date}%'"""
    
    elif "heart" in user_lower or "hr" in user_lower:
        if date:
            return f"""SELECT Time, Value 
                      FROM heart_rate 
                      WHERE Id = {CURRENT_USER_ID} 
                      AND Time LIKE '{date}%' 
                      ORDER BY Value DESC 
                      LIMIT 10"""
        elif "high" in user_lower or "above" in user_lower:
            return f"""SELECT Time, Value 
                      FROM heart_rate 
                      WHERE Id = {CURRENT_USER_ID} 
                      AND Value > 100 
                      ORDER BY Value DESC 
                      LIMIT 10"""
    
    elif "step" in user_lower or "walk" in user_lower:
        if date:
            return f"""SELECT ActivityDate, TotalSteps, Calories 
                      FROM daily_activity 
                      WHERE Id = {CURRENT_USER_ID} 
                      AND ActivityDate LIKE '{date}%'"""
    
    return None

def execute_sql(sql: str) -> tuple[str, bool]:
    """Execute SQL and return (results, has_data)."""
    print(f"\n[AURA]  Executing SQL:")
    print(f"{'─' * 5}")
    print(sql)
    print(f"{'─' * 5}\n")
    
    conn = sqlite3.connect(SQL_DB_PATH)
    try:
        df = pd.read_sql_query(sql, conn)
        conn.close()
        
        has_data = not df.empty
        
        if not has_data:
            print(f"[AURA] Error - Query returned 0 rows")
            return "No data found.", False
        
        print(f"[AURA] Yes- Query returned {len(df)} rows")
        print(f"[AURA]  Data preview:")
        print(f"{'─' * 5}")
        print(df.to_string(index=False))
        print(f"{'─' * 5}\n")
        
        result = df.to_string(index=False) if len(df) <= 20 else df.head(20).to_string(index=False) + f"\n... ({len(df)-20}"
        return result, True
        
    except Exception as e:
        conn.close()
        print(f"[AURA] SQL error: {e}")
        return f"Error: {e}", False

def generate_llm_sql(user_query: str, date: str = None) -> str:
    try:
        llm = ChatOllama(model=LLM_MODEL, temperature=0, timeout=10)
        
        schema = f"""Database Schema:
- heart_rate (Id, Time, Value) — Time format: 'YYYY-MM-DD HH:MM:SS'
- sleep_logs (Id, SleepDay, TotalMinutesAsleep, TotalTimeInBed) — SleepDay format: 'YYYY-MM-DD HH:MM:SS'
- daily_activity (Id, ActivityDate, TotalSteps, Calories) — ActivityDate format: 'YYYY-MM-DD HH:MM:SS'

User ID: {CURRENT_USER_ID}

CRITICAL DATE RULES:
1. ALL date columns contain timestamps in format 'YYYY-MM-DD HH:MM:SS'
2. ALWAYS use LIKE 'YYYY-MM-DD%' for date matching (NOT = 'YYYY-MM-DD')
3. Example: WHERE SleepDay LIKE '2016-04-17%' NOT WHERE SleepDay = '2016-04-17'
4. ALWAYS include WHERE Id = {CURRENT_USER_ID}"""
        
        if date:
            schema += f"\n\nExtracted Date: {date} (use LIKE '{date}%' in WHERE clause)"
        
        prompt = f"""{schema}

User Query: {user_query}

Generate a SELECT query following the rules above:"""
        
        response = llm.invoke(prompt)
        sql = response.content.strip()
        
        sql = sql.replace('```sql', '').replace('```', '').strip()
        
        if sql.upper().startswith('SELECT') and 'DROP' not in sql.upper() and 'DELETE' not in sql.upper():
            return sql
        
        return None
        
    except Exception as e:
        print(f"[AURA] LLM error: {e}")
        return None

def generate_sql_with_fallback(user_query: str, date: str = None) -> tuple[str, str, bool]:
    print(f"[AURA] Generating SQL for: {user_query}")
    llm_sql = generate_llm_sql(user_query, date)
    
    if llm_sql:
        print(f"[AURA] Yes- LLM-generated SQL:\n{llm_sql}")
        
        result, has_data = execute_sql(llm_sql)
        
        if has_data:
            print(f"[AURA] Yes- LLM SQL validated (found data)")
            return llm_sql, result, True
        else:
            print(f"[AURA] No-  LLM SQL returned 0 rows — falling back to template")
    else:
        print(f"[AURA] Error - LLM unavailable — using template SQL")
    
    template_sql = get_template_sql(user_query, date)
    
    if template_sql:
        print(f"[AURA] Template SQL:\n{template_sql}")
        return template_sql, None, False
    
    print(f"[AURA] Error - No SQL could be generated")
    return None, None, False

def search_journals(query: str, date: str = None) -> str:
    if _vector_db is None:
        print("[AURA] Error - Vector DB not available")
        return ""
    try:
        print("[AURA]  Step 1: Preparing search query...")
        if date:
            date_parts = date.split('-')
            month = "april" if date_parts[1] == "04" else "may"
            day = int(date_parts[2])
            search_query = f"{month} {day} 2016 {query}"
        else:
            search_query = query
        print(f"[AURA]  Step 2: Searching with query: '{search_query}'")
        try:
            results = _vector_db.similarity_search(
                search_query, 
                k=50, 
                filter={"user_id": str(CURRENT_USER_ID)}
            )
            print(f"[AURA]  Step 3: Search completed - found {len(results)} results")
        except Exception as filter_error:
            print(f"[AURA] Error -  Filter failed ({filter_error}), trying without filter...")
            results = _vector_db.similarity_search(search_query, k=50)
            results = [r for r in results if r.metadata.get('user_id') == str(CURRENT_USER_ID)]
            print(f"[AURA] Yes - Found {len(results)} results (manual filter)")
        
        print(f"[AURA] Step 4: Filtering by date (date={date})...")
        if date:
            print(f"[AURA] Step 4a: Before date filter - {len(results)} results")
            results = [r for r in results if r.metadata.get('timestamp', '')[:10] == date]
            print(f"[AURA] Step 4b: After date filter - {len(results)} results")
        
        print(f"[AURA] Step 5: Checking if results are empty...")
        if not results:
            print("[AURA]  No matching journal entries found")
            return ""
        
        print(f"[AURA] Step 6: Formatting {min(3, len(results))} entries...")
        entries = []
        for i, r in enumerate(results[:3]):
            print(f"[AURA] Step 6.{i+1}: Processing entry {i+1}...")
            timestamp = r.metadata.get('timestamp', 'unknown')[:10]
            content = r.page_content[:150]
            entry = f"[{timestamp}] {content}"
            entries.append(entry)
            print(f"[AURA] Step 6.{i+1}: Entry formatted successfully")
        
        print(f"[AURA] Step 7: Joining entries...")
        result = "\n".join(entries)
        print(f"[AURA]  Step 8: Complete! Returning {len(result)} characters")
        return result
        
    except Exception as e:
        print(f"[AURA] Error - Journal search error at some step: {e}")
        import traceback
        traceback.print_exc()
        return ""

def parse_date(user_input: str) -> str:
    match = re.search(r'(april|may)\s+(\d+)', user_input.lower())
    if match:
        month = 4 if match.group(1) == "april" else 5
        day = int(match.group(2))
        return f"2016-{month:02d}-{day:02d}"
    return None


def run_query(user_input: str, chat_history: list[dict] | None = None) -> str:
    try:
        print(f"\n[AURA] Query: {user_input}")
        user_lower = user_input.lower()
        date = parse_date(user_input)
        sql, cached_result, result_cached = generate_sql_with_fallback(user_input, date)
        if not sql:
            print("[AURA] Error - No SQL generated")
            return "I couldn't generate a data query for that. Try asking about a specific date or health metric."

        if result_cached:
            print("[AURA] Yes - Using cached SQL result (no re-execution)")
            numerical_data = cached_result
            has_data = True
        else:
            print("[AURA]  Executing template SQL...")
            numerical_data, has_data = execute_sql(sql)
        
        if not has_data:
            print("[AURA] Error - No data found")
            return f"I couldn't find data for {date if date else 'that query'}. The date might be outside the available data range (April-May 2016)."
        
        print("[AURA] 🔍 Searching journals...")
        try:
            journal_text = search_journals(user_input, date)
            print(f"[AURA] Yes - Journal search complete ({len(journal_text)} chars)")
        except Exception as e:
            print(f"[AURA] Yes - Journal search failed: {e}")
            journal_text = ""
        
        print("[AURA]  Creating Response...")
        result = f"** Data for {date if date else 'requested period'}:**\n\n{numerical_data}"
        
        if journal_text:
            result += f"\n\n** Journal Entries:**\n{journal_text}"
        else:
            result += f"\n\n** Journal Entries:** No journal entries found for this period."
            
        print(f"[AURA]  Response ready ({len(result)} chars)")
        return result

    except Exception as e:
        print(f"[AURA] No- CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return f"Sorry, I encountered an error: {str(e)}"

print(" AURA Hybrid Intelligence Online")

if __name__ == "__main__":
    print("\n" + "="*5)
    print("TESTING AURA QUERY")
    print("="*5)
    try:
        result = run_query("what was my sleep duration on april 17th?")
        print("\n" + "="*5)
        print("RESPONSE:")
        print("="*5)
        print(result)
        print("="*5)
    except KeyboardInterrupt:
        print("\n\n Error - Test interrupted by user")
    except Exception as e:
        print(f"\n\n Error - TEST FAILED: {e}")
        import traceback
        traceback.print_exc()