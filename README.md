# ChatBuddy 🫂

## Overview

ChatBuddy is a conversational AI assistant built using **LangGraph**, evolving step by step from a basic chatbot into a more capable, production-style application.

The project explores core LangGraph concepts including state management, persistence, streaming, multi-thread conversations, observability with LangSmith, and Tool Calling. Instead of building isolated demos, every new concept is integrated into the same application to better understand how real-world AI systems evolve over time.

---

## Features

- Multi-thread conversations
- Persistent chat history using SQLite
- Resume previous conversations
- Automatic checkpoint management using LangGraph
- Streaming LLM responses
- Dynamic chat titles
- Streamlit-based chat interface
- Thread management using LangGraph Thread IDs
- LangSmith Tracing & Monitoring
- LangGraph Tool Calling
- DuckDuckGo Internet Search
- Calculator Tool
- Live Weather Information
- Live Stock Price Lookup
- Currency Conversion
- Tool execution status indicator in the UI
- Clean streaming of only the final LLM response

---

## Tech Stack

- Python
- LangGraph
- LangChain
- Hugging Face Inference API
- Qwen3-4B-Instruct
- SQLite
- Streamlit
- LangSmith
- DuckDuckGo Search
- OpenWeather API
- Alpha Vantage API
- ExchangeRate API

---

## Project Structure

```text
chatbuddy/
│
├── frontend.py          # Streamlit Frontend
├── backend.py           # LangGraph Workflow
├── chatbot.db           # SQLite Checkpoint Database
├── requirements.txt
└── README.md
```

---

## Architecture

```text
                           User
                             │
                             ▼
                    Streamlit Frontend
                             │
                             ▼
                      LangGraph Graph
                             │
                             ▼
                       Chat Node (LLM)
                             │
                ┌────────────┴────────────┐
                │                         │
        Direct Response          Tool Required?
                │                         │
                │                        Yes
                │                         │
                ▼                         ▼
           Final Response            Tool Node
                                          │
      ┌──────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
      ▼              ▼              ▼              ▼              ▼
  DuckDuckGo     Calculator      Weather      Stock Price    Currency Converter
      │              │              │              │              │
      └──────────────┴──────────────┴──────────────┴──────────────┘
                             │
                             ▼
                        Chat Node (LLM)
                             │
                             ▼
                      Final AI Response
                             │
                             ▼
                 SQLite Checkpointer
                             │
                             ▼
                 Resume Conversation Anytime
```

---

# Concepts Covered

## 1. LangGraph StateGraph

ChatBuddy is built using LangGraph's `StateGraph`, where the application state stores the complete conversation.

```python
class ChatState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
```

The `add_messages` reducer automatically appends new messages to the conversation state.

---

## 2. SQLite Persistence

ChatBuddy uses `SqliteSaver` to persist every conversation checkpoint.

```python
checkPointer = SqliteSaver(conn)
```

Benefits:

- Persistent conversations
- Resume after restart
- Automatic checkpoint management
- Production-style state persistence

---

## 3. Thread-Based Conversations

Each conversation is assigned a unique LangGraph Thread ID.

Using the thread ID, LangGraph automatically restores the correct conversation state.

```python
config = {
    "configurable": {
        "thread_id": thread_id
    }
}
```

---

## 4. Streaming Responses

Responses are streamed token by token using LangGraph's streaming API.

```python
chatBot.stream(...)
```

This provides a smoother, real-time chat experience.

---

## 5. LangGraph Tool Calling

ChatBuddy uses LangGraph's `ToolNode` together with conditional routing to decide whether a user query should invoke a tool or be answered directly by the LLM.

```python
graph.add_conditional_edges(
    "chatNode",
    tools_condition
)
```

The model is connected to available tools using:

```python
model.bind_tools(tools)
```

Current tools include:

- DuckDuckGo Search
- Calculator
- Weather Information
- Stock Price Lookup
- Currency Converter

---

## 6. Conditional Graph Routing

Instead of following a fixed workflow, the graph dynamically decides the execution path.

```
User Question
      │
      ▼
  Chat Node
      │
      ├── Normal Question
      │        │
      │        ▼
      │   Final Response
      │
      └── Tool Required
               │
               ▼
          Tool Node
               │
               ▼
          Chat Node
               │
               ▼
        Final Response
```

---

## 7. LangSmith Observability

LangSmith is integrated to trace every conversation and visualize:

- LLM calls
- Tool execution
- Latency
- Tokens
- Execution flow
- Thread-specific traces

This makes debugging and monitoring significantly easier.

---

## Version Progression

### Version 2

- Basic LangGraph chatbot
- InMemorySaver
- Conversation memory

---

### Version 3

Added:

- Streaming responses
- Generator-based output

---

### Version 4

Added:

- Multi-thread conversations
- Resume chat
- Dynamic chat titles
- Conversation history

---

### Version 5

Added:

- SQLite Checkpointer
- Persistent conversations
- Automatic thread retrieval

---

### Version 6

Added:

- LangSmith integration
- End-to-end tracing
- Thread-specific monitoring
- Better debugging and observability

---

### Version 7

Added:

- LangGraph Tool Calling
- ToolNode
- Conditional graph routing
- DuckDuckGo Search
- Calculator
- Weather Tool
- Stock Price Tool
- Currency Converter
- Tool execution status indicator
- Streaming only the final AI response

---

## What I Learned

Building ChatBuddy helped me gain hands-on experience with:

- LangGraph StateGraph
- Messages State
- Reducers (`add_messages`)
- Thread IDs
- Checkpointers
- SQLite Persistence
- Streaming
- Multi-thread conversations
- LangSmith Observability
- Tool Calling
- Conditional Routing
- ToolNode
- Streamlit Session State
- Building a stateful AI application incrementally

---

## Future Improvements

- Model Context Protocol (MCP)
- LangGraph Agents
- Human-in-the-Loop Workflows
- Multi-Agent Systems
- User Authentication
- Rename/Delete Chats
- PostgreSQL Checkpointer
- Docker Deployment
- Cloud Deployment

---

## Key Takeaways

Rather than building separate demos for each LangGraph concept, I chose to evolve a single application across multiple versions.

Each version introduced one new capability—from conversation memory and persistence to observability and Tool Calling—making it easier to understand how these concepts fit together when building real-world AI applications.

The project continues to evolve, with **Model Context Protocol (MCP)** being the next major addition.

---

## Repository

If you found this project useful, feel free to explore the repository and share your feedback.

⭐ If you like the project, consider giving it a star!
