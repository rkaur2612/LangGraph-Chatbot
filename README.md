# 🤖 LangGraph Chatbot with Persistent Memory

A stateful AI chatbot built using **LangGraph**, **LangChain**, **Streamlit**, and **MCP**. This project demonstrates how to build a production-ready conversational agent that maintains long-term memory across multiple sessions using SQLite persistence while loading tools dynamically from MCP servers.

## 🚀 Key Features

-   **Stateful Orchestration**: Built with `LangGraph` to manage conversation flow and state transitions.
-   **Tool Integration**: Seamlessly integrates with external tools through MCP servers for search, a calculator, and a stock price checker to provide real-time information and computations.
-   **Persistent Storage**: Uses `SqliteSaver` to store conversation checkpoints, allowing users to resume chats even after a server restart.
-   **Real-time Streaming**: Implements token-by-token streaming using `st.write_stream` for a smooth, ChatGPT-like user experience.
-   **Observability**: Integrated with LangSmith for enhanced debugging, monitoring, and tracing of conversation flows and tool usage.
-   **Multi-Thread Management**: Supports multiple independent conversation threads with a dedicated sidebar for navigation.
-   **Dynamic Chat Titles**: Automatically generates human-readable titles for chat sessions based on the initial user prompt.
-   **High Performance**: Powered by the `llama-3.1-8b-instant` model via Groq for ultra-fast inference.

## 🛠️ Technologies & Frameworks

| Category | Technology |
| :--- | :--- |
| **LLM Orchestration** | LangGraph |
| **LLM Framework** | LangChain | 
| **Tool Transport** | MCP (MultiServerMCPClient + FastMCP) |
| **Inference Engine** | Groq (Llama 3.1 8B) |
| **Frontend** | Streamlit |
| **Database** | SQLite (via `SqliteSaver`) |
| **Tooling** | DuckDuckGo search, Alpha Vantage API, calculator |
| **Observability** | LangSmith |
| **Environment** | Python, Dotenv, Pydantic |

## 📐 Graph Architecture

The chatbot logic is structured as a state machine. This ensures that every interaction is tracked and can be resumed at any point. The LLM only decides whether a tool should be called; the actual tool execution happens through MCP servers discovered at runtime.

```mermaid
graph LR
    START((START)) --> ChatNode[Chat Node]
    ChatNode -- Tools needed? --> ToolsNode[Tools Node]
    ToolsNode --> ChatNode
    ChatNode -- No tools needed --> END((END))
    
    subgraph StateManagement
    ChatNode -.-> Checkpointer[(SQLite DB)]
    Checkpointer -.-> ChatNode
    end
```

1.  **START**: The graph receives the user input and the current `thread_id`.
2.  **Chat Node**: The LLM processes message history and determines if a tool call is required based on strict system instructions designed to prevent hallucinations.
3.  **ToolNode**: If a tool is requested, LangGraph routes to `ToolNode`, which executes the MCP-backed tool.
4.  **MCP Servers**: The tool call is forwarded through `MultiServerMCPClient` to the appropriate server process (`calculator_server.py`, `stock_server.py`, or `search_server.py`).
5.  **Checkpointer**: Every state transition and tool result is persisted to the SQLite database for session continuity.
6.  **END**: The finalized response is streamed back to the Streamlit UI.

## 📁 Project Structure

-   `streamlit_frontend_database.py`: The main entry point. Handles the UI, sidebar logic, and session state.
-   `langgraph_tool_backend.py`: **Main Logic File**. Integrates advanced tool logic on top of the database backend. It includes **strict system prompting** to mitigate hallucinations, **graceful fallback logic** for tool failures, **MCP client orchestration**, and **LangSmith observability**.
-   `langgraph_database_backend.py`: A simplified version of the backend focusing on SQLite state management without tool integration.
-   `langgraph_backend.py`: A lightweight version of the backend using in-memory saving (`MemorySaver`).
-   `mcp_servers/calculator_server.py`: MCP server for arithmetic operations.
-   `mcp_servers/stock_server.py`: MCP server for stock quotes via Alpha Vantage.
-   `mcp_servers/search_server.py`: MCP server for web search.
-   `chatbot.db`: The SQLite database where all conversation history and threads are stored.

## 🏁 Getting Started

### Prerequisites
- Python 3.10+
- Groq API Key
- Alpha Vantage API Key

### Installation

1. **Clone the repository:**
   ```bash
   git clone
   cd LangGraph-Chatbot
   ```

2. **Set up a virtual environment:**
   ```bash
   python -m venv .venv
   # Windows
   .\.venv\Scripts\activate
   # Mac/Linux
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configuration:**
   Create a `.env` file in the root directory and add your Groq API key and Alpha Vantage key:
   ```env
   GROQ_API_KEY=your_api_key_here
   ALPHAVANTAGE_API_KEY=your_alpha_vantage_api_key_here
   ```

   The MCP servers are launched automatically by the LangGraph backend through `MultiServerMCPClient`; you do not need to start them manually.

5. **Run the application:**
   ```bash
   streamlit run streamlit_frontend_database.py
   ```

## 🔮 Future Roadmap

-   [ ] **AI Title Generation**: Use the LLM to generate more descriptive 3-5 word titles for chats.
-   [ ] **Message Editing**: Allow users to edit previous messages and re-trigger the graph from that checkpoint.

---
*Developed as part of the LangGraph Learning Path.*

---

Developed by **Ramandeep** 🚀