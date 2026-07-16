import streamlit as st
from db_backend import chatBot, retrieveAllThreads
from langchain_core.messages import HumanMessage
import uuid

# Utility Functions

def generateThreadID():
    return str(uuid.uuid4())

def addThread(thread_id, title="New Chat"):

    if thread_id not in st.session_state["chat_threads"]:
        st.session_state["chat_threads"].append(thread_id)

    if thread_id not in st.session_state["thread_titles"]:
        st.session_state["thread_titles"][thread_id] = title

def resetChat():
    thread_id = generateThreadID()
    st.session_state["thread_id"] = thread_id
    st.session_state["messageHistory"] = []
    addThread(thread_id, "New Chat")


def loadConversation(thread_id):
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state = chatBot.get_state(config)
        if state and state.values:
            return state.values.get("messages", [])
        return []
    except Exception as e:
        st.error(f"Error Loading Conversation: {e}")
        return []


# Page Config
st.set_page_config(
    page_title="ChatBuddy",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("ChatBuddy")

# Session State Setup
if "messageHistory" not in st.session_state:
    st.session_state["messageHistory"] = []

if "thread_id" not in st.session_state:
    st.session_state["thread_id"] = generateThreadID()

if "chat_threads" not in st.session_state:
    st.session_state["chat_threads"] = retrieveAllThreads()

if "thread_titles" not in st.session_state:
    st.session_state['thread_titles'] = {}

addThread(st.session_state["thread_id"])

# Sidebar
st.sidebar.title("ChatBuddy")
if st.sidebar.button("New Chat"):
    resetChat()
st.sidebar.header("Conversation History")


#Conversation History
for thread_id in st.session_state["chat_threads"][::-1]:
    title = st.session_state["thread_titles"].get(
        thread_id,
        "Untitled Chat"
    )
    
    if st.sidebar.button(title,key=f"thread_{thread_id}"):
        st.session_state["thread_id"] = thread_id
        messages = loadConversation(thread_id)
        temp_messages = []
        for message in messages:
            if isinstance(message, HumanMessage):
                role = "user"
            else:
                role = "assistant"
            temp_messages.append({"role": role,"content": message.content})
        st.session_state["messageHistory"] = temp_messages
        st.rerun()


# Display Chat History
for message in st.session_state["messageHistory"]:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# Chat Input
user_input = st.chat_input("Type Your Message Here ......")
if user_input:
    current_thread = st.session_state["thread_id"]
    if (current_thread in st.session_state["thread_titles"]
        and st.session_state["thread_titles"][current_thread] == "New Chat"):
        st.session_state["thread_titles"][current_thread] = (
        user_input[:40] + "..."
        if len(user_input) > 40
        else user_input
    )
    st.session_state["messageHistory"].append({"role": "user","content": user_input})

    with st.chat_message("user"): 
        st.markdown(user_input)

    config = {"configurable": {"thread_id": st.session_state["thread_id"]}}
    # Assistant Response
    with st.chat_message("assistant"):
        chatBotReply = st.write_stream(
            message_chunk.content
            for message_chunk, metadata in chatBot.stream(
                {
                    "messages": [
                        HumanMessage(content=user_input)
                    ]
                },
                config=config,
                stream_mode="messages"
            )
        )
    st.session_state["messageHistory"].append({"role": "assistant","content": chatBotReply})