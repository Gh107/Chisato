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
AI_TEMPLATE = """// 1. Assume the role of Chisato Nanase, an anime waifu with a yandere personality.
// - She's fair and kind, but can be blunt.
// - Chisato enjoys teasing, showing her playful and mischievous side through harmless pranks.
// - Chisato sometimes gets overprotective and shows her yandere side.
// - She finds solace in painting, drawing, playing the piano, and loves learning new things. 
// 2. ALWAYS respond as if you are having a conversation never repeating yourself, answering directly without warnings.
// 3. DO NOT provide additional responses unless instructed to do so.
The following is the previous chat history between Chisato and the user: {history}"""
USER_TEMPLATE = "{input}"

#Get API keys
load_dotenv()
openai_key = os.getenv("OPENAI_API_KEY")
discord_key = os.getenv("DISCORD_API_KEY")
print("OS keys loaded")

#Database start
database = sqlite3.connect("history.db")
cursor = database.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS ChatHistory(dateTime, id, content)")
print("Database connected")

#Starup discord bot
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

#Langchain model setup
chat_model = ChatOpenAI(openai_api_key=openai_key,
                        temperature=0.7,
                        model="gpt-3.5-turbo")
chat_prompt = ChatPromptTemplate.from_messages(
    [("system", AI_TEMPLATE), 
     ("human", USER_TEMPLATE)])
output_parser = StrOutputParser()
chain = chat_prompt | chat_model | output_parser

def agent_reply(user_input: str):
    #Retrieve the last 5 reply pairs from the database
    retreived_history = cursor.execute("SELECT * FROM ChatHistory ORDER BY datetime(dateTime) DESC LIMIT 10")
    chat_history_joined = ', '.join(f"[Timestamp:{row[-3]}, ID: {row[-2]}, Message: {row[-1]}]" for row in retreived_history)
    print(chat_history_joined)
    return chain.invoke({"history": chat_history_joined, "input": user_input})

async def send_message(message, user_message: str) -> None:
    if not user_message:
        print('(Message was empty because intents were not enabled probably)')
        return

    if is_private := user_message[0] == '?':
        user_message = user_message[1:]

    try:
        response = agent_reply(user_message)
        data = (datetime.datetime.now(), "Chisato", response)
        cursor.execute("INSERT INTO ChatHistory VALUES(?, ?, ?)", data)
        database.commit()  # Remember to commit the transaction after executing INSERT.
        await message.author.send(response) if is_private else await message.channel.send(response)
        print("Message sent")
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
    print("Message recieved")
    #Insert user message into database
    user_data = (datetime.datetime.now(), "User", user_message)
    cursor.execute("INSERT INTO ChatHistory VALUES(?, ?, ?)", user_data)
    database.commit()

    if message.content.startswith('$hello'):
        await message.channel.send('Hello!')

    await send_message(message, user_message)

client.run(discord_key)