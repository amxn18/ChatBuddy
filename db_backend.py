from langgraph.graph import StateGraph, START, END
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import add_messages
from typing import List, TypedDict, Annotated
import sqlite3

from dotenv import load_dotenv
load_dotenv()

llm = HuggingFaceEndpoint(
        repo_id="Qwen/Qwen3-4B-Instruct-2507",
        task="text-generation",
    )
model = ChatHuggingFace(llm=llm)

class ChatState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]

def chatNode(state: ChatState):
    messages = state['messages']
    response = model.invoke(messages)
    return {"messages": [response]}

conn = sqlite3.connect(database = 'chatbot.db', check_same_thread= False)
checkPointer = SqliteSaver(conn = conn)

graph = StateGraph(ChatState)
graph.add_node("chatNode", chatNode)
graph.add_edge(START, "chatNode")
graph.add_edge("chatNode", END)

chatBot = graph.compile(checkpointer= checkPointer)

def retrieveAllThreads():
    allThreads = set()
    for checkPoint in checkPointer.list(None):
        allThreads.add(checkPoint.config['configurable']['thread_id'])
        
    return (list(allThreads))