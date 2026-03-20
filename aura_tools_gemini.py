import sqlite3
import re
import pandas as pd
from datetime import datetime, timedelta
import os

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("[AURA] ⚠️  Google Generative AI not installed - will use template SQL only")
    print("       Install with: pip install google-generativeai")

from sentence_transformers import SentenceTransformer
from langchain_chroma import Chroma

from session_manager_realtime import get_todays_journals, get_recent_journals

CURRENT_USER_ID = 1503960366
SQL_DB_PATH = "aura_health.db"
VECTOR_DB_DIR = "./aura_vector_db_hf"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "SET_YOUR_API")
GEMINI_MODEL = "gemini-2.5-flash"  # Latest and most powerful - Dec 2024

import sys
DEBUG_MODE = not any('streamlit' in arg.lower() for arg in sys.argv)

if GEMINI_AVAILABLE and GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        print(f"[AURA] ✅ Gemini API configured ({GEMINI_MODEL})")
    except Exception as e:
        print(f"[AURA] ⚠️  Gemini configuration failed: {e}")
        GEMINI_AVAILABLE = False

print("⏳ Initializing AURA with Gemini...")

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
    print("⏳ Step 1/3: Loading embedding model...")
    _embeddings = DirectEmbeddings(EMBED_MODEL)
    print("✅ Step 1/3: Embeddings loaded")
    
    print("⏳ Step 2/3: Initializing vector database...")
    sys.stdout.flush()
    
    _vector_db = Chroma(
        persist_directory=VECTOR_DB_DIR, 
        embedding_function=_embeddings
    )
    
    print("✅ Step 2/3: Vector DB object created")
    print("✅ Step 3/3: Vector DB ready")
        
except KeyboardInterrupt:
    print("\n❌ Initialization interrupted by user (Ctrl+C)")
    print("⚠️  AURA will run without vector DB (journal search disabled)")
    _vector_db = None
    _embeddings = None
    
except Exception as e:
    print(f"❌ Vector DB initialization failed: {e}")
    print("⚠️  AURA will run without vector DB (journal search disabled)")
    _vector_db = None
    _embeddings = None

def get_enhanced_template_sql(user_query: str, date: str) -> str:
    """Enhanced template SQL with more query patterns."""
    user_lower = user_query.lower()
    
    print(f"[AURA] 🔧 Template SQL check: query='{user_lower[:50]}...' date='{date}'")
    
    if "calorie" in user_lower:
        print(f"[AURA] ✅ Matched 'calories' template")
        if date:
            sql = f"""SELECT ActivityDate, Calories 
                      FROM daily_activity 
                      WHERE Id = {CURRENT_USER_ID} 
                      AND ActivityDate LIKE '{date}%'"""
            print(f"[AURA] 📝 Generated SQL for calories on {date}")
            return sql
        else:
            return f"""SELECT ActivityDate, Calories 
                      FROM daily_activity 
                      WHERE Id = {CURRENT_USER_ID} 
                      ORDER BY ActivityDate DESC 
                      LIMIT 7"""
    
    if "sleep" in user_lower:
        print(f"[AURA] ✅ Matched 'sleep' template")
        if "worst" in user_lower or "least" in user_lower:
            return f"""SELECT SleepDay, TotalMinutesAsleep 
                      FROM sleep_logs 
                      WHERE Id = {CURRENT_USER_ID} 
                      ORDER BY TotalMinutesAsleep ASC 
                      LIMIT 5"""
        
        elif "best" in user_lower or "most" in user_lower:
            return f"""SELECT SleepDay, TotalMinutesAsleep 
                      FROM sleep_logs 
                      WHERE Id = {CURRENT_USER_ID} 
                      ORDER BY TotalMinutesAsleep DESC 
                      LIMIT 5"""
        
        elif date:
            sql = f"""SELECT SleepDay, TotalMinutesAsleep, TotalTimeInBed 
                      FROM sleep_logs 
                      WHERE Id = {CURRENT_USER_ID} 
                      AND SleepDay LIKE '{date}%'"""
            print(f"[AURA] 📝 Generated SQL for sleep on {date}")
            return sql
        else:
            sql = f"""SELECT SleepDay, TotalMinutesAsleep, TotalTimeInBed 
                      FROM sleep_logs 
                      WHERE Id = {CURRENT_USER_ID} 
                      ORDER BY SleepDay DESC 
                      LIMIT 7"""
            print(f"[AURA] 📝 Generated SQL for recent sleep")
            return sql
    
    if "heart" in user_lower or "hr" in user_lower:
        print(f"[AURA] ✅ Matched 'heart rate' template")
        if "highest" in user_lower or "max" in user_lower:
            return f"""SELECT Time, Value 
                      FROM heart_rate 
                      WHERE Id = {CURRENT_USER_ID} 
                      ORDER BY Value DESC 
                      LIMIT 10"""
        
        elif date:
            return f"""SELECT Time, Value 
                      FROM heart_rate 
                      WHERE Id = {CURRENT_USER_ID} 
                      AND Time LIKE '{date}%' 
                      ORDER BY Value DESC 
                      LIMIT 10"""

    if "step" in user_lower:
        print(f"[AURA] ✅ Matched 'steps' template")
        if "most" in user_lower or "highest" in user_lower:
            return f"""SELECT ActivityDate, TotalSteps 
                      FROM daily_activity 
                      WHERE Id = {CURRENT_USER_ID} 
                      ORDER BY TotalSteps DESC 
                      LIMIT 5"""
        
        elif "least" in user_lower or "lowest" in user_lower or "fewest" in user_lower:
            return f"""SELECT ActivityDate, TotalSteps 
                      FROM daily_activity 
                      WHERE Id = {CURRENT_USER_ID} 
                      ORDER BY TotalSteps ASC 
                      LIMIT 5"""
        
        elif date:
            return f"""SELECT ActivityDate, TotalSteps, Calories 
                      FROM daily_activity 
                      WHERE Id = {CURRENT_USER_ID} 
                      AND ActivityDate LIKE '{date}%'"""
    
    print(f"[AURA] ❌ No template matched")
    return None

def execute_sql(sql: str) -> tuple[str, bool]:
    """Execute SQL and return (results, has_data)."""
    print(f"\n[AURA] 🔍 Executing SQL:")
    print(f"{'─' * 80}")
    print(sql)
    print(f"{'─' * 80}\n")
    
    conn = sqlite3.connect(SQL_DB_PATH)
    try:
        df = pd.read_sql_query(sql, conn)
        conn.close()
        has_data = not df.empty
        if not has_data:
            print(f"[AURA] ❌ Query returned 0 rows")
            return "No data found.", False
        
        print(f"[AURA] ✅ Query returned {len(df)} rows")
        print(f"[AURA] 📊 Data preview:")
        print(f"{'─' * 80}")
        print(df.to_string(index=False))
        print(f"{'─' * 80}\n")
        result = df.to_string(index=False) if len(df) <= 20 else df.head(20).to_string(index=False) + f"\n... ({len(df)-20} more rows)"
        return result, True

    except Exception as e:
        conn.close()
        print(f"[AURA] SQL error: {e}")
        return f"Error: {e}", False

def generate_gemini_sql(user_query: str, date: str = None) -> str:
    if not GEMINI_AVAILABLE:
        print(f"[AURA] ⚠️  Gemini not installed - using template SQL")
        return None  # Will use template SQL
    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        schema = f"""You are a SQL expert. Generate ONLY a SQL SELECT query for this health database.

Tables:
- heart_rate (Id, Time, Value)
- sleep_logs (Id, SleepDay, TotalMinutesAsleep, TotalTimeInBed)
- daily_activity (Id, ActivityDate, TotalSteps, Calories)

Rules:
- User ID is {CURRENT_USER_ID} - ALWAYS include WHERE Id = {CURRENT_USER_ID}
- Dates are in format YYYY-MM-DD HH:MM:SS
- Use LIKE 'YYYY-MM-DD%' for date matching
- Return ONLY the SQL query, no markdown, no explanations
- Only SELECT statements allowed

User Query: {user_query}

SQL:"""
        
        response = model.generate_content(schema)
        sql = response.text.strip()
        sql = sql.replace('```sql', '').replace('```', '').strip()
        if sql.upper().startswith('SELECT') and 'DROP' not in sql.upper():
            print(f"[AURA] ✅ Gemini-generated SQL")
            return sql
        print(f"[AURA] ⚠️  Invalid SQL from Gemini - using template SQL")
        return None
    except Exception as e:
        error_msg = str(e)
        
        if "quota" in error_msg.lower() or "429" in error_msg:
            print(f"[AURA] ⚠️  Gemini quota exceeded - using template SQL")
            print(f"[AURA] 💡 Free tier: 15 requests/min, 1500/day. Try again later or wait a minute.")
        elif "api" in error_msg.lower() or "key" in error_msg.lower():
            print(f"[AURA] ⚠️  Gemini API key issue - using template SQL")
            print(f"[AURA] 💡 Get free key at: https://aistudio.google.com/apikey")
        elif "connection" in error_msg.lower() or "network" in error_msg.lower():
            print(f"[AURA] ⚠️  Network error - using template SQL")
        else:
            print(f"[AURA] ⚠️  Gemini error: {error_msg[:100]} - using template SQL")
        
        return None

def search_journals_realtime(query: str, date: str = None) -> str:
    print(f"[AURA] 📓 Searching journals (real-time mode)...")
    if date:
        print(f"[AURA] 📓 Filtering for date: {date}")
    
    import string
    query_clean = query.lower().translate(str.maketrans('', '', string.punctuation))
    search_terms = [word for word in query_clean.split() if len(word) > 3 
                    and word not in ('what', 'when', 'show', 'tell', 'about', 'journal', 'entry', 'that', 'this', 'with', 'from')]
    
    print(f"[AURA] 📓 Search terms: {search_terms}")
    
    all_results = []
    print(f"[AURA] 📓 Step 1: Searching recent session journals...")
    try:
        recent_journals = get_recent_journals(hours=24)
        if recent_journals:
            print(f"[AURA] 📓 Found {len(recent_journals)} recent journal(s)")

            if date:
                matched_recent = [j for j in recent_journals if j['timestamp'][:10] == date]
                print(f"[AURA] 📓 Date filter: {len(matched_recent)} entries match {date}")
            else:
                matched_recent = []
                
                for journal in recent_journals:
                    entry_text = journal['entry'].replace('🎤 [Voice Entry]', '').strip()
                    entry_clean = entry_text.lower().translate(str.maketrans('', '', string.punctuation))
                    
                    if search_terms:
                        matches = [term for term in search_terms if term in entry_clean]
                        if matches:
                            score = len(matches) / len(search_terms)
                            if score >= 0.3:  # At least 30% of terms must match
                                matched_recent.append((journal, score, matches))
                    else:
                        matched_recent.append((journal, 1.0, []))
                
                matched_recent = sorted(matched_recent, key=lambda x: x[1], reverse=True)
                print(f"[AURA] 📓 Keyword match: {len(matched_recent)} relevant entries")
                matched_recent = [j[0] for j in matched_recent]  # Extract journals only
            
            if matched_recent:
                for j in matched_recent[:5]:  # Top 5
                    timestamp = j['timestamp'][:19]
                    content = j['entry'][:150]
                    all_results.append((f"[{timestamp}] ⚡NEW: {content}", 1.0))  # High relevance
    except Exception as e:
        print(f"[AURA] ⚠️  Recent journal search failed: {e}")
        import traceback
        traceback.print_exc()
    
    if _vector_db is not None:
        print(f"[AURA] 📓 Step 2: Searching vector database...")
        try:
            if date:
                date_parts = date.split('-')
                year = date_parts[0]
                month_num = int(date_parts[1])
                day = int(date_parts[2])
                
                month_names = ['', 'january', 'february', 'march', 'april', 'may', 'june',
                              'july', 'august', 'september', 'october', 'november', 'december']
                month_name = month_names[month_num] if month_num <= 12 else ''
                if year == '2016':
                    if month_num == 4:
                        month_name = 'april'
                    elif month_num == 5:
                        month_name = 'may'
                    search_query = f"{month_name} {day} 2016 {query}"
                else:
                    search_query = f"{month_name} {day} {year} {query}"
            else:
                search_query = query
            
            print(f"[AURA] 📓 Vector search query: '{search_query[:50]}...'")
            
            try:
                results = _vector_db.similarity_search(
                    search_query, 
                    k=20,  # Get more results to filter
                    filter={"user_id": str(CURRENT_USER_ID)}
                )
                print(f"[AURA] 📓 Found {len(results)} vector DB results")
            except:
                results = _vector_db.similarity_search(search_query, k=20)
                results = [r for r in results if r.metadata.get('user_id') == str(CURRENT_USER_ID)]
                print(f"[AURA] 📓 Found {len(results)} results (manual filter)")

            if date:
                results = [r for r in results if r.metadata.get('timestamp', '')[:10] == date]
                print(f"[AURA] 📓 Filtered to {len(results)} for date {date}")
            if search_terms and not date:  # Only filter if not date-specific
                relevant_results = []
                for r in results:
                    content_clean = r.page_content.lower().translate(str.maketrans('', '', string.punctuation))
                    # Check if entry contains at least one search term
                    matches = [term for term in search_terms if term in content_clean]
                    if matches:
                        score = len(matches) / len(search_terms)
                        relevant_results.append((r, score))
                relevant_results = sorted(relevant_results, key=lambda x: x[1], reverse=True)
                results = [r[0] for r in relevant_results[:5]]  # Top 5 most relevant
                
                print(f"[AURA] 📓 Filtered to {len(results)} relevant entries (keyword match)")
            
            for r in results:
                timestamp = r.metadata.get('timestamp', '')[:19]
                content = r.page_content[:150]
                all_results.append((f"[{timestamp}] {content}", 0.8))  # Good relevance
                
        except Exception as e:
            print(f"[AURA] ⚠️  Vector DB search failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"[AURA] ⚠️  Vector DB not available")

    if all_results:
        # Remove duplicates (same timestamp)
        seen_timestamps = set()
        unique_results = []

        all_results = sorted(all_results, key=lambda x: x[1], reverse=True)
        
        for result, score in all_results:
            timestamp = result[1:20]  # Extract timestamp
            if timestamp not in seen_timestamps:
                seen_timestamps.add(timestamp)
                unique_results.append(result)
        
        print(f"[AURA] ✅ Total unique results: {len(unique_results)}")
        max_results = 3 if search_terms else 10  # Fewer results when specific search
        return "\n".join(unique_results[:max_results])
    else:
        print(f"[AURA] ❌ No journal entries found")
        return ""


def parse_date(user_input: str) -> str:
    user_lower = user_input.lower()

    if "today" in user_lower:
        return datetime.now().strftime("%Y-%m-%d")
    if "yesterday" in user_lower:
        yesterday = datetime.now() - timedelta(days=1)
        return yesterday.strftime("%Y-%m-%d")
    
    month_match = re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d+)', user_lower)
    if month_match:
        month_name = month_match.group(1)
        day = int(month_match.group(2))
        
        month_map = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12
        }
        
        month_num = month_map.get(month_name)
        if month_num:
            if month_name in ['april', 'may']:
                year = 2016
                print(f"[AURA] 📅 Detected historical data month: {month_name} → using 2016")
            else:
                year = datetime.now().year
                print(f"[AURA] 📅 Current year month: {month_name} → using {year}")
            
            return f"{year:04d}-{month_num:02d}-{day:02d}"

    date_match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', user_input)
    if date_match:
        return f"{date_match.group(1)}-{int(date_match.group(2)):02d}-{int(date_match.group(3)):02d}"
    
    return None

def generate_reasoning_plan(user_query: str, date: str = None) -> dict:
    if not GEMINI_AVAILABLE:
        return None
    
    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        
        planning_prompt = f"""You are a health data analyst planning how to answer a user's question.

User Question: {user_query}
{f"Date Mentioned: {date}" if date else "No specific date mentioned"}

Available Data Sources:
1. Sleep data (SleepDay, TotalMinutesAsleep, TotalTimeInBed)
2. Heart rate data (Time, Value)
3. Activity data (ActivityDate, TotalSteps, Calories)
4. Journal entries (timestamp, text content)

Analyze this query and create a reasoning plan. Consider:
- What data is needed to answer this fully?
- What dates should we check? (If asking about "why" on date X, check X-1 and X for context)
- What comparisons would be helpful?
- What patterns should we look for?

Respond with a JSON object:
{{
    "query_type": "sleep_analysis|heart_rate|activity|why_question|comparison",
    "primary_date": "YYYY-MM-DD or null",
    "additional_dates": ["YYYY-MM-DD", ...],
    "data_needed": ["sleep", "heart_rate", "activity", "journals"],
    "reasoning_steps": ["step 1", "step 2", ...],
    "comparisons": ["compare X to Y"]
}}

Query: {user_query}
Plan:"""
        response = model.generate_content(planning_prompt)
        plan_text = response.text.strip()
        plan_text = plan_text.replace('```json', '').replace('```', '').strip()
        
        import json
        plan = json.loads(plan_text)
        
        print(f"[AURA] 🧠 Reasoning plan created:")
        print(f"[AURA]   Query type: {plan.get('query_type')}")
        print(f"[AURA]   Data needed: {', '.join(plan.get('data_needed', []))}")
        
        return plan
        
    except Exception as e:
        print(f"[AURA] ⚠️  Reasoning plan failed: {str(e)[:100]}")
        return None


def execute_reasoning_plan(plan: dict, user_query: str) -> dict:
    if not plan:
        return {}
    
    data_package = {
        'sleep_data': [],
        'heart_rate_data': [],
        'activity_data': [],
        'journal_data': []
    }
    
    dates_to_check = []
    if plan.get('primary_date'):
        primary_date = plan['primary_date']
        dates_to_check.append(primary_date)

        try:
            from datetime import datetime, timedelta
            date_obj = datetime.strptime(primary_date, "%Y-%m-%d")
            day_before = (date_obj - timedelta(days=1)).strftime("%Y-%m-%d")
            dates_to_check.append(day_before)
            print(f"[AURA] 📊 Focused: {primary_date} + {day_before} for comparison")
        except:
            pass
    
    print(f"[AURA] 📊 Gathering data for: {', '.join(dates_to_check)}")

    if 'sleep' in plan.get('data_needed', []):
        for date in dates_to_check:
            sql = f"""SELECT SleepDay, TotalMinutesAsleep, TotalTimeInBed 
                     FROM sleep_logs 
                     WHERE Id = {CURRENT_USER_ID} 
                     AND SleepDay LIKE '{date}%'"""
            result, has_data = execute_sql(sql)
            if has_data:
                data_package['sleep_data'].append({
                    'date': date,
                    'data': result
                })

    if 'heart_rate' in plan.get('data_needed', []):
        for date in dates_to_check:
            sql = f"""SELECT Time, Value 
                     FROM heart_rate 
                     WHERE Id = {CURRENT_USER_ID} 
                     AND Time LIKE '{date}%' 
                     ORDER BY Value DESC 
                     LIMIT 5"""
            result, has_data = execute_sql(sql)
            if has_data:
                data_package['heart_rate_data'].append({
                    'date': date,
                    'data': result
                })

    if 'activity' in plan.get('data_needed', []):
        for date in dates_to_check:
            sql = f"""SELECT ActivityDate, TotalSteps, Calories 
                     FROM daily_activity 
                     WHERE Id = {CURRENT_USER_ID} 
                     AND ActivityDate LIKE '{date}%'"""
            result, has_data = execute_sql(sql)
            if has_data:
                data_package['activity_data'].append({
                    'date': date,
                    'data': result
                })

    if 'journals' in plan.get('data_needed', []):
        for date in dates_to_check:
            journals = search_journals_realtime(user_query, date)
            if journals:
                data_package['journal_data'].append({
                    'date': date,
                    'data': journals
                })
    
    print(f"[AURA] ✅ Data package ready")
    return data_package


def generate_chain_of_thought_insights(user_query: str, plan: dict, data_package: dict) -> str:
    if not GEMINI_AVAILABLE or not data_package:
        return None
    
    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        
        context_parts = []
        
        if data_package.get('sleep_data'):
            context_parts.append("**Sleep Data:**")
            for item in data_package['sleep_data']:
                context_parts.append(f"Date {item['date']}:\n{item['data']}")
        
        if data_package.get('heart_rate_data'):
            context_parts.append("\n**Heart Rate Data:**")
            for item in data_package['heart_rate_data']:
                context_parts.append(f"Date {item['date']}:\n{item['data']}")
        
        if data_package.get('activity_data'):
            context_parts.append("\n**Activity Data:**")
            for item in data_package['activity_data']:
                context_parts.append(f"Date {item['date']}:\n{item['data']}")
        
        if data_package.get('journal_data'):
            context_parts.append("\n**Journal Entries:**")
            for item in data_package['journal_data']:
                context_parts.append(f"Date {item['date']}:\n{item['data']}")
        
        combined_context = "\n".join(context_parts)

        cot_prompt = f"""You are a health data analyst. Use chain-of-thought reasoning to analyze this comprehensively.

User Question: {user_query}

Available Data:
{combined_context}

Reasoning Plan:
{plan.get('reasoning_steps', [])}

Use step-by-step reasoning:

**Step 1: Understand the Question**
- What is the user really asking?
- What timeframe matters?

**Step 2: Analyze the Data**
- What does the sleep data show?
- What do the journals reveal?
- What patterns or correlations exist?

**Step 3: Make Connections**
- How does data from different days relate?
- What could explain the observations?
- Are there clear cause-effect relationships?

**Step 4: Synthesize Insights**
- What's the most likely explanation?
- What actionable advice follows from this?

Provide your analysis in this format:

🧠 **Reasoning:**
[Your step-by-step thinking, 2-3 sentences]

💡 **Insight:**
[Final answer with specific recommendations, 2-3 sentences]

Be specific, use actual numbers from the data, and make clear connections between events."""
        
        print(f"[AURA] 🧠 Generating chain-of-thought analysis...")
        
        response = model.generate_content(cot_prompt)
        analysis = response.text.strip()
        
        if analysis and len(analysis) > 20:
            print(f"[AURA] ✅ Chain-of-thought analysis complete ({len(analysis)} chars)")
            return analysis
        
        return None
        
    except Exception as e:
        print(f"[AURA] 💭 Chain-of-thought analysis unavailable: {str(e)[:100]}")
        return None
    """
    Generate AI-powered health insights from data.
    Combines SQL results + journals for comprehensive analysis.
    """
    if not GEMINI_AVAILABLE:
        print(f"[AURA] 💭 AI insights skipped (Gemini not installed)")
        return None  # No analysis without AI
    
    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        
        # Build context for analysis
        context_parts = []
        
        if numerical_data and numerical_data != "No data found.":
            context_parts.append(f"**Health Data:**\n{numerical_data}")
        
        if journal_context:
            context_parts.append(f"**Journal Entries:**\n{journal_context}")
        
        if not context_parts:
            print(f"[AURA] 💭 AI insights skipped (no data to analyze)")
            return None  # No data to analyze
        
        combined_data = "\n\n".join(context_parts)
        
        # Create analysis prompt
        analysis_prompt = f"""You are a health data analyst. Analyze this health information and provide insights.

User Question: {user_query}
{f"Date Focus: {date}" if date else ""}

Data Available:
{combined_data}

Provide a brief analysis (2-3 sentences) that:
1. Identifies key patterns or notable findings
2. Connects health metrics with journal context (if available)
3. Offers ONE actionable insight or consideration

Be conversational, supportive, and specific. Focus on what's most relevant to the user's question.
Avoid medical advice. If data seems concerning, suggest consulting a healthcare provider.

Analysis:"""
        
        print(f"[AURA] 🤖 Generating AI insights...")
        
        response = model.generate_content(analysis_prompt)
        analysis = response.text.strip()
        
        if analysis and len(analysis) > 10:
            print(f"[AURA] ✅ AI insights generated ({len(analysis)} chars)")
            return analysis
        
        print(f"[AURA] 💭 AI insights empty or too short")
        return None
        
    except Exception as e:
        error_msg = str(e)
        
        # Detailed error logging
        if "quota" in error_msg.lower() or "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            print(f"[AURA] 💭 AI insights unavailable (quota exceeded)")
            print(f"[AURA] 💡 Quota limits: 15 requests/min, 1500/day")
            print(f"[AURA] 💡 Solution: Wait 1 minute or use tomorrow")
        elif "api_key" in error_msg.lower() or "API_KEY_INVALID" in error_msg or "403" in error_msg:
            print(f"[AURA] 💭 AI insights unavailable (invalid API key)")
            print(f"[AURA] 💡 Get free key at: https://aistudio.google.com/apikey")
            print(f"[AURA] 💡 Set with: export GEMINI_API_KEY='your-key'")
        elif "network" in error_msg.lower() or "connection" in error_msg.lower() or "timeout" in error_msg.lower():
            print(f"[AURA] 💭 AI insights unavailable (network error)")
            print(f"[AURA] 💡 Check internet connection and try again")
        elif "blocked" in error_msg.lower() or "safety" in error_msg.lower():
            print(f"[AURA] 💭 AI insights unavailable (safety filter triggered)")
            print(f"[AURA] 💡 Try rephrasing your query")
        else:
            print(f"[AURA] 💭 AI insights unavailable (API error)")
            print(f"[AURA] 🔍 Error details: {error_msg[:200]}")
        
        return None


def generate_health_insights(user_query: str, numerical_data: str, journal_context: str, date: str = None) -> str:
    if not GEMINI_AVAILABLE:
        print(f"[AURA] 💭 AI insights skipped (Gemini not installed)")
        return None
    
    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        context_parts = []
        
        if numerical_data and numerical_data != "No data found.":
            context_parts.append(f"**Health Data:**\n{numerical_data}")
        
        if journal_context:
            context_parts.append(f"**Journal Entries:**\n{journal_context}")
        
        if not context_parts:
            print(f"[AURA] 💭 AI insights skipped (no data to analyze)")
            return None
        
        combined_data = "\n\n".join(context_parts)

        analysis_prompt = f"""You are a health data analyst. Provide a brief, supportive insight.

User Question: {user_query}
{f"Date: {date}" if date else ""}

Data:
{combined_data}

Provide a brief analysis (2-3 sentences) that:
1. Interprets the data in context
2. Makes connections between metrics and journal entries (if available)
3. Offers ONE specific, actionable recommendation

Be conversational and supportive. Avoid medical advice.

Analysis:"""
        
        print(f"[AURA] 🤖 Generating standard insights...")
        
        response = model.generate_content(analysis_prompt)
        analysis = response.text.strip()
        
        if analysis and len(analysis) > 10:
            print(f"[AURA] ✅ Standard insights generated ({len(analysis)} chars)")
            return analysis
        
        print(f"[AURA] 💭 Insights too short or empty")
        return None
        
    except Exception as e:
        error_msg = str(e)
        
        if "quota" in error_msg.lower() or "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
            print(f"[AURA] 💭 AI insights unavailable (quota exceeded)")
        elif "api_key" in error_msg.lower() or "API_KEY_INVALID" in error_msg or "403" in error_msg:
            print(f"[AURA] 💭 AI insights unavailable (invalid API key)")
        else:
            print(f"[AURA] 💭 AI insights unavailable: {error_msg[:100]}")
        
        return None

def run_query(user_input: str, chat_history: list[dict] | None = None) -> str:
    """Main entry point with chain-of-thought reasoning for complex queries."""
    try:
        print(f"\n[AURA] Query: {user_input}")
        
        user_lower = user_input.lower()
        date = parse_date(user_input)
        
        # Detect follow-up questions that need advice, not data
        is_followup_advice = any(phrase in user_lower for phrase in [
            'how to prevent', 'how can i prevent', 'how do i prevent',
            'how to avoid', 'how can i avoid', 'how do i avoid',
            'what should i do', 'what can i do',
            'how to fix', 'how to improve', 'tips for', 'advice for'
        ]) and len(user_input.split()) < 10  # Short follow-up questions
        
        # If it's a follow-up advice question, use chat history for context
        if is_followup_advice and chat_history and GEMINI_AVAILABLE:
            print(f"[AURA] 💬 Follow-up advice question detected")
            
            try:
                model = genai.GenerativeModel(GEMINI_MODEL)
                
                # Build context from recent chat (include MORE of the assistant's response)
                recent_context = []
                last_user_query = None
                
                for msg in chat_history[-4:]:  # Last 2 exchanges
                    if msg['role'] == 'user':
                        recent_context.append(f"User: {msg['content']}")
                        last_user_query = msg['content']  # Track the last question
                    elif msg['role'] == 'assistant':
                        # Include FULL response, not just 200 chars
                        recent_context.append(f"Assistant: {msg['content']}")
                
                # Try to extract date from last query for re-querying data
                last_date = None
                if last_user_query:
                    last_date = parse_date(last_user_query)
                
                # If we can extract a date, re-query the actual data for better context
                additional_context = ""
                if last_date and "sleep" in (last_user_query or "").lower():
                    print(f"[AURA] 📊 Re-querying sleep data for {last_date} to improve advice")
                    sql = f"""SELECT SleepDay, TotalMinutesAsleep, TotalTimeInBed 
                             FROM sleep_logs 
                             WHERE Id = {CURRENT_USER_ID} 
                             AND SleepDay LIKE '{last_date}%'"""
                    sleep_data, has_data = execute_sql(sql)
                    if has_data:
                        additional_context = f"\n\nActual Sleep Data:\n{sleep_data}"
                
                context_text = "\n".join(recent_context) + additional_context
                
                advice_prompt = f"""Based on this conversation:

{context_text}

User now asks: {user_input}

Provide specific, actionable advice (2-3 sentences) to address their follow-up question. 
Use the ACTUAL DATA (sleep minutes, time in bed) if available to give precise recommendations.
Reference specific numbers and situations from the conversation.
Give practical, implementable steps.

Advice:"""
                
                print(f"[AURA] 🤖 Generating contextual advice...")
                response = model.generate_content(advice_prompt)
                advice = response.text.strip()
                
                if advice:
                    print(f"[AURA] ✅ Contextual advice ready")
                    return f"**💡 Advice:**\n\n{advice}"
                
            except Exception as e:
                print(f"[AURA] ⚠️  Advice generation failed: {str(e)[:100]}")
        
        # Detect if this needs chain-of-thought reasoning
        needs_cot = any(word in user_lower for word in [
            'why', 'what caused', 'explain', 'reason', 'because',
            'compare', 'difference', 'better', 'worse', 'changed'
        ])
        
        # CHAIN-OF-THOUGHT PATH (for complex "why" questions)
        if needs_cot and GEMINI_AVAILABLE:
            print(f"[AURA] 🧠 Complex query detected - using chain-of-thought reasoning")
            
            # Step 1: Generate reasoning plan
            plan = generate_reasoning_plan(user_input, date)
            
            if plan:
                # Step 2: Execute plan and gather data
                data_package = execute_reasoning_plan(plan, user_input)
                
                # Step 3: Generate chain-of-thought insights
                cot_analysis = generate_chain_of_thought_insights(user_input, plan, data_package)
                
                if cot_analysis:
                    # Format data for display
                    result_parts = []
                    
                    if data_package.get('sleep_data'):
                        for item in data_package['sleep_data']:
                            result_parts.append(f"**📊 Sleep Data ({item['date']}):**\n{item['data']}")
                    
                    if data_package.get('activity_data'):
                        for item in data_package['activity_data']:
                            result_parts.append(f"**📊 Activity Data ({item['date']}):**\n{item['data']}")
                    
                    if data_package.get('journal_data'):
                        for item in data_package['journal_data']:
                            result_parts.append(f"**📓 Journal Entries ({item['date']}):**\n{item['data']}")
                    
                    # Add chain-of-thought analysis
                    result_parts.append(f"\n{cot_analysis}")
                    
                    print(f"[AURA] ✅ Chain-of-thought response ready")
                    return "\n\n".join(result_parts)
        
        # STANDARD PATH (simple queries)
        print(f"[AURA] 📊 Standard query processing")
        
        # Check if this is a journal-only query
        is_journal_query = any(word in user_lower for word in [
            'journal', 'wrote', 'said', 'mentioned', 'feeling',
            'leg day', 'workout', 'meeting', 'stress', 'sunrise'
        ])
        
        # 1. Try SQL for health data
        sql = None
        numerical_data = None
        
        if not is_journal_query:
            print(f"[AURA] 🔍 Attempting SQL generation...")
            # Try Gemini first, fall back to templates
            sql = generate_gemini_sql(user_input, date) or get_enhanced_template_sql(user_input, date)
            
            if sql:
                print(f"[AURA] ✅ SQL generated successfully")
            else:
                print(f"[AURA] ⚠️  No SQL generated (Gemini and templates both failed)")
        else:
            print(f"[AURA] 📓 Journal-only query detected, skipping SQL")
        
        if sql:
            print(f"[AURA] 🔍 Executing SQL query...")
            numerical_data, has_data = execute_sql(sql)
            if not has_data:
                print(f"[AURA] ❌ SQL returned no data")
                numerical_data = None
            else:
                print(f"[AURA] ✅ SQL returned data successfully")
        
        # 2. Search journals (REAL-TIME)
        journal_text = search_journals_realtime(user_input, date)
        
        # 3. Generate AI insights
        ai_insights = None
        if numerical_data or journal_text:
            ai_insights = generate_health_insights(
                user_query=user_input,
                numerical_data=numerical_data or "",
                journal_context=journal_text or "",
                date=date
            )
        
        # 4. Format response
        if numerical_data:
            result = f"**📊 Health Data:**\n\n{numerical_data}"
            
            if journal_text:
                result += f"\n\n**📓 Journal Entries:**\n{journal_text}"
            
            if ai_insights:
                result += f"\n\n**💡 AI Insights:**\n{ai_insights}"
            
        elif journal_text:
            result = f"**📓 Journal Entries:**\n\n{journal_text}"
            
            if ai_insights:
                result += f"\n\n**💡 AI Insights:**\n{ai_insights}"
        else:
            result = "I couldn't find any data for that query. Try being more specific or check the date range."
        
        print(f"[AURA] ✅ Response ready")
        return result

    except Exception as e:
        print(f"[AURA] ❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return f"Sorry, I encountered an error: {str(e)}"

llm_status = "Gemini + Templates" if GEMINI_AVAILABLE else "Templates Only"
print(f"✅ AURA Gemini Intelligence Online ({llm_status})")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("TESTING GEMINI-POWERED AURA")
    print("="*80)
    
    # Test query
    print("\n📝 Test: Searching for sunrise")
    result = run_query("when did I see sunrise?")
    print(result)
    
    print("\n" + "="*80)
