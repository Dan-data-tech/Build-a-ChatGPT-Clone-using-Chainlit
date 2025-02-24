from operator import itemgetter
from langchain_together import ChatTogether
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import Runnable, RunnablePassthrough, RunnableLambda
from langchain.schema.runnable.config import RunnableConfig
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import RedisChatMessageHistory
import redis
import chainlit as cl
from chainlit.types import ThreadDict
from dotenv import load_dotenv
from chainlit.sidebar import ElementSidebar
load_dotenv()


# REDIS_HOST = "localhost"
# REDIS_PORT = 6379
# REDIS_KEY_PREFIX = "chat_memory:"


@cl.password_auth_callback
def auth():
    return cl.User(identifier="test")


@cl.on_chat_start
async def on_chat_start():
    cl.user_session.set("chat_history", [])


@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):
    cl.user_session.set("chat_history", [])

    # user_session = thread["metadata"]
    
    for message in thread["steps"]:
        if message["type"] == "user_message":
            cl.user_session.get("chat_history").append({"role": "user", "content": message["output"]})
        elif message["type"] == "assistant_message":
            cl.user_session.get("chat_history").append({"role": "assistant", "content": message["output"]})


@cl.on_message
async def on_message(message: cl.Message):
    # Note: by default, the list of messages is saved and the entire user session is saved in the thread metadata
    chat_history = cl.user_session.get("chat_history")
 

    client = Together(api_key=api_key)

    chat_history.append({"role": "user", "content": message.content})

    chat_response = client.chat.complete(
        model=model,
        messages=chat_history
    )
    
    response_content = chat_response.choices[0].message.content

    chat_history.append({"role": "assistant", "content": response_content})

    await cl.Message(content=response_content).send()

 