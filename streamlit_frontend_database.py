import streamlit as st
from langgraph_tool_backend import chatbot, retrieve_all_threads
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage, AIMessage
import uuid

# *************************** Utilities functions ********************************

# generate random thread_id (for multiple conversations)
def generate_thread_id():
    thread_id = uuid.uuid4()
    return thread_id

def reset_chat():
    thread_id = generate_thread_id()

    st.session_state['thread_id'] = thread_id
    add_threads(st.session_state['thread_id'])

    st.session_state['message_history'] = []

def add_threads(thread_id):
    if thread_id not in st.session_state['chat_threads']:
        st.session_state['chat_threads'].append(thread_id)

# returns message history for a given thread_id
def load_conv(thread_id):
    return chatbot.get_state(config={'configurable' : {'thread_id': thread_id}}).values['messages']


# **************************** Session Setup *************************************

# session_state is a dict - we add a key in dict->'message_history' and value of key is empty list
if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

# creating thread_id for session_state
if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = generate_thread_id() 

if 'chat_threads' not in st.session_state:
    st.session_state['chat_threads'] = retrieve_all_threads()

# adding current session state thread_id in chat_threads
add_threads(st.session_state['thread_id'])


# **************************** Sidebar UI ***************************************
st.sidebar.title('LangGraph Chatbot')

# when new chat button clicked call reset_chat function to:
# remove message_history
# generate new thread_id and add to chat_threads
if st.sidebar.button('New Chat'):
    reset_chat()

st.sidebar.header('Recent Conversations')

# display all thread_ids in sidebar
for thread_id in st.session_state['chat_threads'][::-1]:
    if st.sidebar.button(str(thread_id)):
        st.session_state['thread_id'] = thread_id
        messages = load_conv(thread_id)

        temp_messages = []


        for message in messages:
            # get content safely
            content = getattr(message, 'content', None)
            # skip empty or placeholder messages
            if content is None or (isinstance(content, str) and content.strip() == ''):
                continue

            # Keep only user and assistant (AI) messages; ignore tool/system messages
            if isinstance(message, HumanMessage):
                role = 'user'
                text = content
            elif isinstance(message, AIMessage):
                role = 'assistant'
                text = content
            else:
                # skip tool/system/other messages entirely
                continue

            temp_messages.append({'role': role, 'content': text})

        st.session_state['message_history'] = temp_messages

# ***************************** Main UI ******************************************

# loading conversation history and displaying it 
for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.text(message['content'])

# message_history format
# [{'role':'user', 'content':'Hi'}
#  {'role':'assistant', 'content':'Hello'}]

user_input = st.chat_input('Type here')

if user_input:

    #----------USER MESSAGE------------------#
    # add message to message history
    st.session_state['message_history'].append({'role':'user','content':user_input})
    
    # display user message
    with st.chat_message('user'):
        st.text(user_input)
    
    CONFIG = {'configurable' : {'thread_id':st.session_state['thread_id']}}

    # display assistant message — stream and capture final text
    response_chunks = []

    def stream_and_capture():
        for message_chunk, metadata in chatbot.stream(
            {'messages': [HumanMessage(content=user_input)]},
            config = CONFIG,
            stream_mode ='messages'
        ):
            # only capture AIMessage chunks; ignore tool messages during streaming
            if not isinstance(message_chunk, AIMessage):
                continue

            chunk_text = message_chunk.content or ''
            response_chunks.append(chunk_text)
            yield chunk_text

    with st.chat_message('assistant'):
        _ = st.write_stream(stream_and_capture())

    full_ai_text = ''.join(response_chunks).strip()
    if full_ai_text:
        st.session_state['message_history'].append({'role':'assistant','content': full_ai_text})
