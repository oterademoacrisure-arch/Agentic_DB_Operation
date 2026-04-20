import os
import json
from dotenv import load_dotenv
from openai import AzureOpenAI
from agents.observability.db_observe import handle_db_observability
from agents.optimization.executionlayer.db_connector import handle_query_optimization

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

# Initialize the Azure OpenAI client
client = AzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)

DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
MAX_FOLLOWUP_COUNT = 5

def route_query_stream(user_query: str, followup_count: int = 0):
    """
    Generator function that yields status updates before yielding the final response.
    """
    print(f"[DEBUG] Routing query: {user_query}")
    # 1. Yield initial thinking status
    yield json.dumps({"type": "status", "message": "Analyzing request intent..."}) + "\n"

    system_prompt = """
    You are an intelligent routing agent for a database support chatbot. 
    Analyze the user's input and classify it into exactly one of these categories:
    
    1. 'greeting': The user is saying hello, hi, or asking how you are.
    2. 'db_observability': Database health, CPU, memory, connection pooling, or system metrics.
    3. 'query_optimization': SQL performance, slow queries, EXPLAIN plans, or indexing.
    4. 'ambiguous': If the query is vague and could apply to both DB health or query speed.
    5. 'out_of_domain': The query is completely unrelated to databases or SQL.
    
    You MUST respond with a valid JSON object containing exactly these four keys:
    - "intent": The category name (string).
    - "confidence_score": A float between 0.0 and 1.0 indicating your certainty.
    - "summary": A concise, technical summary of what the user needs.
    - "followup_question": If the intent is 'ambiguous', provide a short question to clarify. Otherwise, leave empty.
    """

    try:
        response = client.chat.completions.create(
            model=DEPLOYMENT_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ],
            temperature=0.0,
            response_format={ "type": "json_object" } 
        )
        
        llm_output = json.loads(response.choices[0].message.content)
        intent = llm_output.get("intent")
        confidence = llm_output.get("confidence_score", 0.0)
        summary = llm_output.get("summary", "")
        followup_question = llm_output.get("followup_question", "")

        # 2. Yield the decision status
        yield json.dumps({"type": "status", "message": f"Intent identified: {intent.replace('_', ' ').title()}"}) + "\n"

    except Exception as e:
        yield json.dumps({"type": "result", "message": "Sorry, I encountered an internal error while trying to process your request."}) + "\n"
        return

    # --- Routing & Response Logic ---
    
    if intent == "greeting":
        yield json.dumps({"type": "status", "message": "Generating welcome message..."}) + "\n"
        final_text = (
            "Hello! Welcome to the Database Support Chatbot. 👋\n\n"
            "I can help you keep your databases running smoothly. I currently support:\n"
            "- **Database Observability:** Checking CPU, memory, connection pools, and system metrics.\n"
            "- **Query Optimization:** Analyzing slow SQL queries and providing indexing recommendations.\n\n"
            "How can I assist you today?"
        )
        yield json.dumps({"type": "result", "message": final_text}) + "\n"

    elif intent == "out_of_domain":
        final_text = (
            "I specialize strictly in database support and cannot assist with that request.\n\n"
            "**Here are the use cases I currently support:**\n"
            "1. Database Observability & System Health\n"
            "2. SQL Query Optimization"
        )
        yield json.dumps({"type": "result", "message": final_text}) + "\n"

    elif intent == "ambiguous":
        if followup_count < MAX_FOLLOWUP_COUNT:
            yield json.dumps({"type": "result", "message": followup_question}) + "\n"
        else:
            yield json.dumps({"type": "result", "message": "Please specify if you need help with 'Database Health' or 'Query Performance'."}) + "\n"

    else:
        # Route Valid Technical Queries
        agent_payload = f"Summary: {summary} | Confidence Score: {confidence}"

        if intent == "db_observability":
            # 3. Yield agent handoff status
            yield json.dumps({"type": "status", "message": "Observability Agent is gathering database metrics..."}) + "\n"
            result = handle_db_observability(user_query)
            yield json.dumps({"type": "result", "message": result}) + "\n"
            
        elif intent == "query_optimization":
            # 3. Yield agent handoff status
            print(f"[DEBUG] Routing to query optimization for: {user_query}")
            yield json.dumps({"type": "status", "message": "Optimization Agent is running EXPLAIN plans..."}) + "\n"
            result = handle_query_optimization(user_query)
            yield json.dumps({"type": "result", "message": result}) + "\n"