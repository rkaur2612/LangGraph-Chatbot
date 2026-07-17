# START, END are dummy nodes
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated, Literal
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
import operator
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph.message import add_messages
import sqlite3
import logging

from langgraph.prebuilt import ToolNode, tools_condition
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool
import requests
import os

from langchain_mcp_adapters.client import MultiServerMCPClient
import asyncio
import nest_asyncio
import aiosqlite
import json

load_dotenv()

# Use one shared event loop for async MCP tools, checkpoint access, and graph calls.
ASYNC_LOOP = asyncio.new_event_loop()
asyncio.set_event_loop(ASYNC_LOOP)

# configure logger
logging.basicConfig(level=logging.INFO)

# ---------------- LLM ------------------------------------#
# lower temperature to reduce hallucinations when calling tools
model = ChatGroq(model="llama-3.1-8b-instant", temperature=0.2)

# --------------------- MCP CLIENT ---------------------------#
async def load_mcp_tools():
    client = MultiServerMCPClient(
        {
            "calculator": {
                "command": "python",
                "args": ["mcp_servers/calculator_server.py"],
                "transport": "stdio",
            },
            "search": {
                "command": "python",
                "args": ["mcp_servers/search_server.py"],
                "transport": "stdio",
            },
            "stock": {
                "command": "python",
                "args": ["mcp_servers/stock_server.py"],
                "transport": "stdio",
            }
        }
    )

    tools = await client.get_tools()
    return tools

# mcp tool loading
nest_asyncio.apply()

# tools = asyncio.run(load_mcp_tools())
tools = ASYNC_LOOP.run_until_complete(load_mcp_tools())

print("Loaded MCP Tools:", [t.name for t in tools])

for tool in tools:
    print(tool.name)
    print(json.dumps(tool.args_schema, indent=2))

# bind tools to llm
llm_with_tools = model.bind_tools(tools)

# Clear system prompt describing allowed tools and rules to reduce hallucinated tool calls
SYSTEM_PROMPT = (
    "You have access to the following tools (use ONLY these exact names):\n"
    "- calculator(first_num: float, second_num: float, operation: str) -> returns a JSON with keys first_num, second_num, operation, result.\n"
    "- search_tool(query: str) -> returns web search results for current or factual information.\n"
    "- get_stock_price(symbol: str) -> returns the latest stock quote for a ticker symbol.\n"
    "Rules:\n"
    "- Call calculator for arithmetic questions like add, subtract, multiply, or divide.\n"
    "- Call search_tool for current, real-world, factual, location, travel, news, or recommendation questions.\n"
    "- Call get_stock_price for any stock, share, ticker, market price, or quote question.\n"
    "- Do NOT answer those questions directly when a matching tool exists.\n"
    "- Do NOT invent or assume any other tool names.\n"
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
        if getattr(response, "tool_calls", None):
            logging.info("LLM requested tool call(s): %s", response.tool_calls)
        else:
            logging.info("LLM answered directly without requesting a tool.")
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
#tool_node = ToolNode(tools, handle_tool_errors=True) # executes tool call
tool_node = ToolNode(tools, handle_tool_errors=True)

# -------------------- CHECKPOINTER --------------------# 
async def create_checkpointer():
    conn = await aiosqlite.connect(database='chatbot.db')
    return AsyncSqliteSaver(conn=conn)


# checkpointer
checkpointer = ASYNC_LOOP.run_until_complete(create_checkpointer())

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

    async def collect_threads():
        async for checkpoint in checkpointer.alist(None):
            all_threads.add(checkpoint.config['configurable']['thread_id'])

    ASYNC_LOOP.run_until_complete(collect_threads())

    return list(all_threads)


def run_async(coro):
    return ASYNC_LOOP.run_until_complete(coro)