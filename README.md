# ChatBuddy 🫂

## Overview
A conversational AI assistant that evolved from a LangGraph chatbot into a modular MCP-powered AI application with persistent conversations and PDF-based RAG.

ChatBuddy started as a learning project for understanding LangGraph and gradually evolved into a production-style GenAI application.

The project was built incrementally: conversation state and memory came first, followed by persistence, streaming, multi-thread conversations, observability, tool calling, Model Context Protocol (MCP), multiple MCP servers, PostgreSQL-backed expense management, and finally Retrieval-Augmented Generation (RAG).

The current version uses a Streamlit MCP client connected to multiple independent MCP servers. RAG is exposed as another MCP capability, allowing users to upload a PDF for a conversation and ask questions grounded in that document.

## Current Features

### Chat
- Multi-thread conversations
- Persistent chat history
- Resume previous conversations
- Dynamic conversation titles
- Streamlit chat interface
- SQLite application persistence
- Clear current conversation
- Tool execution status in the UI

### MCP Tools

| Capability | MCP tool(s) | Backend |
|---|---|---|
| Arithmetic | `calculator` | Python |
| Web search | `web_search` | DuckDuckGo |
| Stock price | `get_stock_price` | Alpha Vantage |
| Weather | `get_weather_details` | OpenWeather |
| Currency | `currency_converter` | Exchange-rate API |
| Expense tracker | `add_expense`, `list_expenses`, `summarize_expenses`, `edit_expense`, `delete_expense`, `credit` | PostgreSQL |
| RAG | `index_pdf`, `rag_search`, `remove_knowledge_base` | FAISS + Hugging Face |

## Current Architecture

```text
                              User
                                |
                                v
                     +---------------------+
                     |    Streamlit UI     |
                     |      ChatBuddy      |
                     +----------+----------+
                                |
                                v
                     +---------------------+
                     |      MCP Client     |
                     |   Qwen3-4B-Instruct |
                     +----------+----------+
                                |
                                v
                       LLM Tool Selection
                                |
        +-----------------------+------------------------+
        |              |              |                 |
        v              v              v                 v
   Arithmetic      Web Search      Weather           Stock
   MCP Server      MCP Server      MCP Server         MCP Server
        |              |              |                 |
   Calculator      DuckDuckGo      OpenWeather       Alpha Vantage

        +-----------------------+------------------------+
        |                       |                        |
        v                       v                        v
   Currency MCP           Expense MCP                RAG MCP
       Server                 Server                   Server
        |                       |                        |
   Exchange API            PostgreSQL             FAISS Index
                                                     ^
                                                     |
                                             Hugging Face API
                                                     ^
                                                     |
                                                  PDF File
```

## MCP Server Structure

```text
mcp-server/
|
+-- db/
|   +-- __init__.py
|   +-- connection.py
|
+-- arithmetic-server.py
+-- search-server.py
+-- stock-server.py
+-- weather-server.py
+-- currency-server.py
+-- expense-tracker-server.py
+-- rag-server.py
|
+-- rag_data/
+-- .env
+-- pyproject.toml
+-- uv.lock
```

The client lives separately:

```text
mcp-client/
|
+-- client.py
+-- chatbuddy_mcp.db
+-- pyproject.toml
+-- .venv/
```

## Technology Stack

### Application
- Python
- Streamlit
- SQLite

### LLM
- Qwen/Qwen3-4B-Instruct-2507
- Hugging Face Inference API

### MCP
- FastMCP
- LangChain MCP Adapters
- MCP Inspector
- stdio transport

### RAG
- LangChain
- PyPDF / PyPDFLoader
- RecursiveCharacterTextSplitter
- Hugging Face Embedding API
- `sentence-transformers/all-MiniLM-L6-v2`
- FAISS

### Backend and Data
- PostgreSQL
- psycopg

### External APIs
- Hugging Face
- DuckDuckGo
- OpenWeather
- Alpha Vantage
- Exchange-rate API

## Installation

The project uses `uv` for Python dependency and environment management.

Separate environments are used for the MCP client and MCP server.

### MCP Client

```powershell
cd C:\\Github\\ChatBuddy\\mcp-client
uv add streamlit python-dotenv langchain-core langchain-huggingface langchain-mcp-adapters
```

### MCP Server

```powershell
cd C:\\Github\\ChatBuddy\\mcp-server
uv add langchain langchain-community langchain-huggingface langchain-text-splitters faiss-cpu pypdf python-dotenv
```

The Expense Tracker server also requires PostgreSQL connectivity through `psycopg`.

## Environment Variables

Create:

```text
mcp-server/.env
```

Example:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ChatBuddy-expense-tracker
DB_USER=postgres
DB_PASSWORD=your_password

STOCK_PRICE_API=your_alpha_vantage_key
WEATHER_API_KEY=your_openweather_key
CONVERSION_API_KEY=your_exchange_rate_key

HUGGINGFACEHUB_API_TOKEN=hf_xxxxxxxxxxxxxxxxx
```

Never commit API keys or passwords to GitHub. Add `.env` to `.gitignore`.

## Running ChatBuddy

```powershell
cd C:\\Github\\ChatBuddy\\mcp-client
uv run streamlit run client.py
```

The Streamlit application provides the ChatBuddy interface.

## How MCP Tool Calling Works

The client discovers tools from all configured MCP servers and binds them to Qwen.

```text
User
 |
 v
Qwen
 |
 +-- No tool required ----------------> Final Answer
 |
 +-- Tool required
       |
       v
   MCP Client
       |
       v
   MCP Server
       |
       v
   Tool Result
       |
       v
      Qwen
       |
       v
  Final Answer
```

The client continues the tool-calling loop until the model produces a final response.

## RAG Pipeline

The RAG implementation uses Hugging Face for embeddings and FAISS for local vector search.

```text
Uploaded PDF
     |
     v
PyPDFLoader
     |
     v
PDF Documents
     |
     v
RecursiveCharacterTextSplitter
     |
     v
Chunks
     |
     v
Hugging Face Embedding API
     |
     v
Embeddings
     |
     v
FAISS
     |
     v
Retriever
```

The embedding model is:

```text
sentence-transformers/all-MiniLM-L6-v2
```

The embedding computation is performed through the Hugging Face inference API instead of running the embedding model locally.

## Conversation-Specific Knowledge Bases

Each ChatBuddy conversation can have its own knowledge base.

```text
Thread A
 |
 +-- machine-learning.pdf
       |
       +-- FAISS Index A

Thread B
 |
 +-- database-notes.pdf
       |
       +-- FAISS Index B

Thread C
 |
 +-- No PDF
```

This prevents a document uploaded for one conversation from automatically becoming available in another conversation.

Knowledge-base metadata is persisted with the ChatBuddy application data, while FAISS indexes are persisted under `rag_data/`.

## Using PDF RAG

1. Start ChatBuddy.

```powershell
uv run streamlit run client.py
```

2. Create or select a conversation.

3. Use the **Knowledge Base** section in the sidebar.

4. Upload a PDF.

5. ChatBuddy loads and chunks the PDF, creates embeddings through Hugging Face, builds the FAISS index, and persists the knowledge base.

6. Ask a question such as:

```text
Using my uploaded PDF, explain how to find the ideal value of K in KNN.
```

The LLM can then call:

```text
rag_search
```

to retrieve relevant chunks before generating the answer.

## RAG Query Flow

```text
User Question
      |
      v
     Qwen
      |
      | decides RAG is required
      v
  rag_search()
      |
      v
 RAG MCP Server
      |
      v
 FAISS Retriever
      |
      v
Top relevant chunks
      |
      v
     Qwen
      |
      v
Final Answer
```

## Testing MCP Servers

Each MCP server can be tested independently using MCP Inspector before integrating it with ChatBuddy.

For the RAG server, the typical flow is:

```text
Start RAG MCP Server
        |
        v
Open MCP Inspector
        |
        v
index_pdf
        |
        v
Verify FAISS index creation
        |
        v
rag_search
        |
        v
Verify retrieved chunks
```

This makes it easier to distinguish MCP connectivity problems from RAG or retrieval problems.

## Expense Tracker

The Expense Tracker is implemented as an independent FastMCP server backed by PostgreSQL.

Available tools:

```text
add_expense
list_expenses
summarize_expenses
edit_expense
delete_expense
credit
```

The database connection is isolated in:

```text
mcp-server/db/connection.py
```

Conversation state and transaction data are intentionally kept separate:

```text
ChatBuddy SQLite
    |
    +-- Conversations
    +-- Messages
    +-- RAG metadata

PostgreSQL
    |
    +-- Expenses
    +-- Credits / Income
```

## Application Persistence

The client uses SQLite for application-level persistence.

Conceptually, it stores:

```text
conversations
+-- thread_id
+-- title
+-- created_at
+-- updated_at

messages
+-- id
+-- thread_id
+-- role
+-- content
+-- created_at

knowledge_bases
+-- thread_id
+-- filename
+-- file_path
+-- file_hash
+-- indexed
+-- pages
+-- chunks
```

This allows ChatBuddy to resume conversations and restore the corresponding knowledge-base metadata.

## Original LangGraph Version

ChatBuddy originally used LangGraph directly for orchestration.

The original implementation covered:

- `StateGraph`
- `ChatState`
- `add_messages`
- `ToolNode`
- `tools_condition`
- SQLite checkpointing
- LangSmith tracing
- Streaming
- Thread IDs
- Dynamic chat titles
- Direct application-local tools

The earlier architecture was:

```text
User
 |
 v
Streamlit
 |
 v
LangGraph StateGraph
 |
 v
Chat Node
 |
 +-- Direct Response ----------> Final Response
 |
 +-- Tool Required
        |
        v
     ToolNode
        |
        v
    Chat Node
        |
        v
   Final Response
```

The original LangGraph implementation represents the project's learning progression, while the current application uses MCP to expose capabilities as independent servers.

## Project Evolution

### Version 1 — Basic Chatbot
Initial conversational AI application.

### Version 2 — LangGraph
Added:
- StateGraph
- In-memory conversation state
- Conversation memory

### Version 3 — Streaming
Added:
- Streaming LLM responses
- Generator-based output

### Version 4 — Multi-thread Conversations
Added:
- Multiple conversations
- Thread IDs
- Resume previous chats
- Dynamic titles
- Conversation history

### Version 5 — SQLite Persistence
Added:
- SQLite checkpointing
- Persistent conversations
- Automatic thread retrieval

### Version 6 — LangSmith
Added:
- LangSmith tracing
- End-to-end observability
- Thread-specific monitoring
- LLM/tool debugging

### Version 7 — LangGraph Tool Calling
Added:
- ToolNode
- Conditional routing
- DuckDuckGo Search
- Calculator
- Weather
- Stock price
- Currency conversion
- Tool execution status

### Version 8 — MCP Architecture
Added:
- FastMCP
- MCP client
- MCP Inspector
- Independent MCP servers
- LangChain MCP adapters
- stdio transport
- Multi-server tool discovery

### Version 9 — Expense Tracker MCP
Added:
- PostgreSQL-backed Expense Tracker
- Add expense
- List expenses
- Summarize expenses
- Edit expense
- Delete expense
- Credit/income tracking

### Version 10 — RAG MCP
Added:
- PDF upload from Streamlit
- Conversation-specific knowledge bases
- PDF loading
- Recursive text splitting
- Hugging Face embedding API
- FAISS vector search
- Persistent indexes
- RAG MCP tools
- PDF question answering

## Key Concepts Learned

### LangGraph
- StateGraph
- State management
- Messages state
- Reducers
- `add_messages`
- Thread IDs
- Checkpointers
- ToolNode
- Conditional routing
- Streaming

### MCP
- MCP servers
- MCP clients
- FastMCP
- MCP tools
- stdio transport
- MCP Inspector
- Multi-server MCP clients
- Tool discovery
- Tool execution

### RAG
- PDF loading
- Document splitting
- Chunk size and overlap
- Embeddings
- Hugging Face inference
- Vector stores
- FAISS
- Similarity retrieval
- Conversation-scoped knowledge bases
- Retrieval as an MCP capability

### Application Engineering
- Streamlit
- SQLite persistence
- PostgreSQL
- Environment variables
- External API integration
- Thread-based application state
- Modular server architecture
- Error handling
- Tool execution status

## Design Principles

### 1. Separation of concerns

The UI, MCP client, MCP servers, databases, and RAG components have separate responsibilities.

### 2. Independent testing

MCP servers can be tested with MCP Inspector before connecting them to the main application.

### 3. Persistent state

Conversation and knowledge-base metadata survive application restarts.

### 4. Modular capabilities

A new capability can be introduced as an independent MCP server instead of tightly coupling it to the main client.

### 5. LLM-driven tool selection

The LLM determines when an available capability is relevant.

### 6. Conversation-scoped RAG

Uploaded documents are associated with individual conversations rather than one global knowledge base.

## Current Limitations

This is a learning and engineering project rather than a fully production-deployed platform.

Current areas for improvement include:

- Authentication and authorization
- Multi-user isolation
- Cloud object storage
- Distributed vector databases
- Hybrid retrieval
- Reranking
- RAG evaluation
- Citation-aware answers
- Background indexing
- Queue-based processing
- MCP tool observability
- Rate limiting
- Production deployment
- Horizontal scaling
- Automated end-to-end tests

## Future Improvements

Potential next steps:

- Hybrid retrieval: BM25 + dense retrieval
- Cross-encoder reranking
- RAG evaluation and retrieval metrics
- Multiple PDFs per conversation
- Document management
- Page-level citations
- Background document indexing
- Authentication
- PostgreSQL-backed application state
- Docker deployment
- Cloud deployment
- Kubernetes deployment
- MCP server observability
- Advanced LangGraph agent workflows
- Human-in-the-loop workflows
- Multi-agent systems

## Learning Outcome

ChatBuddy was deliberately built as an evolving system rather than a collection of unrelated demos.

The progression was:

```text
Basic Chatbot
      |
      v
LangGraph
      |
      v
State Management
      |
      v
Persistence
      |
      v
Multi-thread Conversations
      |
      v
Streaming
      |
      v
Observability
      |
      v
Tool Calling
      |
      v
MCP
      |
      v
Multiple MCP Servers
      |
      v
PostgreSQL Expense System
      |
      v
RAG
      |
      v
RAG exposed through MCP
```

The final architecture demonstrates how an AI application can evolve from a simple LLM interface into a modular system where reasoning, tools, external services, databases, and retrieval capabilities are separated into well-defined components.

## Repository

Explore the repository to see the complete evolution of the project from LangGraph fundamentals to a multi-server MCP application with RAG.

If you find the project useful, feel free to share feedback.

⭐ If you like the project, consider giving it a star!
"""
