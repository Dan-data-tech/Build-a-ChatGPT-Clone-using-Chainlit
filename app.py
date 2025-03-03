from operator import itemgetter
from langchain_together import ChatTogether
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema.output_parser import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough, RunnableLambda
from langchain.schema.runnable.config import RunnableConfig
from langchain.memory import ConversationBufferMemory
from chainlit.data.sql_alchemy import SQLAlchemyDataLayer 
import chainlit as cl
from chainlit.types import ThreadDict
from chainlit.step import StepDict
from dotenv import load_dotenv


load_dotenv()


DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/chainlit"


@cl.data_layer
def get_data_layer():
    return SQLAlchemyDataLayer(conninfo=DATABASE_URL)

data_layer = get_data_layer()

@cl.set_starters
async def set_starters():
    return [
        cl.Starter(
            label="Morning routine ideation",
            message="Can you help me create a personalized morning routine that would help increase my productivity throughout the day? Start by asking me about my current habits and what activities energize me in the morning.",
            icon=r"public\idea.svg",
            ),

        cl.Starter(
            label="Explain superconductors",
            message="Explain superconductors like I'm five years old.",
            icon=r"public\learn.svg",
            ),
        cl.Starter(
            label="Python script for daily email reports",
            message="Write a script to automate sending daily email reports in Python, and walk me through how I would set it up.",
            icon=r"public\code.svg",
            ),
        cl.Starter(
            label="Text inviting friend to wedding",
            message="Write a text asking a friend to be my plus-one at a wedding next month. I want to keep it super short and casual, and offer an out.",
            icon=r"public\write.svg",
            )
        ]


def setup_runnable():
        memory = cl.user_session.get("memory")
        model = ChatTogether(streaming=True)
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system","You are a ChatGPT"),
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

    if (username, password) == ("admin", "admin"): 
        return cl.User(
            identifier="admin", metadata={"role": "admin", "provider": "credentials"}
        )
    elif (username, password) == ("user", "test"):
        return cl.User(
            identifier="user", metadata={"role": "user", "provider": "credentials"}
        )
    else:
        return None
    


@cl.on_chat_start
async def on_chat_start():
    memory = ConversationBufferMemory(return_messages=True)
    cl.user_session.set("memory", memory)
    setup_runnable() 
    


@cl.on_chat_resume
async def on_chat_resume(thread: ThreadDict):
    memory = ConversationBufferMemory(return_messages=True)  
    root_messages = [m for m in thread["steps"] if m["parentId"] == None] 
    for message in root_messages:
        if message["type"] == "user_message":
            memory.chat_memory.add_user_message(message["output"])           
        else:
            memory.chat_memory.add_ai_message(message["output"])       
    cl.user_session.set("memory", memory)
    setup_runnable()
   


@cl.on_message
async def on_message(message: cl.Message):
    memory = cl.user_session.get("memory")  
    runnable = cl.user_session.get("runnable")  
    
    res = cl.Message(content="")

    async for chunk in runnable.astream(
        {"question": message.content},
        config=RunnableConfig(callbacks=[cl.LangchainCallbackHandler()]),
    ):
        await res.stream_token(chunk)

    await res.send()

    #save on in-memory for chat context
    memory.chat_memory.add_user_message(message.content)
    memory.chat_memory.add_ai_message(res.content)




