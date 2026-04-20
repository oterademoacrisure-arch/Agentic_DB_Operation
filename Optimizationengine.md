# 🛠️ Project Dependencies & Technical Justification

This document provides a detailed breakdown of the software ecosystem powering the **Watchman Agent**. Each library has been strategically selected to handle high-load database environments and complex AI reasoning.

## 1. Core AI, RAG & Optimization Engine
These libraries form the "Cognitive Layer," enabling the agent to understand SQL semantics and retrieve the correct governance rules.

| Library | What does this library do? | Reason for Choice in This Project |
| :--- | :--- | :--- |
| **`openai`** | Interface for Large Language Models. | Communicates with **Azure OpenAI** to provide optimized SQL rewrites and technical reasoning based on DB stats. |
| **`sentence-transformers`** | Text embedding generator. | Converts your Excel guardrail chunks into vector embeddings for semantic search in the RAG service. |
| **`faiss-cpu`** | Vector similarity search engine. | Allows the agent to instantly find the best matching "Excel Rule" even if the query text doesn't match exactly. |
| **`torch`** | Deep learning framework. | The underlying engine required to run the `sentence-transformers` models for your RAG pipeline. |
| **`transformers`** | NLP model utilities. | Provides the architectural support for the AI to understand complex SQL query structures. |



---

## 2. Monitoring & Autonomous Action (Kafka & DB)
These libraries allow the script to "observe" the database and "act" autonomously to prevent downtime.

| Library | What does this library do? | Reason for Choice in This Project |
| :--- | :--- | :--- |
| **`kafka-python`** | Distributed messaging client. | Streams live incident reports and "auto-heal" logs to your Kafka broker for observability. |
| **`psycopg2-binary`** | PostgreSQL database adapter. | Facilitates the core "Watchdog" logic: monitoring `pg_stat_activity` and executing `pg_terminate_backend`. |
| **`pandas`** | Data analysis/manipulation. | Used to parse and structure the knowledge base from your Excel-based guardrail sheet. |
| **`openpyxl`** | Excel file engine. | Required specifically to read the `.xlsx` file format used for the governance knowledge base. |

---

## 🏗️ System Architecture: The Autonomous Healing Loop

The Watchman Agent operates as a closed-loop system across four distinct layers:

1.  **Detection Layer (Observability):** The agent uses **psycopg2** to poll `pg_stat_activity` every 60 seconds, identifying "Stuck" queries or deadlocks.
2.  **Intelligence Layer (RAG + AI):** Problematic queries are embedded via **sentence-transformers** and matched against the Excel Knowledge Base using **FAISS**.
3.  **Execution Layer (Remediation):** For deadlocks, the agent executes `pg_terminate_backend(pid)`. For slow queries, an `optimized_sql` suggestion is generated.
4.  **Communication Layer (Kafka):** Every action and AI reasoning step is published as a JSON payload to the Kafka broker for a permanent audit trail.



---

## 🛠️ Troubleshooting & Common Issues

| Issue | Potential Cause | Resolution |
| :--- | :--- | :--- |
| **`ImportError`** | Libraries installed outside the `venv`. | Activate the virtual environment and run `pip install -r requirements.txt`. |
| **`psycopg2` Timeout** | Incorrect credentials or Firewall. | Verify your DB config and ensure your local IP is allowed in the Neon Console. |
| **`NoBrokersAvailable`** | Kafka broker is down. | Ensure Zookeeper and Kafka services are started on `localhost:9092`. |
| **`faiss_index.bin` Missing** | RAG init was skipped. | Run `python -m agents.optimization.servicelayer.rag_service` to generate the index. |

---

### 💡 Maintenance Tip
Whenever you update the **Excel Knowledge Base**, you must re-run the `rag_service.py` script to refresh the FAISS vector embeddings.
