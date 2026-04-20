import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

current_file = Path(__file__).resolve()
PROJECT_ROOT = current_file
while not (PROJECT_ROOT / 'backend').is_dir() and PROJECT_ROOT != PROJECT_ROOT.parent:
    PROJECT_ROOT = PROJECT_ROOT.parent
if not (PROJECT_ROOT / 'backend').is_dir():
    PROJECT_ROOT = current_file.parents[4]
BACKEND_ROOT = PROJECT_ROOT / 'backend'
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from openai import AzureOpenAI
from agents.optimization.datalayer.db_service import PostgresClient

load_dotenv(dotenv_path=BACKEND_ROOT / '.env')

# VERIFIED CONFIGURATION
DATABASE_URL = os.getenv("DATABASE_URL")

db_client = PostgresClient(DATABASE_URL)
client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-12-01-preview"
)

def handle_query_optimization(user_query: str) -> str:
    print(f"[DEBUG] Handling query optimization for: {user_query}")
    print(f"[DEBUG] Handling query optimization for: {user_query}")
    # 1. Resolve Columns & Schema
    real_columns = db_client.get_query_metadata(user_query)
    print(f"[DEBUG] Real columns: {real_columns}")
    
    # 2. Extract Live Telemetry (Plan, Cost, I/O, Indexes)
    full_plan = db_client.investigate(user_query)
    print(f"[DEBUG] Full plan: {full_plan}")
    current_effort = full_plan.get('total_cost', 0)

    prompt = f"""
    ROLE: Senior PostgreSQL SRE & Performance Architect
    USER SQL: {user_query}
    METADATA: {real_columns}
    LIVE TELEMETRY: {json.dumps(full_plan)}

    GOVERNANCE RULES:
    1. If '*' is used, ALWAYS expand it using the provided METADATA.
    2. Check 'existing_indexes'. If the required index is already present, health is 🟢.
    3. If 'is_scan' is True AND no relevant index exists, health is 🟡. Suggest a fix.
    4. If 'reads' > 0, mention that the query is hitting Physical Disk instead of RAM Cache.
    5. If 'is_scan' is True but indexes EXIST, explain it is a 'Small Table Seq Scan' but architecture is 🟢.

    RETURN JSON ONLY:
    {{
        "execution_verified": true,
        "health_indicator": "🟢 | 🟡 | 🔴",
        "status": "Verified | Optimization Recommended | Critical Error",
        "performance_comparison": {{
            "workload_effort_original": "{current_effort}",
            "workload_effort_projected": "Calculate based on fix",
            "efficiency_gain": "Percentage"
        }},
        "optimized_sql": "Fully rewritten SQL",
        "suggested_fix": "CREATE INDEX... or 'Infrastructure Verified'",
        "audit_note": "Explain the I/O path (RAM vs Disk) and Scan Type."
    }}
    """

    try:
        response = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
            messages=[{"role": "system", "content": "You are a DB Auditor. Return only raw JSON."},
                      {"role": "user", "content": prompt}],
            temperature=0
        )
        content = response.choices[0].message.content.strip()
        
        # Log to database
        try:
            data = json.loads(content)
            new_query = data.get('optimized_sql', user_query)
            # Escape single quotes for SQL
            old_query_escaped = user_query.replace("'", "''")
            new_query_escaped = new_query.replace("'", "''")
            optimization_json_escaped = content.replace("'", "''")
            insert_sql = f"INSERT INTO query_audit_log (old_query, new_query, optimization_json) VALUES ('{old_query_escaped}', '{new_query_escaped}', '{optimization_json_escaped}')"
            db_client.execute_query(insert_sql)
        except json.JSONDecodeError:
            pass  # Skip logging if not valid JSON
        
        return content
    except Exception as e:
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    print("🚀 WATCHMAN AGENT ONLINE: Multi-Scenario PostgreSQL Intelligence")
    while True:
        user_input = input("\n🔍 Query: ")
        if user_input.lower() in ['exit', 'quit']: break
        if not user_input.strip(): continue
        
        print("\n--- AUDIT RESULTS ---")
        print(handle_query_optimization(user_input))