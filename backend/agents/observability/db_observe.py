import os
import psycopg2
import logging
import re
from openai import AzureOpenAI
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

def handle_db_observability(user_query: str) -> str:
    """
    1. Generates a dynamic SQL query based on user_query.
    2. Fetches the data from Neon DB.
    3. Analyzes the fetched data using Azure OpenAI to generate a DBRE report.
    """
    ack_message = f"[DB Observability Agent] Request received: '{user_query}'\nGenerating query and fetching metrics...\n"
    logging.info(f"DB Observability Agent triggered for query: {user_query}")

    client = AzureOpenAI(
        azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT"),
        api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
        api_version=os.environ.get("OPENAI_API_VERSION")
    )

    # ==========================================
    # STEP 1: Text-to-SQL Generation
    # ==========================================
    schema_definition = """
    Table Name: db_metrics
    Columns:
    - Time_Stamp (timestamp)
    - System_Id (varchar)
    - Application_Name (varchar)
    - Hostname (varchar)
    - Tier (int)
    - CPU_Allocated_vCPU (int)
    - CPU_Usage_Pct (numeric)
    - Memory_Allocated_GB (numeric)
    - Memory_Usage_Pct (numeric)
    - Storage_Allocated_GB (numeric)
    - Storage_Usage_Pct (numeric)
    - Active_Connections (int)
    - Slow_Query_Count (int)
    - Wait_Type (varchar)
    """

    sql_generation_prompt = f"""
    You are an expert PostgreSQL Database Reliability Engineer. Your sole purpose is to convert natural language requests into valid, highly optimized PostgreSQL SELECT queries.

    SCHEMA:
    {schema_definition}

    STRICT CONSTRAINTS:
    1. RAW SQL ONLY: Output nothing but the executable SQL query. No explanations, no markdown formatting (do not use ```sql), and no conversational text.
    2. PREVENT TOKEN OVERFLOW: You MUST append "LIMIT 100" to every query.
    3. SORTING: You MUST append "ORDER BY Time_Stamp DESC" before the LIMIT clause to ensure the most recent data is fetched first.
    4. TIME BOUNDARIES (NO FUTURE DATA): If a relative timeframe is requested (e.g., "last 2 days"), you must exclude synthetic future data by enforcing an upper bound. 
    - Use: `WHERE Time_Stamp >= NOW() - INTERVAL 'X days' AND Time_Stamp <= NOW()`
    5. SMART AGGREGATION: If the user requests a timeframe greater than 24 hours, do not return raw rows. You MUST aggregate the metrics to fit the trend within the 100-row limit. 
    - Group by `DATE_TRUNC('hour', Time_Stamp)`
    - Use `AVG(CPU_Usage_Pct)`, `AVG(Active_Connections)`, `SUM(Slow_Query_Count)`, etc.
    """

    try:
        sql_response = client.chat.completions.create(
            model=os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME"),
            messages=[
                {"role": "system", "content": sql_generation_prompt},
                {"role": "user", "content": user_query}
            ],
            temperature=0.0 # Keep temperature at 0 for strict, deterministic SQL generation
        )
        
        # Clean up the generated SQL (remove potential markdown if the LLM ignores rules)
        generated_sql = sql_response.choices[0].message.content.strip()
        generated_sql = re.sub(r"```sql\n|\n```|```", "", generated_sql).strip()
        logging.info(f"Generated SQL: {generated_sql}")
        
    except Exception as e:
        error_msg = f"Error generating SQL via Azure OpenAI: {str(e)}"
        logging.error(error_msg)
        return ack_message + f"\n[Error] {error_msg}"

    # ==========================================
    # STEP 2: Database Execution
    # ==========================================
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        error_msg = "DATABASE_URL environment variable not set. Please check your .env file."
        logging.error(error_msg)
        return ack_message + f"\n[Error] {error_msg}"
    
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Execute the AI-generated SQL query
        cursor.execute(generated_sql)
        rows = cursor.fetchall()
        
        # Format the data into a CSV string
        if not rows:
            data_context = "No data returned for the requested timeframe/criteria."
        else:
            columns = [desc[0] for desc in cursor.description]
            data_context = ",".join(columns) + "\n"
            for row in rows:
                data_context += ",".join(str(item) for item in row) + "\n"
                
        cursor.close()
        conn.close()
        logging.info("Successfully fetched data from Neon DB.")
        
    except Exception as e:
        error_msg = f"Database execution error: {str(e)}\nAttempted Query: {generated_sql}"
        logging.error(error_msg)
        return ack_message + f"\n[Error] Could not execute the generated query. {error_msg}"

    # ==========================================
    # STEP 3: Data Analysis & DBRE Report
    # ==========================================
    analysis_prompt = """
    You are a Senior Database Reliability Engineer (DBRE) AI specializing in Azure PostgreSQL for Banking Systems.

    1. **Input Analysis:**
    - You will receive database metrics.
    - **Correlate:** specifically check if high `CPU_Usage_Pct` (>80%) aligns with high `Slow_Query_Count` and blocking `Wait_Type` events.

    2. **Prioritization:**
    - **Tier-1 Systems** require immediate "Sev-1" critical incident formatting.
    - **Tier-2/3 Systems** should be treated as "Sev-2" or warning level.

    3. **Actionable Output:**
    - **Root Cause:** Hypothesize the cause based on the metrics.
    - **Remediation:** Recommend specific PostgreSQL or Neon DB actions.

    4. **Format:**
    - Output as a professional **Incident Report Email**.
    - **Subject Line:** [Sev-Level] Alert: [Application Name] (System ID)
    - Keep the body concise.
    - Show the timeperiod of the data analyzed.

    5. **SQL Context:**
    - The SQL query used to fetch the data was: {generated_sql}
    """

    try:
        report_response = client.chat.completions.create(
            model=os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME"),
            messages=[
                {"role": "system", "content": analysis_prompt},
                {"role": "user", "content": f"User query: {user_query}\n\nGenerated SQL Used: {generated_sql}\n\nReturned DB metrics:\n\n{data_context}"}
            ],
            temperature=0.3
        )
        
        analysis = report_response.choices[0].message.content
        logging.info("Azure OpenAI analysis generated successfully.")
        
        # Return the final chain of information
        return f"{ack_message}\n{analysis}"

    except Exception as e:
        logging.error(f"Error generating analysis via Azure OpenAI: {str(e)}")
        return ack_message + "\n[Error] Failed to generate the final analysis."