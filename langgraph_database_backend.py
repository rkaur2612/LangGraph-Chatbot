# START, END are dummy nodes
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated, Literal
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
import operator
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import add_messages
import sqlite3

load_dotenv()

model = ChatGroq(model="llama-3.1-8b-instant")

class ChatState(TypedDict):
    # append all messages in list of messages, using reducer add_messages
    messages: Annotated[list[BaseMessage], add_messages]


def chat_node(state:ChatState):
    # takes user query from state
    messages = state['messages']

    # pass to llm
    response = model.invoke(messages)

    # add llm message back to state
    return{'messages' : [response]}

# database connection
conn = sqlite3.connect(database='chatbot.db', check_same_thread=False)

# checkpointer
checkpointer = SqliteSaver(conn=conn)

# define graph
graph = StateGraph(ChatState)

# add nodes
graph.add_node('chat_node',chat_node)

# add edges
graph.add_edge(START,'chat_node')
graph.add_edge('chat_node',END)

# compile graph
chatbot = graph.compile(checkpointer=checkpointer)

def retrieve_all_threads():
    """Return list of unique threads in database"""
    all_threads = set()

    for checkpoint in checkpointer.list(None):
        # print(checkpoint.config['configurable']['thread_id'])
        all_threads.add(checkpoint.config['configurable']['thread_id'])

    return list(all_threads)

#testing only - NOT IN USE

# CONFIG = {'configurable' : {'thread_id':'thread_2'}}

# response = chatbot.invoke(
#             {'messages': [HumanMessage(content='My name is Sharn')]},
#             config = CONFIG
#             )

# print(response)