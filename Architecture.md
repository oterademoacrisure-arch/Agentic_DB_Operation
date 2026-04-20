# EDDI-Chatbot Architecture Document

## Overview

EDDI-Chatbot is an intelligent database support chatbot designed to assist with PostgreSQL database operations, including query optimization and system observability. The application consists of a backend API built with FastAPI and a frontend user interface built with React/Vite. It leverages AI agents powered by Azure OpenAI to provide intelligent responses and recommendations.

## System Architecture

### High-Level Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API   │    │   Database      │
│   (React/Vite)  │◄──►│   (FastAPI)     │◄──►│   (PostgreSQL)  │
│                 │    │                 │    │                 │
│ - Chat UI       │    │ - Routing Agent │    │ - User Data     │
│ - Streaming     │    │ - Optimization  │    │ - Audit Logs    │
│ - Real-time     │    │   Agent         │    │ - Metrics       │
└─────────────────┘    │ - Observability │    └─────────────────┘
                       │   Agent         │
                       └─────────────────┘
```

### Technology Stack

#### Backend
- **Framework**: FastAPI (Python web framework for building APIs)
- **Language**: Python 3.x
- **AI Integration**: Azure OpenAI API
- **Database Driver**: psycopg2 (PostgreSQL adapter for Python)
- **Environment Management**: python-dotenv
- **Data Validation**: Pydantic
- **CORS Handling**: FastAPI middleware
- **Streaming**: Server-Sent Events (SSE) via NDJSON

#### Frontend
- **Framework**: React 18
- **Build Tool**: Vite
- **Language**: JavaScript (JSX)
- **Styling**: CSS
- **HTTP Client**: Fetch API (built-in)
- **State Management**: React hooks
- **Routing**: React Router (if needed)

#### Database
- **Database**: PostgreSQL
- **Schema**: Production schema for data isolation
- **Connection**: psycopg2 with connection pooling
- **Audit Logging**: Custom `query_audit_log` table

#### Infrastructure
- **Deployment**: Local development with uvicorn
- **Environment Variables**: .env file for configuration
- **Version Control**: Git
- **Containerization**: Not implemented (can be added with Docker)

## Component Breakdown

### 1. Frontend (React/Vite)

#### Purpose
Provides a user-friendly chat interface for interacting with the database support chatbot.

#### Key Components
- **App.jsx**: Main application component
- **Main.jsx**: Entry point with React rendering
- **CSS Files**: Styling for UI components
- **Assets**: Static files (SVG icons, etc.)

#### Features
- Real-time chat interface
- Streaming responses from backend
- Responsive design
- Error handling for API failures

#### Integration
- Communicates with backend via HTTP POST to `/api/chat`
- Receives streaming responses in NDJSON format
- Handles CORS for local development

### 2. Backend API (FastAPI)

#### Purpose
Serves as the central API gateway, handling requests, routing to appropriate agents, and streaming responses.

#### Key Files
- **main.py**: FastAPI application setup, CORS configuration, chat endpoint
- **agents/router.py**: Intelligent routing logic using AI
- **agents/optimization/**: Query optimization agent
- **agents/observability/**: Database observability agent

#### Endpoints
- `GET /`: Health check endpoint
- `POST /api/chat`: Main chat endpoint accepting `{"message": "user query"}`

#### Features
- Asynchronous request handling
- Streaming responses using `StreamingResponse`
- CORS middleware for frontend integration
- Environment variable loading

### 3. Routing Agent

#### Location
`backend/agents/router.py`

#### Purpose
Analyzes user queries and routes them to the appropriate specialized agent.

#### How It Works
1. Receives user query as string
2. Uses Azure OpenAI to classify query intent:
   - `greeting`: Simple welcome responses
   - `db_observability`: Database health metrics
   - `query_optimization`: SQL performance analysis
   - `ambiguous`: Requests clarification
   - `out_of_domain`: Rejects non-database queries
3. Routes to appropriate handler function
4. Yields status updates and final response via generator

#### Technologies Used
- Azure OpenAI GPT model for intent classification
- JSON response parsing
- Generator functions for streaming

### 4. Query Optimization Agent

#### Location
`backend/agents/optimization/executionlayer/db_connector.py`

#### Purpose
Analyzes SQL queries, provides optimization recommendations, and logs results to database.

#### How It Works
1. **Metadata Resolution**: Uses `db_service.py` to extract column information from query
2. **Plan Analysis**: Executes `EXPLAIN` to get query execution plan and costs
3. **AI Analysis**: Sends metadata and plan to Azure OpenAI for optimization recommendations
4. **Response Generation**: Returns JSON with health indicators, optimized SQL, and suggestions
5. **Audit Logging**: Inserts old query, new query, and full JSON response into `query_audit_log` table

#### Technologies Used
- PostgreSQL `EXPLAIN` for query analysis
- Azure OpenAI for intelligent optimization suggestions
- JSON parsing and validation
- Database logging with parameterized queries

#### Output Format
```json
{
  "execution_verified": true,
  "health_indicator": "🟢 | 🟡 | 🔴",
  "status": "Verified | Optimization Recommended | Critical Error",
  "performance_comparison": {
    "workload_effort_original": "original cost",
    "workload_effort_projected": "optimized cost",
    "efficiency_gain": "percentage"
  },
  "optimized_sql": "optimized SQL query",
  "suggested_fix": "index creation or infrastructure note",
  "audit_note": "I/O path and scan type explanation"
}
```

### 5. Database Observability Agent

#### Location
`backend/agents/observability/db_observe.py`

#### Purpose
Provides database health monitoring and system metrics analysis.

#### How It Works
1. **Text-to-SQL**: Converts natural language requests to PostgreSQL queries
2. **Data Retrieval**: Executes queries against `db_metrics` table
3. **AI Analysis**: Uses Azure OpenAI to analyze metrics and generate reports
4. **Report Generation**: Provides insights on CPU, memory, connections, etc.

#### Technologies Used
- Dynamic SQL generation via AI
- PostgreSQL queries for metrics retrieval
- Azure OpenAI for report generation
- Logging for debugging

### 6. Database Layer

#### Location
`backend/agents/optimization/datalayer/db_service.py`

#### Purpose
Provides low-level database operations and connection management.

#### Components
- **PostgresClient Class**: Handles database connections and queries
- **execute_query()**: Executes SQL with RealDictCursor for JSON results
- **get_query_metadata()**: Extracts column information by running queries with `WHERE 1=0`
- **investigate()**: Runs `EXPLAIN` for query plan analysis

#### Features
- Connection pooling via psycopg2
- Schema isolation (`production` schema)
- Error handling and connection cleanup
- Metadata extraction without data retrieval

## Data Flow

### Query Processing Flow

1. **User Input**: User types query in frontend chat interface
2. **API Request**: Frontend sends POST to `/api/chat` with message
3. **Intent Classification**: Router agent uses AI to classify query type
4. **Status Streaming**: Backend yields status updates ("Analyzing request intent...")
5. **Agent Execution**:
   - For optimization: Extracts metadata, runs EXPLAIN, generates recommendations
   - For observability: Generates SQL, fetches metrics, analyzes with AI
6. **Response Streaming**: Final response streamed back as NDJSON
7. **Audit Logging**: Optimization results logged to database

### Database Schema

#### query_audit_log Table
```sql
CREATE TABLE query_audit_log (
    id SERIAL PRIMARY KEY,
    old_query TEXT,
    new_query TEXT,
    optimization_json JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### db_metrics Table (for observability)
```sql
CREATE TABLE db_metrics (
    Time_Stamp TIMESTAMP,
    System_Id VARCHAR,
    Application_Name VARCHAR,
    Hostname VARCHAR,
    Tier INTEGER,
    CPU_Allocated_vCPU INTEGER,
    CPU_Usage_Pct NUMERIC,
    Memory_Allocated_GB NUMERIC,
    Memory_Usage_Pct NUMERIC,
    Storage_Allocated_GB NUMERIC,
    Storage_Usage_Pct NUMERIC,
    Active_Connections INTEGER,
    Slow_Query_Count INTEGER,
    Wait_Type VARCHAR
);
```

## Security Considerations

- **API Keys**: Stored in environment variables, not committed to repository
- **CORS**: Configured for local development ports
- **Input Validation**: Pydantic models for request validation
- **SQL Injection Prevention**: Parameterized queries and input sanitization
- **Secrets Management**: .env files excluded from version control

## Deployment and Scaling

### Local Development
- Backend: `uvicorn main:app --reload --host 127.0.0.1 --port 8000`
- Frontend: `npm run dev` (serves on port 5177)
- Database: Local PostgreSQL instance

### Production Considerations
- **Containerization**: Add Docker for backend and frontend
- **Reverse Proxy**: Nginx for static file serving and API proxying
- **Database**: Managed PostgreSQL (AWS RDS, Google Cloud SQL, etc.)
- **AI Service**: Azure OpenAI or alternative LLM providers
- **Monitoring**: Add logging and metrics collection
- **Load Balancing**: For multiple backend instances

## Future Enhancements

- **Multi-Database Support**: Extend beyond PostgreSQL
- **Advanced Analytics**: Historical performance trends
- **Automated Fixes**: Direct index creation and query rewriting
- **User Authentication**: Secure access control
- **Real-time Monitoring**: WebSocket connections for live metrics
- **Plugin Architecture**: Extensible agent system

## Conclusion

EDDI-Chatbot demonstrates a modern AI-powered application architecture combining web technologies, intelligent agents, and database expertise. The modular design allows for easy extension and maintenance, while the streaming architecture provides responsive user interactions.