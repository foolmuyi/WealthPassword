# !/usr/bin/env python3
# -*- coding: utf-8 -*-


import os
import asyncio
import telegram
from dotenv import load_dotenv


load_dotenv()
bot_token = os.getenv('BOT_TOKEN')
chat_id = os.getenv('CHAT_ID')

bot = telegram.Bot(bot_token)
loop = asyncio.get_event_loop()

def sendMsg(text):
    loop.run_until_complete(bot.send_message(chat_id=chat_id,text=text))