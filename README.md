# ChatBuddy v5 - Persistent Multi-Thread Chatbot using LangGraph & SQLite

## Overview

**ChatBuddy v5** is the fifth iteration of my LangGraph learning journey. Starting from a basic chatbot, this version evolves into a **persistent multi-thread conversational assistant** capable of maintaining multiple chat sessions and restoring conversations even after the application restarts.

The primary goal of this version was to understand how **LangGraph Persistence** works in real-world applications using **SQLite Checkpointers**.

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
- LangSmith Tracing & Monitoring (Thread Specific)
- Tool Calling (Internet Search, Calculator, Live Stock Price, Weather Information, Currency Conversion).

---

## Tech Stack

- Python
- LangGraph
- LangChain
- Hugging Face Inference API
- Qwen3-4B-Instruct
- SQLite
- Streamlit

---

## Project Structure

```text
chatbot_v5/
│
├── frontend.py          # Streamlit UI
├── db_backend.py        # LangGraph workflow & SQLite persistence
├── chatbot.db           # SQLite checkpoint database
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
               Chat Node
                    │
                    ▼
        HuggingFace Qwen Model
                    │
                    ▼
             Assistant Response
                    │
                    ▼
      SQLite Checkpointer (Persistence)
                    │
                    ▼
         Resume Conversation Anytime
```

---

## Concepts Covered

### 1. LangGraph StateGraph

The chatbot is implemented using LangGraph's `StateGraph`, where the application state stores the entire conversation.

```python
class ChatState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
```

The `add_messages` reducer automatically appends new messages to the conversation state.

---

### 2. SQLite Persistence

Unlike previous versions that used `InMemorySaver`, this version uses `SqliteSaver`.

```python
conn = sqlite3.connect(
    database="chatbot.db",
    check_same_thread=False
)

checkPointer = SqliteSaver(conn)
```

Benefits:

- Conversations survive application restarts.
- Checkpoints are stored permanently.
- No loss of chat history.

---

### 3. Thread-Based Conversations

Every conversation receives its own unique thread ID.

```text
Thread A
 ├── User
 ├── AI
 ├── User
 └── AI

Thread B
 ├── User
 ├── AI
```

LangGraph restores the correct conversation automatically using:

```python
config = {
    "configurable": {
        "thread_id": thread_id
    }
}
```

---

### 4. Resume Chat

Users can reopen previous conversations directly from the sidebar.

The application restores the latest checkpoint using:

```python
chatBot.get_state(config)
```

instead of manually storing every conversation.

---

### 5. Streaming Responses

Instead of waiting for the complete response, the chatbot streams tokens in real time.

```python
chatBot.stream(...)
```

This creates a smoother experience similar to modern AI chat applications.

---

### 6. Automatic Thread Retrieval

Existing conversations are discovered directly from the SQLite checkpoint database.

```python
def retrieveAllThreads():
    allThreads = set()

    for checkpoint in checkPointer.list(None):
        allThreads.add(
            checkpoint.config["configurable"]["thread_id"]
        )

    return list(allThreads)
```

This allows all previous chats to appear automatically after restarting the application.

---

## Version Progression

### Version 2

- Built the first LangGraph chatbot.
- Introduced `InMemorySaver`.
- Learned thread-based conversation memory.

---

### Version 3

Added:

- Streaming responses.
- Generator-based output.
- Better user experience with real-time token generation.

---

### Version 4

Added:

- Multiple conversations.
- Resume chat.
- Dynamic thread IDs.
- Conversation history.
- Automatic chat titles.

---

### Version 5

Added:

- SQLite Checkpointer.
- Persistent conversations.
- Resume chat after application restart.
- Automatic retrieval of existing conversation threads.
- Production-style conversation management.

---

## What I Learned

This project helped me gain practical experience with:

- LangGraph StateGraph
- Messages State
- Reducers (`add_messages`)
- Checkpointers
- Thread IDs
- Persistence
- SQLite Checkpointer
- Streaming
- Resume Chat
- Multi-thread conversation management
- Streamlit Session State

---

## Future Improvements

- AI-generated conversation titles
- Rename/Delete chats
- User authentication
- PostgreSQL Checkpointer
- Tool Calling
- LangGraph Agents
- RAG Integration
- Human-in-the-Loop
- Model Context Protocol (MCP)

---

## Key Takeaways

Building this project helped me understand that **LangGraph Persistence** is much more than simply storing chat history.

It enables:

- Stateful AI applications
- Resume chat functionality
- Multiple concurrent conversations
- Fault tolerance
- Checkpoint management
- Production-ready conversational systems

Rather than building everything at once, I evolved the chatbot across multiple versions, with each version introducing a new LangGraph capability. This incremental approach made it much easier to understand not only **how** these features work, but also **why** they matter when designing real-world AI applications.

---

## Repository

If you found this project useful, feel free to explore the repository and share your feedback.

 If you like the project, consider giving it a star!
