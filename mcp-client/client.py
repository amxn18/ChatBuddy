import asyncio
import hashlib
import json
import os
import shutil
import sqlite3
import uuid
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_mcp_adapters.client import MultiServerMCPClient


load_dotenv()


# ============================================================
# Paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MCP_SERVER_DIR = PROJECT_ROOT / "mcp-server"

DATABASE_PATH = PROJECT_ROOT / "chatbuddy_mcp.db"
UPLOAD_DIR = PROJECT_ROOT / "rag_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# UV
# ============================================================

UV_PATH = shutil.which("uv")

if UV_PATH is None:
    default_uv_path = (
        Path.home()
        / "AppData"
        / "Local"
        / "Programs"
        / "Python"
        / "Python311"
        / "Scripts"
        / "uv.exe"
    )

    if default_uv_path.exists():
        UV_PATH = str(default_uv_path)
    else:
        UV_PATH = "uv"


# ============================================================
# MCP Servers
# ============================================================

def server_config(server_file: str) -> dict:
    return {
        "transport": "stdio",
        "command": UV_PATH,
        "args": [
            "run",
            "--directory",
            str(MCP_SERVER_DIR),
            "fastmcp",
            "run",
            server_file,
        ],
    }


SERVERS = {
    "math": server_config("arithmetic-server.py"),
    "search": server_config("search-server.py"),
    "stock": server_config("stock-server.py"),
    "weather": server_config("weather-server.py"),
    "currency": server_config("currency-server.py"),
    "expense": server_config("expense-tracker-server.py"),
    "rag": server_config("rag-server.py"),
}


# ============================================================
# System Prompt
# ============================================================

SYSTEM_PROMPT = """
You are ChatBuddy, a helpful AI assistant with access to multiple
MCP servers and tools.

Use MCP tools whenever they are appropriate for the user's request.

Available capabilities include:
- Arithmetic calculations
- Web search
- Stock prices
- Weather information
- Currency conversion
- Expense and income management
- Searching the user's currently indexed PDF knowledge base

For expense-related requests, use the Expense Tracker MCP tools.

For questions that are clearly about the currently indexed PDF,
use the RAG search tool. If no PDF is indexed, answer normally
and do not pretend that you searched a document.

Use the information returned by tools as evidence. Do not invent
information that can be obtained using an available tool.

Do not narrate internal tool execution.
Do not explain that you are "calling a tool".

After completing the necessary tool calls, provide a concise and
helpful final answer to the user.
"""


# ============================================================
# Streamlit setup
# ============================================================

st.set_page_config(
    page_title="ChatBuddy 🫂",
    page_icon="🫂",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("ChatBuddy 🫂")


# ============================================================
# SQLite
# ============================================================

def get_db_connection():
    conn = sqlite3.connect(
        DATABASE_PATH,
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            thread_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(thread_id)
                REFERENCES conversations(thread_id)
                ON DELETE CASCADE
        )
        """
    )

    # One PDF knowledge base per ChatBuddy thread.
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS knowledge_bases (
            thread_id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_hash TEXT NOT NULL,
            indexed INTEGER NOT NULL DEFAULT 0,
            pages INTEGER,
            chunks INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(thread_id)
                REFERENCES conversations(thread_id)
                ON DELETE CASCADE
        )
        """
    )

    conn.commit()
    conn.close()


initialize_database()


# ============================================================
# Conversation helpers
# ============================================================

def create_thread(thread_id: str, title: str = "New Chat"):
    conn = get_db_connection()

    conn.execute(
        """
        INSERT OR IGNORE INTO conversations
        (thread_id, title)
        VALUES (?, ?)
        """,
        (thread_id, title),
    )

    conn.commit()
    conn.close()


def update_thread_title(thread_id: str, title: str):
    conn = get_db_connection()

    conn.execute(
        """
        UPDATE conversations
        SET title = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE thread_id = ?
        """,
        (title, thread_id),
    )

    conn.commit()
    conn.close()


def save_message(thread_id: str, role: str, content: str):
    conn = get_db_connection()

    conn.execute(
        """
        INSERT INTO messages
        (thread_id, role, content)
        VALUES (?, ?, ?)
        """,
        (thread_id, role, content),
    )

    conn.execute(
        """
        UPDATE conversations
        SET updated_at = CURRENT_TIMESTAMP
        WHERE thread_id = ?
        """,
        (thread_id,),
    )

    conn.commit()
    conn.close()


def get_all_threads():
    conn = get_db_connection()

    rows = conn.execute(
        """
        SELECT thread_id, title
        FROM conversations
        ORDER BY updated_at DESC
        """
    ).fetchall()

    conn.close()

    return [
        {
            "thread_id": row["thread_id"],
            "title": row["title"],
        }
        for row in rows
    ]


def get_thread_messages(thread_id: str):
    conn = get_db_connection()

    rows = conn.execute(
        """
        SELECT role, content
        FROM messages
        WHERE thread_id = ?
        ORDER BY id ASC
        """,
        (thread_id,),
    ).fetchall()

    conn.close()

    return [
        {
            "role": row["role"],
            "content": row["content"],
        }
        for row in rows
    ]


def delete_thread_messages(thread_id: str):
    conn = get_db_connection()

    conn.execute(
        """
        DELETE FROM messages
        WHERE thread_id = ?
        """,
        (thread_id,),
    )

    conn.commit()
    conn.close()


# ============================================================
# Knowledge-base helpers
# ============================================================

def get_knowledge_base(thread_id: str):
    conn = get_db_connection()

    row = conn.execute(
        """
        SELECT thread_id, filename, file_path, file_hash,
               indexed, pages, chunks
        FROM knowledge_bases
        WHERE thread_id = ?
        """,
        (thread_id,),
    ).fetchone()

    conn.close()

    if row is None:
        return None

    return dict(row)


def save_knowledge_base(
    thread_id: str,
    filename: str,
    file_path: str,
    file_hash: str,
    indexed: bool,
    pages: int | None = None,
    chunks: int | None = None,
):
    conn = get_db_connection()

    conn.execute(
        """
        INSERT INTO knowledge_bases
        (
            thread_id,
            filename,
            file_path,
            file_hash,
            indexed,
            pages,
            chunks
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(thread_id)
        DO UPDATE SET
            filename = excluded.filename,
            file_path = excluded.file_path,
            file_hash = excluded.file_hash,
            indexed = excluded.indexed,
            pages = excluded.pages,
            chunks = excluded.chunks,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            thread_id,
            filename,
            file_path,
            file_hash,
            int(indexed),
            pages,
            chunks,
        ),
    )

    conn.commit()
    conn.close()


def delete_knowledge_base(thread_id: str):
    kb = get_knowledge_base(thread_id)

    conn = get_db_connection()
    conn.execute(
        """
        DELETE FROM knowledge_bases
        WHERE thread_id = ?
        """,
        (thread_id,),
    )
    conn.commit()
    conn.close()

    # Delete the uploaded PDF from the client side.
    if kb:
        file_path = Path(kb["file_path"])
        if file_path.exists():
            try:
                file_path.unlink()
            except OSError:
                pass

    # The MCP RAG server stores the FAISS index under:
    # mcp-server/rag_data/<thread_id>
    rag_index_dir = MCP_SERVER_DIR / "rag_data" / thread_id

    if rag_index_dir.exists():
        shutil.rmtree(rag_index_dir, ignore_errors=True)


def save_uploaded_pdf(uploaded_file, thread_id: str) -> tuple[Path, str]:
    """
    Save the Streamlit UploadedFile to a stable local path and
    return (path, sha256 hash).
    """

    thread_upload_dir = UPLOAD_DIR / thread_id
    thread_upload_dir.mkdir(parents=True, exist_ok=True)

    file_bytes = uploaded_file.getvalue()
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    # Always use a safe generated filename.
    file_path = thread_upload_dir / "document.pdf"
    file_path.write_bytes(file_bytes)

    return file_path, file_hash


# ============================================================
# Thread state
# ============================================================

def generate_thread_id():
    return str(uuid.uuid4())


def create_new_chat():
    thread_id = generate_thread_id()

    create_thread(thread_id, "New Chat")

    st.session_state["thread_id"] = thread_id
    st.session_state["message_history"] = []


def load_chat(thread_id: str):
    st.session_state["thread_id"] = thread_id
    st.session_state["message_history"] = get_thread_messages(thread_id)


if "thread_id" not in st.session_state:
    existing_threads = get_all_threads()

    if existing_threads:
        st.session_state["thread_id"] = existing_threads[0]["thread_id"]
        st.session_state["message_history"] = get_thread_messages(
            existing_threads[0]["thread_id"]
        )
    else:
        create_new_chat()


if "message_history" not in st.session_state:
    st.session_state["message_history"] = []


# ============================================================
# MCP result helpers
# ============================================================

def extract_mcp_text(result) -> str:
    """Extract plain text from LangChain MCP adapter tool results."""

    if result is None:
        return ""

    if isinstance(result, str):
        return result

    if isinstance(result, dict):
        # FastMCP/LangChain MCP adapters may return:
        # {"type": "text", "text": "...", ...}
        if isinstance(result.get("text"), str):
            return result["text"]

        # Some versions wrap content in a list.
        content = result.get("content")
        if content is not None:
            return extract_mcp_text(content)

        return str(result)

    if isinstance(result, list):
        parts = [extract_mcp_text(item) for item in result]
        return "\n".join(part for part in parts if part)

    # Handle object-style results that expose .text or .content.
    result_text = getattr(result, "text", None)
    if isinstance(result_text, str):
        return result_text

    result_content = getattr(result, "content", None)
    if result_content is not None:
        return extract_mcp_text(result_content)

    return str(result)


# ============================================================
# MCP helpers
# ============================================================

async def get_mcp_tools():
    client = MultiServerMCPClient(SERVERS)
    return await client.get_tools()


async def index_pdf_with_mcp(
    pdf_path: str,
    thread_id: str,
) -> str:
    """
    Call only the RAG MCP server's index_pdf tool.
    """

    client = MultiServerMCPClient(
        {
            "rag": SERVERS["rag"],
        }
    )

    tools = await client.get_tools()

    index_tool = next(
        (tool for tool in tools if tool.name == "index_pdf"),
        None,
    )

    if index_tool is None:
        raise RuntimeError(
            "RAG MCP server does not expose the `index_pdf` tool."
        )

    result = await index_tool.ainvoke(
        {
            "pdf_path": pdf_path,
            "knowledge_base_id": thread_id,
        }
    )

    return extract_mcp_text(result)


async def remove_pdf_with_mcp(thread_id: str):
    """
    Ask the RAG MCP server to remove the persistent index.
    """

    client = MultiServerMCPClient(
        {
            "rag": SERVERS["rag"],
        }
    )

    tools = await client.get_tools()

    remove_tool = next(
        (tool for tool in tools if tool.name == "remove_knowledge_base"),
        None,
    )

    if remove_tool is not None:
        await remove_tool.ainvoke(
            {
                "knowledge_base_id": thread_id,
            }
        )


# ============================================================
# RAG tool wrapper
# ============================================================

def create_rag_search_tool(mcp_rag_tool, thread_id: str):
    """
    Create a client-side wrapper around the MCP rag_search tool.

    The LLM only sees:
        rag_search(query)

    The wrapper automatically injects the current ChatBuddy
    thread's knowledge_base_id before calling the real MCP tool.
    """

    @tool("rag_search")
    async def rag_search(query: str) -> str:
        """
        Search the PDF currently indexed for this ChatBuddy conversation.

        Use this when the user's question should be answered from
        the uploaded PDF.
        """

        result = await mcp_rag_tool.ainvoke(
            {
                "query": query,
                "knowledge_base_id": thread_id,
            }
        )

        return extract_mcp_text(result)

    return rag_search


# ============================================================
# Chat processing
# ============================================================

def normalize_message_content(content) -> str:
    if content is None:
        return ""

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []

        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                if "text" in item:
                    parts.append(str(item["text"]))
                elif "content" in item:
                    parts.append(str(item["content"]))

        if parts:
            return "\n".join(parts)

    return str(content)


async def process_message(
    user_text: str,
    status_container,
    thread_id: str,
):
    """
    Process one user message.

    Flow:

    User
      ↓
    Qwen
      ↓
    MCP tool call?
      ↓
    MCP server
      ↓
    Tool result
      ↓
    Qwen
      ↓
    Final answer
    """

    client = MultiServerMCPClient(SERVERS)
    mcp_tools = await client.get_tools()

    tool_by_name = {
        tool.name: tool
        for tool in mcp_tools
    }

    # --------------------------------------------------------
    # Replace the raw MCP RAG tool with a thread-aware wrapper.
    # index_pdf is intentionally NOT exposed to the LLM.
    # --------------------------------------------------------

    model_tools = []

    for mcp_tool in mcp_tools:
        if mcp_tool.name == "index_pdf":
            continue

        if mcp_tool.name == "rag_search":
            continue

        model_tools.append(mcp_tool)

    raw_rag_tool = tool_by_name.get("rag_search")

    if raw_rag_tool is not None:
        current_kb = get_knowledge_base(thread_id)

        if current_kb and current_kb["indexed"]:
            model_tools.append(
                create_rag_search_tool(
                    raw_rag_tool,
                    thread_id,
                )
            )

    # --------------------------------------------------------
    # Model
    # --------------------------------------------------------

    llm = HuggingFaceEndpoint(
        repo_id="Qwen/Qwen3-4B-Instruct-2507",
        task="text-generation",
    )

    model = ChatHuggingFace(llm=llm)

    model_with_tools = model.bind_tools(model_tools)

    # --------------------------------------------------------
    # Reconstruct conversation
    # --------------------------------------------------------

    messages = [
        SystemMessage(content=SYSTEM_PROMPT)
    ]

    for message in st.session_state["message_history"]:
        if message["role"] == "user":
            messages.append(
                HumanMessage(
                    content=message["content"]
                )
            )

        elif message["role"] == "assistant":
            messages.append(
                AIMessage(
                    content=message["content"]
                )
            )

    messages.append(
        HumanMessage(content=user_text)
    )

    # --------------------------------------------------------
    # Tool calling loop
    # --------------------------------------------------------

    while True:

        response = await model_with_tools.ainvoke(messages)

        tool_calls = getattr(
            response,
            "tool_calls",
            None,
        )

        if not tool_calls:
            return response

        messages.append(response)

        for tool_call in tool_calls:

            tool_name = tool_call["name"]

            tool_args = tool_call.get("args") or {}

            tool_call_id = tool_call["id"]

            status_container.update(
                label=f"Using `{tool_name}` ...",
                state="running",
                expanded=True,
            )

            if isinstance(tool_args, str):
                try:
                    tool_args = json.loads(tool_args)
                except json.JSONDecodeError:
                    tool_args = {}

            selected_tool = {
                tool.name: tool
                for tool in model_tools
            }.get(tool_name)

            if selected_tool is None:
                tool_result = (
                    f"Error: MCP tool `{tool_name}` was not found."
                )
            else:
                try:
                    tool_result = await selected_tool.ainvoke(
                        tool_args
                    )

                except Exception as e:
                    tool_result = (
                        f"Error executing `{tool_name}`: {str(e)}"
                    )

            if isinstance(tool_result, str):
                tool_content = tool_result
            else:
                try:
                    tool_content = json.dumps(
                        tool_result,
                        default=str,
                    )
                except Exception:
                    tool_content = str(tool_result)

            messages.append(
                ToolMessage(
                    tool_call_id=tool_call_id,
                    content=tool_content,
                )
            )


# ============================================================
# Sidebar
# ============================================================

with st.sidebar:

    st.title("ChatBuddy 🫂")

    if st.button(
        "➕ New Chat",
        use_container_width=True,
    ):
        create_new_chat()
        st.rerun()

    st.divider()

    # --------------------------------------------------------
    # Knowledge Base
    # --------------------------------------------------------

    st.subheader("📚 Knowledge Base")

    current_thread = st.session_state["thread_id"]
    current_kb = get_knowledge_base(current_thread)

    if current_kb and current_kb["indexed"]:
        st.success(
            f"📄 {current_kb['filename']}"
        )

        if current_kb["pages"] is not None:
            st.caption(
                f"{current_kb['pages']} pages • "
                f"{current_kb['chunks']} chunks"
            )

        if st.button(
            "🗑️ Remove PDF",
            use_container_width=True,
        ):
            with st.spinner("Removing PDF knowledge base..."):
                try:
                    asyncio.run(
                        remove_pdf_with_mcp(current_thread)
                    )
                except Exception:
                    # Local cleanup still happens below.
                    pass

                delete_knowledge_base(current_thread)

            st.rerun()

    else:
        st.info("No PDF indexed yet.")

        st.caption("Upload a PDF for this chat")

        uploaded_pdf = st.file_uploader(
            "Upload PDF",
            type=["pdf"],
            key=f"pdf_uploader_{current_thread}",
            label_visibility="collapsed",
        )

        if uploaded_pdf is not None:

            file_bytes = uploaded_pdf.getvalue()
            file_hash = hashlib.sha256(file_bytes).hexdigest()

            # Prevent Streamlit reruns from indexing the same file
            # repeatedly.
            already_indexed = (
                current_kb is not None
                and current_kb["file_hash"] == file_hash
                and current_kb["indexed"] == 1
            )

            if not already_indexed:

                with st.spinner(
                    "Indexing PDF with the RAG MCP server..."
                ):

                    try:
                        pdf_path, saved_hash = save_uploaded_pdf(
                            uploaded_pdf,
                            current_thread,
                        )

                        result = asyncio.run(
                            index_pdf_with_mcp(
                                str(pdf_path),
                                current_thread,
                            )
                        )

                        result_text = extract_mcp_text(result)

                        # The RAG server returns pages/chunks in its
                        # success message. Store them if available.
                        pages = None
                        chunks = None

                        for line in result_text.splitlines():
                            lower_line = line.lower()

                            if lower_line.startswith("pages:"):
                                try:
                                    pages = int(
                                        line.split(":", 1)[1].strip()
                                    )
                                except ValueError:
                                    pass

                            elif lower_line.startswith("chunks:"):
                                try:
                                    chunks = int(
                                        line.split(":", 1)[1].strip()
                                    )
                                except ValueError:
                                    pass

                        if not result_text.lower().startswith("successfully"):
                            raise RuntimeError(result_text)

                        save_knowledge_base(
                            thread_id=current_thread,
                            filename=uploaded_pdf.name,
                            file_path=str(pdf_path),
                            file_hash=saved_hash,
                            indexed=True,
                            pages=pages,
                            chunks=chunks,
                        )

                        st.rerun()

                    except Exception as e:
                        st.error(
                            f"PDF indexing failed: {str(e)}"
                        )

    st.divider()

    # --------------------------------------------------------
    # MCP Servers
    # --------------------------------------------------------

    st.subheader("MCP Servers")

    st.success("🔢 Math")
    st.success("🔎 Search")
    st.success("📈 Stock")
    st.success("🌤️ Weather")
    st.success("💱 Currency")
    st.success("💰 Expense")
    st.success("📚 RAG")

    st.divider()

    # --------------------------------------------------------
    # Conversation history
    # --------------------------------------------------------

    st.subheader("Conversation History")

    threads = get_all_threads()

    for thread in threads:

        thread_id = thread["thread_id"]
        title = thread["title"]

        if st.button(
            title,
            key=f"thread_{thread_id}",
            use_container_width=True,
        ):
            load_chat(thread_id)
            st.rerun()

    st.divider()

    if st.button(
        "🗑️ Clear Current Chat",
        use_container_width=True,
    ):

        current_thread = st.session_state["thread_id"]

        delete_thread_messages(current_thread)

        st.session_state["message_history"] = []

        st.rerun()


# ============================================================
# Display conversation
# ============================================================

for message in st.session_state["message_history"]:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# ============================================================
# Chat input
# ============================================================

user_input = st.chat_input(
    "Type your message..."
)


if user_input:

    current_thread = st.session_state["thread_id"]

    # --------------------------------------------------------
    # Generate title for first message
    # --------------------------------------------------------

    threads = get_all_threads()

    current_thread_data = next(
        (
            thread
            for thread in threads
            if thread["thread_id"] == current_thread
        ),
        None,
    )

    if (
        current_thread_data
        and current_thread_data["title"] == "New Chat"
    ):

        title = (
            user_input[:40] + "..."
            if len(user_input) > 40
            else user_input
        )

        update_thread_title(
            current_thread,
            title,
        )

    # --------------------------------------------------------
    # Display user message
    # --------------------------------------------------------

    with st.chat_message("user"):
        st.markdown(user_input)

    # --------------------------------------------------------
    # Save user message
    # --------------------------------------------------------

    save_message(
        current_thread,
        "user",
        user_input,
    )

    st.session_state["message_history"].append(
        {
            "role": "user",
            "content": user_input,
        }
    )

    # --------------------------------------------------------
    # Assistant response
    # --------------------------------------------------------

    with st.chat_message("assistant"):

        status_box = st.status(
            "Thinking...",
            expanded=False,
        )

        final_content = ""

        try:

            final_response = asyncio.run(
                process_message(
                    user_input,
                    status_box,
                    current_thread,
                )
            )

            status_box.update(
                label="MCP tools finished",
                state="complete",
                expanded=False,
            )

            final_content = normalize_message_content(
                final_response.content
            )

            st.markdown(final_content)

        except Exception as e:

            status_box.update(
                label="Error",
                state="error",
                expanded=True,
            )

            final_content = (
                "Sorry, something went wrong:\n\n"
                f"`{str(e)}`"
            )

            st.error(final_content)

    # --------------------------------------------------------
    # Save assistant response
    # --------------------------------------------------------

    save_message(
        current_thread,
        "assistant",
        final_content,
    )

    st.session_state["message_history"].append(
        {
            "role": "assistant",
            "content": final_content,
        }
    )
