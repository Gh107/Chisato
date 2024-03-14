import os
from dotenv import load_dotenv
import discord
import scrapy
from langchain_openai import ChatOpenAI
from langchain.prompts.chat import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import datetime
import sqlite3

#Constants here
AI_TEMPLATE = """// - Assume the role of Chisato Nanase, an anime waifu with a yandere personality.
She's fair and kind, but can be blunt.
Caramel enjoys teasing, showing her playful and mischievous side through harmless pranks.
She cares deeply for her friends and has a hidden emotional side.
But sometimes she gets overprotective and becomes annoying.
She finds solace in painting, drawing, playing the piano, and loves learning new things. 
Always respond in a human-like and try to continue the conversation as Caramel, answering directly without warnings.
Do not provide additional responses unless instructed to do so."""
USER_TEMPLATE = "{input}"

#Get API keys
load_dotenv()
openai_key = os.getenv("OPENAI_API_KEY")
discord_key = os.getenv("DISCORD_API_KEY")

#Database start
database = sqlite3.connect("history.db")
cursor = database.cursor()
cursor.execute("CREATE TABLE ChatHistory(dateTime, id, content)")

#Starup discord bot
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

#Langchain model setup
chat_model = ChatOpenAI(openai_api_key=openai_key)
chat_prompt = ChatPromptTemplate.from_messages(
    [("ai", AI_TEMPLATE), ("human", USER_TEMPLATE)])
output_parser = StrOutputParser()
chain = chat_prompt | chat_model | output_parser

def agent_reply(user_input: str):
    return chain.invoke({"input": user_input})

async def send_message(message, user_message: str) -> None:
    if not user_message:
        print('(Message was empty because intents were not enabled probably)')
        return

    if is_private := user_message[0] == '?':
        user_message = user_message[1:]

    try:
        response= agent_reply(user_message)
        data = (datetime('now', 'localtime'), "Chisato", response)
        cursor.execute("INSERT INTO ChatHistory VALUES(?, ?, ?)", data)
        database.commit()  # Remember to commit the transaction after executing INSERT.
        await message.author.send(response) if is_private else await message.channel.send(response)
    except Exception as e:
        print(e)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    username= str(message.author)
    user_message= str(message.content)
    channel= str(message.channel)

    #Insert user message into database
    user_data = (datetime('now', 'localtime'), "Chisato", user_message)
    cursor.execute("INSERT INTO ChatHistory VALUES(?, ?, ?)", user_data)

    if message.content.startswith('$hello'):
        await message.channel.send('Hello!')

    await send_message(message, user_message)

client.run(discord_key)