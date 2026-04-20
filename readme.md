# Database AI Support Chatbot

This project is a multi-agent AI chatbot that helps with Database Observability and SQL Query Optimization. It uses a React frontend, a Python/FastAPI backend, and Azure OpenAI for intelligent routing and analysis.

## 📋 Prerequisites
Before you begin, ensure you have the following installed on your system:
* **Python 3.14 (for the backend)
* **Node.js & npm** (for the frontend)


## 🛠️ Step 1: Backend Setup (Python / FastAPI)

1. **Navigate to the backend folder:**
   ```bash
   cd backend

2. **Create and activate a virtual environment:**
    * **Windows:**
    ```bash
    python -m venv venv
    venv\Scripts\activate

    ```

    * **Mac/Linux:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate

    ```

3. **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt

    ```

4. **Set up Environment Variables:**
    Create a `.env` file inside the `backend` folder and add your credentials:
    ```env
    AZURE_OPENAI_ENDPOINT="https://<your-resource>[.openai.azure.com/](https://.openai.azure.com/)"
    AZURE_OPENAI_API_KEY="<your-key>"
    AZURE_OPENAI_API_VERSION="2024-02-15-preview"
    AZURE_OPENAI_DEPLOYMENT_NAME="<your-deployment-name>"

    # Database connection string or config used by psycopg2
    DATABASE_URL="postgresql+psycopg2://user:password@host:port/dbname?sslmode=require"

    ```

5. **Start the backend server:**
    ```bash
    uvicorn main:app --reload

    ```

*(The API will run on http://localhost:8000)*

---

## 🎨 Step 2: Frontend Setup (React / Vite)

1. **Open a new terminal** and navigate to the frontend folder:
    ```bash
    cd frontend

    ```

2. **Install Node dependencies:**
*(Note: `--legacy-peer-deps` is required to resolve standard ESLint conflicts in the Vite template).*
    ```bash
    npm install --legacy-peer-deps

    ```

3. **Start the frontend development server:**
    ```bash
    npm run dev

    ```

*(The UI will run on http://localhost:5173)*

---

## 🚀 Step 3: Usage

1. Open your browser and navigate to **http://localhost:5173**.
2. Start chatting! Ask the bot about database health metrics or paste a slow SQL query for optimization.
