import { useState } from 'react'
import ReactMarkdown from 'react-markdown'

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  // New state to hold the dynamic "thinking" text
  const [agentStatus, setAgentStatus] = useState(""); 

  const quickQuestions = [
    "Show current DB health and monitoring status",
    "Analyze a slow SQL query and suggest optimizations",
    "Find missing indexes for better performance",
    "Explain the query plan for this SQL",
    "Detect potential deadlocks or lock waits",
    "Compare RAM cache vs disk reads for PostgreSQL",
    "Recommend SQL tuning for a high-cost query",
    "Check connection pool and active connections",
    "Review query execution time and CPU usage",
    "Summarize database performance risks"
  ];

  // Function to check if message is an optimization result
  const isOptimizationResult = (text) => {
    try {
      const cleanText = text.replace(/^✓\s*/, '');
      const parsed = JSON.parse(cleanText);
      return parsed && typeof parsed === 'object' && 'optimized_sql' in parsed;
    } catch {
      return false;
    }
  };

  // Component to render optimization charts
  const renderOptimizationCharts = (text) => {
    try {
      const cleanText = text.replace(/^✓\s*/, '');
      const data = JSON.parse(cleanText);

      return (
        <div style={{ padding: '12px', background: '#f8fafc', borderRadius: '8px', marginTop: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
            <div style={{ fontSize: '1.2rem', fontWeight: '600', color: '#1f2937' }}>Query Analysis</div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <span style={{ 
                padding: '4px 8px', 
                borderRadius: '12px', 
                fontSize: '0.8rem', 
                fontWeight: '500',
                background: data.health_indicator === '🟢' ? '#d1fae5' : data.health_indicator === '🟡' ? '#fef3c7' : '#fee2e2',
                color: data.health_indicator === '🟢' ? '#065f46' : data.health_indicator === '🟡' ? '#92400e' : '#991b1b'
              }}>
                {data.health_indicator} {data.status}
              </span>
              <span style={{ 
                padding: '4px 8px', 
                borderRadius: '12px', 
                fontSize: '0.8rem', 
                fontWeight: '500',
                background: data.execution_verified ? '#d1fae5' : '#f3f4f6',
                color: data.execution_verified ? '#065f46' : '#6b7280'
              }}>
                {data.execution_verified ? '✓ Verified' : '⏳ Pending'}
              </span>
              <span style={{ 
                padding: '4px 8px', 
                borderRadius: '12px', 
                fontSize: '0.8rem', 
                fontWeight: '500',
                background: '#eff6ff',
                color: '#1e40af'
              }}>
                {data.performance_comparison?.efficiency_gain || 'N/A'}
              </span>
            </div>
          </div>

          <div style={{ background: 'white', padding: '12px', borderRadius: '8px', border: '1px solid #e5e7eb', marginBottom: '8px' }}>
            <div style={{ fontSize: '0.9rem', fontWeight: '500', color: '#374151', marginBottom: '4px' }}>Optimized Query</div>
            <pre style={{ background: '#f9fafb', padding: '8px', borderRadius: '4px', fontSize: '0.85rem', margin: 0, overflow: 'auto', border: '1px solid #e5e7eb' }}>
              {data.optimized_sql}
            </pre>
          </div>

          <div style={{ background: 'white', padding: '12px', borderRadius: '8px', border: '1px solid #e5e7eb', marginBottom: '8px' }}>
            <div style={{ fontSize: '0.9rem', fontWeight: '500', color: '#374151', marginBottom: '4px' }}>Recommended Action</div>
            <pre style={{ background: '#f9fafb', padding: '8px', borderRadius: '4px', fontSize: '0.85rem', margin: 0, overflow: 'auto', border: '1px solid #e5e7eb' }}>
              {data.suggested_fix}
            </pre>
          </div>

          <div style={{ background: 'white', padding: '12px', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
            <div style={{ fontSize: '0.9rem', fontWeight: '500', color: '#374151', marginBottom: '4px' }}>Performance Notes</div>
            <p style={{ margin: 0, fontSize: '0.85rem', lineHeight: '1.4', color: '#4b5563' }}>{data.audit_note}</p>
          </div>
        </div>
      );
    } catch (error) {
      console.error('Error rendering optimization charts:', error);
      return <ReactMarkdown>{text}</ReactMarkdown>;
    }
  };

  const sendMessage = async (messageText) => {
    const text = messageText ?? input;
    if (!text.trim()) return;

    const userMsg = { sender: "User", text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setAgentStatus("Connecting to routing agent..."); // Initial status

    try {
      const response = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMsg.text }),
      });
      
      // Read the stream
      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let done = false;

      while (!done) {
        const { value, done: doneReading } = await reader.read();
        done = doneReading;
        
        if (value) {
          const chunk = decoder.decode(value, { stream: true });
          // Split by newline in case multiple JSON chunks arrive together
          const lines = chunk.split('\n').filter(Boolean);
          
          for (const line of lines) {
            const data = JSON.parse(line);
            
            if (data.type === "status") {
              // Update the live thinking text
              setAgentStatus(data.message);
            } else if (data.type === "result") {
              // Clear status and append the final response
              setAgentStatus("");
              setMessages((prev) => [...prev, { sender: "System", text: "✓ " + data.message }]);
            }
          }
        }
      }
    } catch (error) {
      console.error("Error:", error);
      setAgentStatus("");
      setMessages((prev) => [...prev, { sender: "System", text: "Error connecting to server." }]);
    }
  };

  return (
    <div style={{ minHeight: "100vh", background: "#f6f8fb", fontFamily: "sans-serif", padding: "24px" }}>
      <div style={{ maxWidth: "1400px", margin: "0 auto" }}>
        <header style={{ marginBottom: "24px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h1 style={{ margin: 0, fontSize: "2rem", color: "#111827" }}>Database Support Chatbot</h1>
            <p style={{ margin: "8px 0 0", color: "#4b5563" }}>
              Ask questions, analyze slow SQL, monitor health, and use quick recommendations.
            </p>
          </div>
        </header>

        <div style={{ display: "grid", gridTemplateColumns: "1.9fr 1fr", gap: "24px" }}>
          <section style={{ background: "#ffffff", borderRadius: "20px", boxShadow: "0 20px 60px rgba(0, 0, 0, 0.05)", padding: "24px", minHeight: "720px", display: "flex", flexDirection: "column" }}>
            <div style={{ flex: 1, marginBottom: "18px", overflow: "hidden", borderRadius: "18px", border: "1px solid #e5e7eb" }}>
              <div style={{ height: "100%", overflowY: "auto", padding: "22px", background: "#fbfbfc" }}>
                {messages.map((msg, index) => (
                  <div key={index} style={{ margin: "14px 0", textAlign: msg.sender === "User" ? "right" : "left" }}>
                    <div style={{ marginBottom: "6px", color: "#374151", fontSize: "0.95rem", fontWeight: 600 }}>
                      {msg.sender}
                    </div>
                    <div style={{
                      display: "inline-block",
                      background: msg.sender === "User" ? "#dbeafe" : "#eff6ff",
                      color: "#111827",
                      padding: "16px 18px",
                      borderRadius: "18px",
                      maxWidth: "85%",
                      textAlign: "left",
                      boxShadow: "0 8px 20px rgba(15, 23, 42, 0.06)"
                    }}>
                      {isOptimizationResult(msg.text) ? renderOptimizationCharts(msg.text) : <ReactMarkdown>{msg.text}</ReactMarkdown>}
                    </div>
                  </div>
                ))}

                {agentStatus && (
                  <div style={{ marginTop: "20px", color: "#2563eb", fontStyle: "italic" }}>
                    <span style={{ marginRight: "8px" }}>⚙️</span>
                    {agentStatus}
                  </div>
                )}
              </div>
            </div>

            <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
                placeholder="Ask a database question..."
                style={{ flex: 1, padding: "14px 16px", borderRadius: "14px", border: "1px solid #d1d5db", outline: "none" }}
              />
              <button
                onClick={() => sendMessage()}
                style={{ padding: "14px 26px", cursor: "pointer", backgroundColor: "#2563eb", color: "white", border: "none", borderRadius: "14px", fontWeight: 600 }}
              >
                Send
              </button>
            </div>
          </section>

          <aside style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            <div style={{ background: "#ffffff", borderRadius: "20px", boxShadow: "0 20px 60px rgba(0, 0, 0, 0.05)", padding: "24px" }}>
              <h3 style={{ margin: "0 0 16px", color: "#111827" }}>Top 10 DB Questions</h3>
              <p style={{ margin: "0 0 18px", color: "#4b5563" }}>
                Click one to auto-run the recommendation or type your own question.
              </p>
              <div style={{ display: "grid", gap: "12px" }}>
                {quickQuestions.map((question) => (
                  <button
                    key={question}
                    onClick={() => sendMessage(question)}
                    style={{
                      width: "100%",
                      textAlign: "left",
                      padding: "14px 16px",
                      borderRadius: "14px",
                      border: "1px solid #e5e7eb",
                      background: "#f8fafc",
                      cursor: "pointer",
                      color: "#111827",
                      fontWeight: 500
                    }}
                  >
                    {question}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ background: "#ffffff", borderRadius: "20px", boxShadow: "0 20px 60px rgba(0, 0, 0, 0.05)", padding: "24px" }}>
              <h3 style={{ margin: "0 0 16px", color: "#111827" }}>DB Health Dashboard</h3>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "16px" }}>
                <div style={{ textAlign: "center", padding: "16px", background: "#f8fafc", borderRadius: "12px" }}>
                  <div style={{ fontSize: "2rem", color: "#10b981" }}>🟢</div>
                  <div style={{ fontWeight: 600, color: "#111827" }}>Healthy</div>
                  <div style={{ color: "#4b5563" }}>Connections</div>
                </div>
                <div style={{ textAlign: "center", padding: "16px", background: "#f8fafc", borderRadius: "12px" }}>
                  <div style={{ fontSize: "2rem", color: "#f59e0b" }}>⚠️</div>
                  <div style={{ fontWeight: 600, color: "#111827" }}>2 Slow Queries</div>
                  <div style={{ color: "#4b5563" }}>Detected</div>
                </div>
              </div>
              <div style={{ marginTop: "20px", height: "120px", background: "#f8fafc", borderRadius: "12px", display: "flex", alignItems: "center", justifyContent: "center", color: "#4b5563" }}>
                Graph Placeholder: CPU Usage Over Time
              </div>
            </div>

            <div style={{ background: "#ffffff", borderRadius: "20px", boxShadow: "0 20px 60px rgba(0, 0, 0, 0.05)", padding: "24px" }}>
              <h3 style={{ margin: "0 0 16px", color: "#111827" }}>Why use this?</h3>
              <ul style={{ paddingLeft: "20px", color: "#4b5563", margin: 0, lineHeight: 1.8 }}>
                <li>Quick access to common Postgres issues</li>
                <li>Use chat or one-click questions</li>
                <li>Directly query database metrics</li>
                <li>Meaningful answers with minimal typing</li>
              </ul>
            </div>
          </aside>
        </div>
      </div>
    </div>
  )
}

export default App