from langchain_together import ChatTogether
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory
import chainlit as cl
import os 

api_key = os.getenv("TOGETHERAI_API_KEY")

llm = ChatTogether(model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
               together_api_key=api_key, max_tokens=200)
store = {}

def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
        if session_id not in store:
            store[session_id] = InMemoryChatMessageHistory()
        return store[session_id]

chain = RunnableWithMessageHistory(llm, get_session_history)

@cl.set_starters
async def set_starters():
    return [
        cl.Starter(
            label="Morning routine ideation",
            message="Can you help me create a personalized morning routine that would help increase my productivity throughout the day? Start by asking me about my current habits and what activities energize me in the morning.",
           # icon="/public/idea.svg",
            ),

        cl.Starter(
            label="Explain superconductors",
            message="Explain superconductors like I'm five years old.",
           # icon="/public/learn.svg",
            ),
        cl.Starter(
            label="Python script for daily email reports",
            message="Write a script to automate sending daily email reports in Python, and walk me through how I would set it up.",
           # icon="/public/terminal.svg",
            ),
        cl.Starter(
            label="Text inviting friend to wedding",
            message="Write a text asking a friend to be my plus-one at a wedding next month. I want to keep it super short and casual, and offer an out.",
            #icon="/public/write.svg",
            )
        ]
@cl.step(type="tool")
async def tool():
     await cl.sleep(2)

     return "Response from the tool!"

@cl.on_chat_start
def on_chat_start():
    print("A new chat session started!")

@cl.on_stop # This is a decorator that executes when the user stops the generation of response
def on_stop():
     print("The chat session stopped!")

@cl.on_chat_end
def on_chat_end():
    print("The chat session ended!")

@cl.on_message
async def main(message: cl.Message):
    #tool_res = await tool()

    response = chain.invoke(message.content, config={"configurable": {"session_id": "default_session"}})
    await cl.Message(content=response.content).send()

