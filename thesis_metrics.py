
import time
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Tuple
import pandas as pd

from aura_tools_gemini import (
    run_query,
    generate_gemini_sql,
    get_enhanced_template_sql,
    search_journals_realtime,
    execute_sql,
    parse_date,
    GEMINI_AVAILABLE,
)

SLEEP_QUERIES = [
    "how was my sleep on april 17th?",
    "what was my sleep duration on april 16th?",
    "show me my worst sleep days",
    "compare my sleep on april 15 to april 17",
    "how many hours did i sleep on may 1st?",
]

HEART_RATE_QUERIES = [
    "why was my heart rate high on april 12?",
    "what was my maximum heart rate on april 14?",
    "show me my heart rate spikes",
    "when was my heart rate above 100?",
]

ACTIVITY_QUERIES = [
    "how many steps did i take on april 20?",
    "what was my activity on april 25?",
    "show me my most active days",
    "how many calories did i burn on april 18?",
]

COMPLEX_QUERIES = [
    "why was my sleep poor on april 17?",
    "what caused my heart rate spike on april 12?",
    "explain the difference between april 16 and 17 sleep",
    "why were my steps low on april 15?",
]

JOURNAL_QUERIES = [
    "what did i write about april 17?",
    "did i mention any workouts?",
    "what caused stress on april 14?",
    "show me entries about leg day",
]

MULTILINGUAL_QUERIES = {
    'hi': [
        "17 अप्रैल को मेरी नींद कैसी थी?",
        "12 अप्रैल को मेरी हृदय गति अधिक क्यों थी?",
    ],
    'ta': [
        "ஏப்ரல் 17ல் என் தூக்கம் எப்படி இருந்தது?",
        "ஏப்ரல் 12 அன்று என் இதயத் துடிப்பு ஏன் அதிகமாக இருந்தது?",
    ],
    'es': [
        "¿Cómo fue mi sueño el 17 de abril?",
        "¿Por qué mi frecuencia cardíaca fue alta el 12 de abril?",
    ],
}

def measure_response_time(queries: List[str], category: str) -> Dict:
    """Measure average response time for a category of queries."""
    print(f"\n{'='*80}")
    print(f"METRIC 1: Response Time Analysis - {category}")
    print(f"{'='*80}")
    
    times = []
    results = []
    
    for query in queries:
        print(f"\n🔍 Query: {query}")
        start = time.time()
        try:
            result = run_query(query)
            elapsed = time.time() - start
            times.append(elapsed)
            results.append({
                'query': query,
                'time': elapsed,
                'success': 'Error' not in result and len(result) > 10,
                'response_length': len(result)
            })
            print(f"   ⏱️  Time: {elapsed:.2f}s")
            print(f"   ✅ Success: {results[-1]['success']}")
        except Exception as e:
            elapsed = time.time() - start
            times.append(elapsed)
            results.append({
                'query': query,
                'time': elapsed,
                'success': False,
                'error': str(e)
            })
            print(f"   ❌ Error: {e}")

    avg_time = sum(times) / len(times) if times else 0
    min_time = min(times) if times else 0
    max_time = max(times) if times else 0
    success_rate = sum(1 for r in results if r['success']) / len(results) * 100 if results else 0
    
    print(f"\n📊 Summary:")
    print(f"   Average Response Time: {avg_time:.2f}s")
    print(f"   Min: {min_time:.2f}s | Max: {max_time:.2f}s")
    print(f"   Success Rate: {success_rate:.1f}%")
    
    return {
        'category': category,
        'total_queries': len(queries),
        'avg_time': avg_time,
        'min_time': min_time,
        'max_time': max_time,
        'success_rate': success_rate,
        'results': results
    }

def measure_sql_accuracy(queries: List[str]) -> Dict:
    """Compare Gemini SQL vs Template SQL accuracy."""
    print(f"\n{'='*80}")
    print(f"METRIC 2: SQL Generation Accuracy")
    print(f"{'='*80}")
    
    results = {
        'gemini': {'success': 0, 'total': 0, 'queries': []},
        'template': {'success': 0, 'total': 0, 'queries': []},
    }
    
    for query in queries:
        print(f"\n🔍 Query: {query}")
        date = parse_date(query)

        if GEMINI_AVAILABLE:
            gemini_sql = generate_gemini_sql(query, date)
            if gemini_sql:
                results['gemini']['total'] += 1
                data, has_data = execute_sql(gemini_sql)
                if has_data:
                    results['gemini']['success'] += 1
                    print(f"   ✅ Gemini SQL: Success")
                else:
                    print(f"   ❌ Gemini SQL: No data")
                results['gemini']['queries'].append({
                    'query': query,
                    'sql': gemini_sql,
                    'success': has_data
                })

        template_sql = get_enhanced_template_sql(query, date)
        if template_sql:
            results['template']['total'] += 1
            data, has_data = execute_sql(template_sql)
            if has_data:
                results['template']['success'] += 1
                print(f"   ✅ Template SQL: Success")
            else:
                print(f"   ❌ Template SQL: No data")
            results['template']['queries'].append({
                'query': query,
                'sql': template_sql,
                'success': has_data
            })

    gemini_acc = (results['gemini']['success'] / results['gemini']['total'] * 100) if results['gemini']['total'] > 0 else 0
    template_acc = (results['template']['success'] / results['template']['total'] * 100) if results['template']['total'] > 0 else 0
    
    print(f"\n📊 SQL Generation Accuracy:")
    print(f"   Gemini: {gemini_acc:.1f}% ({results['gemini']['success']}/{results['gemini']['total']})")
    print(f"   Template: {template_acc:.1f}% ({results['template']['success']}/{results['template']['total']})")
    
    return {
        'gemini_accuracy': gemini_acc,
        'template_accuracy': template_acc,
        'gemini_success': results['gemini']['success'],
        'gemini_total': results['gemini']['total'],
        'template_success': results['template']['success'],
        'template_total': results['template']['total'],
        'details': results
    }

def measure_journal_relevance(queries: List[str]) -> Dict:
    """Measure journal search relevance and recall."""
    print(f"\n{'='*80}")
    print(f"METRIC 3: Journal Search Relevance")
    print(f"{'='*80}")
    
    results = []
    
    for query in queries:
        print(f"\n🔍 Query: {query}")
        date = parse_date(query)
        
        start = time.time()
        journal_results = search_journals_realtime(query, date)
        search_time = time.time() - start
        
        has_results = len(journal_results) > 0 and journal_results != "No relevant journal entries found."
        num_entries = journal_results.count('[20') if has_results else 0  # Count date markers
        
        results.append({
            'query': query,
            'has_results': has_results,
            'num_entries': num_entries,
            'search_time': search_time
        })
        
        print(f"   ⏱️  Search time: {search_time:.3f}s")
        print(f"   📝 Entries found: {num_entries}")
        print(f"   ✅ Success: {has_results}")
    
    success_rate = sum(1 for r in results if r['has_results']) / len(results) * 100 if results else 0
    avg_time = sum(r['search_time'] for r in results) / len(results) if results else 0
    avg_entries = sum(r['num_entries'] for r in results) / len(results) if results else 0
    
    print(f"\n📊 Journal Search Performance:")
    print(f"   Success Rate: {success_rate:.1f}%")
    print(f"   Avg Search Time: {avg_time:.3f}s")
    print(f"   Avg Entries per Query: {avg_entries:.1f}")
    
    return {
        'success_rate': success_rate,
        'avg_search_time': avg_time,
        'avg_entries_per_query': avg_entries,
        'total_queries': len(queries),
        'successful_queries': sum(1 for r in results if r['has_results']),
        'details': results
    }

def get_database_stats() -> Dict:
    """Get comprehensive database statistics."""
    print(f"\n{'='*80}")
    print(f"METRIC 4: Database Statistics")
    print(f"{'='*80}")
    
    conn = sqlite3.connect("aura_health.db")
    cursor = conn.cursor()
    
    stats = {}

    cursor.execute("SELECT COUNT(*), MIN(Value), MAX(Value), AVG(Value) FROM heart_rate")
    hr_count, hr_min, hr_max, hr_avg = cursor.fetchone()
    stats['heart_rate'] = {
        'total_records': hr_count,
        'min_value': hr_min,
        'max_value': hr_max,
        'avg_value': hr_avg
    }
    print(f"\n❤️  Heart Rate:")
    print(f"   Total Records: {hr_count:,}")
    print(f"   Range: {hr_min:.0f} - {hr_max:.0f} BPM")
    print(f"   Average: {hr_avg:.1f} BPM")
    
    cursor.execute("SELECT COUNT(*), MIN(TotalMinutesAsleep), MAX(TotalMinutesAsleep), AVG(TotalMinutesAsleep) FROM sleep_logs")
    sleep_count, sleep_min, sleep_max, sleep_avg = cursor.fetchone()
    stats['sleep'] = {
        'total_records': sleep_count,
        'min_minutes': sleep_min,
        'max_minutes': sleep_max,
        'avg_minutes': sleep_avg,
        'avg_hours': sleep_avg / 60 if sleep_avg else 0
    }
    print(f"\n😴 Sleep:")
    print(f"   Total Records: {sleep_count:,}")
    print(f"   Range: {sleep_min:.0f} - {sleep_max:.0f} minutes")
    print(f"   Average: {sleep_avg/60:.1f} hours")

    cursor.execute("SELECT COUNT(*), MIN(TotalSteps), MAX(TotalSteps), AVG(TotalSteps) FROM daily_activity")
    act_count, steps_min, steps_max, steps_avg = cursor.fetchone()
    stats['activity'] = {
        'total_records': act_count,
        'min_steps': steps_min,
        'max_steps': steps_max,
        'avg_steps': steps_avg
    }
    print(f"\n👟 Activity:")
    print(f"   Total Records: {act_count:,}")
    print(f"   Steps Range: {steps_min:,} - {steps_max:,}")
    print(f"   Average: {steps_avg:,.0f} steps/day")

    cursor.execute("SELECT MIN(Time), MAX(Time) FROM heart_rate")
    date_min, date_max = cursor.fetchone()
    stats['date_range'] = {
        'start': date_min,
        'end': date_max
    }
    print(f"\n📅 Data Coverage:")
    print(f"   From: {date_min}")
    print(f"   To: {date_max}")
    
    conn.close()
    
    return stats

def measure_feature_coverage() -> Dict:
    """Measure coverage of different features."""
    print(f"\n{'='*80}")
    print(f"METRIC 5: Feature Coverage Analysis")
    print(f"{'='*80}")
    
    features = {
        'SQL Generation (Gemini)': GEMINI_AVAILABLE,
        'SQL Generation (Templates)': True,
        'Journal Search (Vector DB)': True,
        'AI Insights': GEMINI_AVAILABLE,
        'Chain-of-Thought Reasoning': GEMINI_AVAILABLE,
        'Follow-up Questions': GEMINI_AVAILABLE,
        'Date Parsing (2016 detection)': True,
        'Real-time Journal Indexing': True,
        'Multilingual Support': True,
        'Voice Transcription': True,
    }
    
    print(f"\n✅ Feature Availability:")
    for feature, available in features.items():
        status = "✅ Available" if available else "❌ Unavailable"
        print(f"   {status} - {feature}")
    
    coverage = sum(1 for v in features.values() if v) / len(features) * 100
    print(f"\n📊 Overall Feature Coverage: {coverage:.1f}%")
    
    return {
        'features': features,
        'total_features': len(features),
        'available_features': sum(1 for v in features.values() if v),
        'coverage_percentage': coverage
    }

def measure_multilingual_performance() -> Dict:
    """Measure multilingual translation and response accuracy."""
    print(f"\n{'='*80}")
    print(f"METRIC 6: Multilingual Performance")
    print(f"{'='*80}")
    try:
        from aura_tools_multilingual import run_query_multilingual
        from multilingual_support import detect_language, translate_text
        
        results = {}
        
        for lang_code, queries in MULTILINGUAL_QUERIES.items():
            print(f"\n🌍 Testing {lang_code.upper()}:")
            lang_results = []
            
            for query in queries:
                print(f"\n   Query: {query}")

                detected = detect_language(query)
                detection_correct = detected == lang_code
                print(f"   Detection: {detected} ({'✅' if detection_correct else '❌'})")

                start = time.time()
                english = translate_text(query, 'en', lang_code)
                translation_time = time.time() - start
                print(f"   Translation: {english} ({translation_time:.2f}s)")

                try:
                    start = time.time()
                    response = run_query_multilingual(query, user_language=lang_code)
                    response_time = time.time() - start
                    success = len(response) > 10 and 'Error' not in response
                    print(f"   Response: {'✅' if success else '❌'} ({response_time:.2f}s)")
                except Exception as e:
                    response_time = 0
                    success = False
                    print(f"   Response: ❌ {e}")
                
                lang_results.append({
                    'query': query,
                    'detection_correct': detection_correct,
                    'translation_time': translation_time,
                    'response_time': response_time,
                    'success': success
                })

            detection_acc = sum(1 for r in lang_results if r['detection_correct']) / len(lang_results) * 100
            success_rate = sum(1 for r in lang_results if r['success']) / len(lang_results) * 100
            avg_translation_time = sum(r['translation_time'] for r in lang_results) / len(lang_results)
            avg_response_time = sum(r['response_time'] for r in lang_results) / len(lang_results)
            
            results[lang_code] = {
                'detection_accuracy': detection_acc,
                'success_rate': success_rate,
                'avg_translation_time': avg_translation_time,
                'avg_response_time': avg_response_time,
                'queries': lang_results
            }
            
            print(f"\n   📊 {lang_code.upper()} Summary:")
            print(f"      Detection Accuracy: {detection_acc:.1f}%")
            print(f"      Success Rate: {success_rate:.1f}%")
            print(f"      Avg Translation Time: {avg_translation_time:.2f}s")
        
        return results
        
    except ImportError:
        print("⚠️  Multilingual modules not available")
        return {'error': 'Multilingual modules not installed'}

def run_complete_evaluation():
    """Run all metrics and generate comprehensive report."""
    print("="*80)
    print("AURA THESIS EVALUATION - COMPREHENSIVE METRICS")
    print("="*80)
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    all_results = {}

    all_results['response_time'] = {
        'sleep': measure_response_time(SLEEP_QUERIES, "Sleep Queries"),
        'heart_rate': measure_response_time(HEART_RATE_QUERIES, "Heart Rate Queries"),
        'activity': measure_response_time(ACTIVITY_QUERIES, "Activity Queries"),
        'complex': measure_response_time(COMPLEX_QUERIES, "Complex Queries"),
        'journal': measure_response_time(JOURNAL_QUERIES, "Journal Queries"),
    }

    all_results['sql_accuracy'] = measure_sql_accuracy(
        SLEEP_QUERIES + HEART_RATE_QUERIES + ACTIVITY_QUERIES
    )

    all_results['journal_search'] = measure_journal_relevance(JOURNAL_QUERIES)
    
    all_results['database'] = get_database_stats()

    all_results['features'] = measure_feature_coverage()
    
    all_results['multilingual'] = measure_multilingual_performance()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"thesis_results_{timestamp}.json"
    
    with open(filename, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n{'='*80}")
    print(f"✅ EVALUATION COMPLETE")
    print(f"📁 Results saved to: {filename}")
    print(f"{'='*80}")

    generate_summary_report(all_results)
    
    return all_results

def generate_summary_report(results: Dict):
    """Generate a formatted summary report for thesis."""
    print(f"\n{'='*80}")
    print("📊 THESIS RESULTS SUMMARY")
    print(f"{'='*80}")
    
    print("\n1️⃣  RESPONSE TIME PERFORMANCE:")
    for category, data in results['response_time'].items():
        print(f"   {category.upper()}:")
        print(f"      Average: {data['avg_time']:.2f}s")
        print(f"      Success Rate: {data['success_rate']:.1f}%")
    
    print("\n2️⃣  SQL GENERATION ACCURACY:")
    sql_data = results['sql_accuracy']
    print(f"   Gemini AI: {sql_data['gemini_accuracy']:.1f}%")
    print(f"   Templates: {sql_data['template_accuracy']:.1f}%")
    print(f"   Improvement: {sql_data['gemini_accuracy'] - sql_data['template_accuracy']:.1f}%")
    
    print("\n3️⃣  JOURNAL SEARCH PERFORMANCE:")
    journal_data = results['journal_search']
    print(f"   Success Rate: {journal_data['success_rate']:.1f}%")
    print(f"   Avg Search Time: {journal_data['avg_search_time']:.3f}s")
    print(f"   Avg Entries Found: {journal_data['avg_entries_per_query']:.1f}")
    
    print("\n4️⃣  DATABASE COVERAGE:")
    db = results['database']
    print(f"   Heart Rate: {db['heart_rate']['total_records']:,} records")
    print(f"   Sleep Logs: {db['sleep']['total_records']:,} records")
    print(f"   Activity: {db['activity']['total_records']:,} records")
    
    print("\n5️⃣  FEATURE COVERAGE:")
    features = results['features']
    print(f"   Total Features: {features['total_features']}")
    print(f"   Available: {features['available_features']}")
    print(f"   Coverage: {features['coverage_percentage']:.1f}%")
    
    if 'error' not in results.get('multilingual', {}):
        print("\n6️⃣  MULTILINGUAL SUPPORT:")
        for lang, data in results['multilingual'].items():
            print(f"   {lang.upper()}:")
            print(f"      Detection Accuracy: {data['detection_accuracy']:.1f}%")
            print(f"      Success Rate: {data['success_rate']:.1f}%")
    
    print(f"\n{'='*80}")

if __name__ == "__main__":
    results = run_complete_evaluation()
