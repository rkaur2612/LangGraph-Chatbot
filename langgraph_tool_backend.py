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

from langgraph.prebuilt import ToolNode, tools_condition
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool
import requests
import os

load_dotenv()

# ---------------- LLM ------------------------------------#
model = ChatGroq(model="llama-3.1-8b-instant")

# ----------------- TOOLS ----------------------------------#
# search_tool = DuckDuckGoSearchRun(region="us-en")
_search = DuckDuckGoSearchRun(region="us-en")

@tool
def search_tool(query: str):
    """
    Search the internet for current events, news, sports scores (like IPL), or real-time info.
    Use this tool whenever you need information that is not in your training data.
    """
    return _search.run(query)

# calculator tool
@tool
def calculator(first_num:float,second_num:float,operation:str) -> dict:
    """
    Perform basic arithmetic operations on two numbers
    Supported operations: add, sub, mul, div
    """

    try:
        if operation == "add":
            result = first_num + second_num
        elif operation == "sub":
            result = first_num - second_num
        elif operation == "mul":
            result = first_num * second_num
        elif operation == "div":
            if second_num == 0:
                return{"error":"Division by zero is not allowed"}
            result = first_num/second_num
        else:
            return {"error": f"Unsupported operation, {operation}"}
        
        return{"first_num":first_num, "second_num":second_num, "operation":operation, "result":result}
    except Exception as e:
        return {"error": str(e)}
            
# stock price tool
@tool
def get_stock_price(symbol:str) -> dict:
    """
    Fetch latest stock price for a given symbol  (e.g. 'AAPL','TSLA')
    using Alpha Vantage with API key in the URL
    """
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey=WEYXMRW3JCFZF0QH"
    r = requests.get(url)
    return r.json()


# make tool list
tools = [get_stock_price, search_tool, calculator]

# bind tools to llm
llm_with_tools = model.bind_tools(tools)

# ------------- STATE ------------------------#
class ChatState(TypedDict):
    # append all messages in list of messages, using reducer add_messages
    messages: Annotated[list[BaseMessage], add_messages]


# ----------- NODES ---------------------------------#

# Chat node
def chat_node(state:ChatState):
    # takes user query from state
    messages = state['messages']

    # pass to llm
    response = llm_with_tools.invoke(messages)

    # add llm message back to state
    return{'messages' : [response]}

# tool node
tool_node = ToolNode(tools) # executes tool call

# -------------------- CHECKPOINTER --------------------# 
# database connection
conn = sqlite3.connect(database='chatbot.db', check_same_thread=False)

# checkpointer
checkpointer = SqliteSaver(conn=conn)

# --------------------- GRAPH ---------------------------#
# define graph
graph = StateGraph(ChatState)

# add nodes
graph.add_node('chat_node',chat_node)
graph.add_node('tools',tool_node)

# add edges
graph.add_edge(START,'chat_node')

# start from chat node and whether to go to ToolNode or end , tools_condition tells
# so if LLM asked for tool, go to ToolNode else end node
graph.add_conditional_edges('chat_node', tools_condition)

graph.add_edge('tools', 'chat_node')

# compile graph
chatbot = graph.compile(checkpointer=checkpointer)

# ------------------- HELPER -------------------------#
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