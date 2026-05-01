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
import logging

from langgraph.prebuilt import ToolNode, tools_condition
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool
import requests
import os

load_dotenv()

# configure logger
logging.basicConfig(level=logging.INFO)

# ---------------- LLM ------------------------------------#
# lower temperature to reduce hallucinations when calling tools
model = ChatGroq(model="llama-3.1-8b-instant", temperature=0.2)

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

# Clear system prompt describing allowed tools and rules to reduce hallucinated tool calls
SYSTEM_PROMPT = (
    "You have access to the following tools (use ONLY these exact names):\n"
    "- calculator(first_num: float, second_num: float, operation: str) -> returns a JSON with keys first_num, second_num, operation, result.\n"
    "- search_tool(query: str) -> returns search results.\n"
    "- get_stock_price(symbol: str) -> returns stock price info.\n"
    "Rules:\n"
    "- Only call a tool when it is strictly necessary to compute or retrieve information.\n"
    "- Do NOT invent or assume any other tool names. If a tool is not available, answer directly.\n"
    "- When returning tool output to the user, present it in a human-friendly sentence rather than raw JSON.\n"
)

# ------------- STATE ------------------------#
class ChatState(TypedDict):
    # append all messages in list of messages, using reducer add_messages
    messages: Annotated[list[BaseMessage], add_messages]


# ----------- NODES ---------------------------------#

# Chat node
def chat_node(state:ChatState):
    # takes user query from state
    messages = state['messages']

    # Ensure system prompt is present at the start of the conversation to guide tool usage
    if not messages or not isinstance(messages[0], SystemMessage):
        messages_to_send = [SystemMessage(content=SYSTEM_PROMPT)] + messages
    else:
        messages_to_send = messages

    # Try invoking LLM with tools; if tool call validation fails or any tool-related error
    # occurs, fall back to the base model (no tools) to produce a safe assistant reply.
    try:
        response = llm_with_tools.invoke(messages_to_send)
    except Exception as e:
        logging.exception("Tool invocation failed, falling back to base model: %s", e)
        try:
            fallback_resp = model.invoke(messages_to_send)
            return {'messages': [fallback_resp]}
        except Exception:
            # As a last resort, return a polite assistant message
            from langchain_core.messages import AIMessage
            return {'messages': [AIMessage(content="Sorry, I can't run the requested tool right now. Please ask your question without tool usage.")]}    

    # add llm message back to state
    return {'messages': [response]}

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