import asyncio
import json
import os
import shutil
import sqlite3
import uuid
from pathlib import Path

import streamlit as st

from dotenv import load_dotenv

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_mcp_adapters.client import MultiServerMCPClient


load_dotenv()


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MCP_SERVER_DIR = PROJECT_ROOT / "mcp-server"

DATABASE_PATH = PROJECT_ROOT / "chatbuddy_mcp.db"

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


SERVERS = {
    "math": {
        "transport": "stdio",
        "command": UV_PATH,
        "args": [
            "run",
            "--directory",
            str(MCP_SERVER_DIR),
            "fastmcp",
            "run",
            "arithmetic-server.py",
        ],
    },
    "search": {
        "transport": "stdio",
        "command": UV_PATH,
        "args": [
            "run",
            "--directory",
            str(MCP_SERVER_DIR),
            "fastmcp",
            "run",
            "search-server.py",
        ],
    },
    "stock": {
        "transport": "stdio",
        "command": UV_PATH,
        "args": [
            "run",
            "--directory",
            str(MCP_SERVER_DIR),
            "fastmcp",
            "run",
            "stock-server.py",
        ],
    },
    "weather": {
        "transport": "stdio",
        "command": UV_PATH,
        "args": [
            "run",
            "--directory",
            str(MCP_SERVER_DIR),
            "fastmcp",
            "run",
            "weather-server.py",
        ],
    },
    "currency": {
        "transport": "stdio",
        "command": UV_PATH,
        "args": [
            "run",
            "--directory",
            str(MCP_SERVER_DIR),
            "fastmcp",
            "run",
            "currency-server.py",
        ],
    },
    "expense": {
        "transport": "stdio",
        "command": UV_PATH,
        "args": [
            "run",
            "--directory",
            str(MCP_SERVER_DIR),
            "fastmcp",
            "run",
            "expense-tracker-server.py",
        ],
    },
}

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

For expense-related requests, use the Expense Tracker MCP tools.

Do not invent information that can be obtained using an available tool.

Do not narrate internal tool execution.
Do not explain that you are "calling a tool".

After completing the necessary tool calls, provide a concise and
helpful final answer to the user.
"""

st.set_page_config(page_title="ChatBuddy 🫂",page_icon="🫂",layout="wide",initial_sidebar_state="expanded")


st.title("ChatBuddy 🫂")

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH,check_same_thread=False)
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
    conn.commit()
    conn.close()


initialize_database()
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

def update_thread_title(thread_id: str,title: str):
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

def touch_thread(thread_id: str):
    conn = get_db_connection()
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


def save_message(thread_id: str,role: str,content: str):
    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO messages
        (thread_id, role, content)
        VALUES (?, ?, ?)
        """,
        (
            thread_id,
            role,
            content,
        ),
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


def generate_thread_id():

    return str(uuid.uuid4())


def create_new_chat():

    thread_id = generate_thread_id()

    create_thread(
        thread_id,
        "New Chat",
    )

    st.session_state["thread_id"] = thread_id
    st.session_state["message_history"] = []


def load_chat(thread_id: str):

    messages = get_thread_messages(thread_id)

    st.session_state["thread_id"] = thread_id
    st.session_state["message_history"] = messages


if "thread_id" not in st.session_state:

    existing_threads = get_all_threads()

    if existing_threads:

        st.session_state["thread_id"] = (
            existing_threads[0]["thread_id"]
        )

        st.session_state["message_history"] = (
            get_thread_messages(
                existing_threads[0]["thread_id"]
            )
        )

    else:

        create_new_chat()


if "message_history" not in st.session_state:

    st.session_state["message_history"] = []


with st.sidebar:

    st.title("ChatBuddy 🫂")

    if st.button(
        "➕ New Chat",
        use_container_width=True,
    ):

        create_new_chat()

        st.rerun()

    st.divider()

    st.subheader("MCP Servers")

    st.success("🔢 Math")
    st.success("🔎 Search")
    st.success("📈 Stock")
    st.success("🌤️ Weather")
    st.success("💱 Currency")
    st.success("💰 Expense")

    st.divider()

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

        delete_thread_messages(
            current_thread
        )

        st.session_state["message_history"] = []

        st.rerun()


for message in st.session_state["message_history"]:

    with st.chat_message(
        message["role"]
    ):

        st.markdown(
            message["content"]
        )


async def process_message(
    user_text: str,
    status_container,
):
    """
    Process one user message.

    Flow:

    User
      ↓
    LLM
      ↓
    MCP tool call?
      ↓
    MCP Server
      ↓
    Tool result
      ↓
    LLM
      ↓
    Final answer

    The loop continues until the LLM stops
    requesting tools.
    """

    client = MultiServerMCPClient(
        SERVERS
    )

    tools = await client.get_tools()

    tool_by_name = {
        tool.name: tool
        for tool in tools
    }


    llm = HuggingFaceEndpoint(
        repo_id="Qwen/Qwen3-4B-Instruct-2507",
        task="text-generation",
    )

    model = ChatHuggingFace(
        llm=llm
    )

    model_with_tools = model.bind_tools(
        tools
    )



    messages = [
        SystemMessage(
            content=SYSTEM_PROMPT
        )
    ]

    for message in st.session_state[
        "message_history"
    ]:

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

    # --------------------------------------------------------
    # Add current user message
    # --------------------------------------------------------

    messages.append(
        HumanMessage(
            content=user_text
        )
    )

    # --------------------------------------------------------
    # Tool calling loop
    # --------------------------------------------------------

    while True:

        response = await model_with_tools.ainvoke(
            messages
        )

        tool_calls = getattr(
            response,
            "tool_calls",
            None,
        )

        # ----------------------------------------------------
        # No tool call = final answer
        # ----------------------------------------------------

        if not tool_calls:

            return response

        # ----------------------------------------------------
        # Add AI tool-call message
        # ----------------------------------------------------

        messages.append(
            response
        )

        # ----------------------------------------------------
        # Execute every requested MCP tool
        # ----------------------------------------------------

        for tool_call in tool_calls:

            tool_name = tool_call[
                "name"
            ]

            tool_args = (
                tool_call.get("args")
                or {}
            )

            tool_call_id = tool_call[
                "id"
            ]

            # -----------------------------------------------
            # Display tool status
            # -----------------------------------------------

            status_container.update(
                label=f"Using `{tool_name}` ...",
                state="running",
                expanded=True,
            )

            # -----------------------------------------------
            # Parse arguments if necessary
            # -----------------------------------------------

            if isinstance(
                tool_args,
                str,
            ):

                try:

                    tool_args = json.loads(
                        tool_args
                    )

                except json.JSONDecodeError:

                    pass

            # -----------------------------------------------
            # Find MCP tool
            # -----------------------------------------------

            selected_tool = tool_by_name.get(
                tool_name
            )

            if selected_tool is None:

                tool_result = (
                    f"Error: MCP tool "
                    f"`{tool_name}` was not found."
                )

            else:

                try:

                    tool_result = (
                        await selected_tool.ainvoke(
                            tool_args
                        )
                    )

                except Exception as e:

                    tool_result = (
                        f"Error executing "
                        f"`{tool_name}`: {str(e)}"
                    )

            # -----------------------------------------------
            # Convert result into message content
            # -----------------------------------------------

            if isinstance(
                tool_result,
                str,
            ):

                tool_content = tool_result

            else:

                try:

                    tool_content = json.dumps(
                        tool_result,
                        default=str,
                    )

                except Exception:

                    tool_content = str(
                        tool_result
                    )

            # -----------------------------------------------
            # Add MCP result to conversation
            # -----------------------------------------------

            messages.append(
                ToolMessage(
                    tool_call_id=tool_call_id,
                    content=tool_content,
                )
            )

        # ----------------------------------------------------
        # Loop back to LLM
        # ----------------------------------------------------
        #
        # The LLM now receives the MCP tool results
        # and decides whether:
        #
        # 1. Another tool is needed
        # 2. It can produce the final answer
        #
        # ----------------------------------------------------


# ============================================================
# Chat Input
# ============================================================

user_input = st.chat_input(
    "Type your message..."
)


if user_input:

    current_thread = (
        st.session_state["thread_id"]
    )

    # --------------------------------------------------------
    # Generate title for first message
    # --------------------------------------------------------

    threads = get_all_threads()

    current_thread_data = next(
        (
            thread
            for thread in threads
            if thread["thread_id"]
            == current_thread
        ),
        None,
    )

    if (
        current_thread_data
        and current_thread_data["title"]
        == "New Chat"
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

        st.markdown(
            user_input
        )

    # --------------------------------------------------------
    # Save user message
    # --------------------------------------------------------

    save_message(
        current_thread,
        "user",
        user_input,
    )

    st.session_state[
        "message_history"
    ].append(
        {
            "role": "user",
            "content": user_input,
        }
    )

    # --------------------------------------------------------
    # Assistant response
    # --------------------------------------------------------

    with st.chat_message(
        "assistant"
    ):

        status_box = st.status(
            "Thinking...",
            expanded=False,
        )

        try:

            final_response = asyncio.run(
                process_message(
                    user_input,
                    status_box,
                )
            )

            status_box.update(
                label="MCP tools finished",
                state="complete",
                expanded=False,
            )

            final_content = (
                final_response.content
                or ""
            )

            st.markdown(
                final_content
            )

        except Exception as e:

            status_box.update(
                label="Error",
                state="error",
                expanded=True,
            )

            final_content = (
                f"Sorry, something went wrong:\n\n"
                f"`{str(e)}`"
            )

            st.error(
                final_content
            )

    # --------------------------------------------------------
    # Save assistant response
    # --------------------------------------------------------

    save_message(
        current_thread,
        "assistant",
        final_content,
    )

    st.session_state[
        "message_history"
    ].append(
        {
            "role": "assistant",
            "content": final_content,
        }
    )