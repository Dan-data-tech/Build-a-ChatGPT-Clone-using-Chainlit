from operator import itemgetter
from langchain_together import ChatTogether
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough, RunnableLambda
from langchain.schema.runnable.config import RunnableConfig
from langchain.memory import ConversationBufferMemory
#from langchain_community.chat_message_histories import RedisChatMessageHistory
#from langchain_core.chat_history import InMemoryChatMessageHistory
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer 
import redis
import chainlit as cl
from chainlit.types import ThreadDict
from chainlit.step import StepDict
from dotenv import load_dotenv
#import json
import asyncio


load_dotenv()

# REDIS_HOST = "localhost"
# REDIS_PORT = 6379
# #REDIS_KEY_PREFIX = "chat_memory:"
# REDIS_URL=f"redis://{REDIS_HOST}:{REDIS_PORT}" 
# def get_redis_history(session_id: str):
#     return RedisChatMessageHistory(url=REDIS_URL, session_id=session_id)
# engine = create_engine(DATABASE_URL)
# Session = sessionmaker(bind=engine)
DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/chainlit"


@cl.data_layer
async def get_data_layer():
    return await SQLAlchemyDataLayer(conninfo=DATABASE_URL)


def setup_runnable():
        memory = cl.user_session.get("memory")
        model = ChatTogether(streaming=True)
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system","You are a helpful chatbot named smiley"),
                MessagesPlaceholder(variable_name="history"),
                ("human","{question}")
            ]
        )
        runnable = (
        RunnablePassthrough.assign(
            history=RunnableLambda(memory.load_memory_variables) | itemgetter("history")
        )
        | prompt
        | model
        | StrOutputParser()
         )
        cl.user_session.set("runnable", runnable)
  

@cl.password_auth_callback
async def password_auth_callback(username: str, password: str):
    # if it returns a user that passed the conditions that it's authenticated

    # user = cl.User(identifier=username, metadata={"password": password})
    # await data_layer.create_user(user)
    if (username, password) == ("admin", "admin"):
        return cl.User(
            identifier="admin", metadata={"role": "admin", "provider": "credentials"}
        )
    else:
        return None
    


@cl.on_chat_start
async def on_chat_start():
    memory = ConversationBufferMemory(
        #chat_memory=get_redis_history(session_id), 
        return_messages=True)
    cl.user_session.set("memory", memory)
    setup_runnable() 
    


@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):
    #thread_id = cl.user_session.set("thread_id", thread["id"])
    memory = ConversationBufferMemory(
        #chat_memory=get_redis_history(thread_id),
        return_messages=True)  
    root_messages = [m for m in thread["steps"] if m["parentId"] == None]
    for message in root_messages:
        if message["type"] == "user_message":
            memory.chat_memory.add_user_message(message.content)
            message.content.send()
        else:
            memory.chat_memory.add_ai_message(message.content)
            message.content.send()
    cl.user_session.set("memory", memory)
    setup_runnable()
   


@cl.on_message
async def on_message(message: cl.Message):
    # data_layer = await get_data_layer()
    # print(type(data_layer))


    memory = cl.user_session.get("memory")  
    runnable = cl.user_session.get("runnable")  
    
    res = cl.Message(content="")

    async for chunk in runnable.astream(
        {"question": message.content},
        config=RunnableConfig(callbacks=[cl.LangchainCallbackHandler()]),
    ):
        await res.stream_token(chunk)

    await res.send()
    
    user_step_dict = StepDict(
        name="User Message",
        type="user_message",
        streaming=True,
        threadId=cl.user_session.get("thread_id"),
        input=message.content
    )
    ai_step_dict = StepDict(
        name="Assistant Message",
        type="assistant_message",
        streaming=True,
        threadId=cl.user_session.get("thread_id"),
        output=res.content
    )

    #register on databse 
    # await data_layer.create_step(user_step_dict)
    # await data_layer.create_step(ai_step_dict)

    #save on in-memory for chat context
    memory.chat_memory.add_user_message(message.content)
    memory.chat_memory.add_ai_message(res.content)




