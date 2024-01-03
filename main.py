import concurrent.futures

from flask import Flask, render_template, request
from telethon import TelegramClient, events, types
from datetime import datetime
import asyncio
import sqlite3

api_id = 1111111
api_hash = '***********'

app = Flask(__name__)

conn = sqlite3.connect('telegram_chats.db')
cursor = conn.cursor()

# Create table
cursor.execute('''CREATE TABLE IF NOT EXISTS chats
                 (id INTEGER PRIMARY KEY,
                  title TEXT,
                  keywords TEXT,
                  stop_words TEXT)''')

# Create messages table
cursor.execute('''CREATE TABLE IF NOT EXISTS messages
                 (chat_title TEXT,
                  message TEXT,
                  timestamp REAL)''')

conn.commit()
conn.close()

# Create Telegram client
client = TelegramClient('anon', api_id, api_hash, device_model="iPhone 55 Pro", system_version="IOS 100.1")
client.start()


# Define function for checking if message is unique within the last 10 seconds
def unique_message(message):
    conn = sqlite3.connect('telegram_chats.db')
    cursor = conn.cursor()

    cursor.execute('SELECT message FROM messages WHERE message = ?', (message,))
    result = cursor.fetchone()

    if result:
        conn.close()
        return False
    else:
        conn.close()
        return True

# Define function for deleting old messages from the database
def delete_old_messages():
    conn = sqlite3.connect('telegram_chats.db')
    cursor = conn.cursor()

    cursor.execute('DELETE FROM messages WHERE timestamp < ?', (datetime.now().timestamp() - 10,))
    conn.commit()
    conn.close()

@client.on(events.NewMessage())
async def handle_new_message(event):
    chat = await client.get_entity(event.message.peer_id)

    sender = await event.get_sender()
    user_link = ''
    if isinstance(sender, types.User):
        user_link = f'[{sender.first_name}](https://t.me/{sender.username})'

    chat_title = chat.username or chat.title
    message = event.message.message
    lowermessage = message.lower()
    message_media = event.message.media
    message_link = 'https://t.me/c/{}/{}'.format(chat_title, event.message.id)
    link = f'[🔎 Источник]({message_link})'
    delete_old_messages()

    conn = sqlite3.connect('telegram_chats.db')
    cursor = conn.cursor()

    cursor.execute('SELECT id FROM chats WHERE title = ?', (chat_title,))
    result = cursor.fetchone()

    conn.close()

    if not result:
        return

    keywords = get_keywords(chat_title)
    stop_words = get_stop_words(chat_title)

    if any(keyword in lowermessage for keyword in keywords) and not any(stop_word in lowermessage for stop_word in stop_words):

        if unique_message(message):
            text = f'{user_link}\n\n{message}\n\n{link}'
            ent = await client.get_entity('*********')
            await client.send_message(ent, text, file=message_media)
            conn = sqlite3.connect('telegram_chats.db')
            cursor = conn.cursor()

            cursor.execute('INSERT INTO messages (chat_title, message, timestamp) VALUES (?, ?, ?)',
                           (chat_title, message, datetime.now().timestamp()))
            conn.commit()

            conn.close()
        else:
            return



# Define function for getting keywords for a chat from the database
def get_keywords(title):
    conn = sqlite3.connect('telegram_chats.db')
    cursor = conn.cursor()

    cursor.execute('SELECT keywords FROM chats WHERE title = ?', (title,))
    result = cursor.fetchone()

    conn.close()

    if result:
        return result[0].split(', ')
    else:
        return []

# Define function for getting stop words for a chat from the database
def get_stop_words(title):
    conn = sqlite3.connect('telegram_chats.db')
    cursor = conn.cursor()

    cursor.execute('SELECT stop_words FROM chats WHERE title = ?', (title,))
    result = cursor.fetchone()

    conn.close()

    if result:
        return result[0].split(', ')
    else:
        return []

# Define route for adding a new chat
@app.route('/add_chat', methods=['POST'])
def add_chat():
    title = request.form.get('title').replace('https://t.me/', '')
    keywords = request.form.get('keywords')
    stop_words = request.form.get('stop_words')

    conn = sqlite3.connect('telegram_chats.db')
    cursor = conn.cursor()

    cursor.execute('INSERT INTO chats (title, keywords, stop_words) VALUES (?, ?, ?)', (title, keywords, stop_words))
    conn.commit()

    conn.close()

    return 'Chat added successfully!'

# Define route for displaying all chats
@app.route('/')
def index():
    conn = sqlite3.connect('telegram_chats.db')
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM chats')
    result = cursor.fetchall()

    conn.close()

    return render_template('index.html', chats=result)

# Define route for deleting a chat
@app.route('/delete_chat', methods=['POST'])
def delete_chat():
    chat_id = request.form['id']

    conn = sqlite3.connect('telegram_chats.db')
    cursor = conn.cursor()

    cursor.execute('DELETE FROM chats WHERE id = ?', (chat_id,))
    conn.commit()

    conn.close()

    return 'Chat deleted successfully!'


@app.route('/edit_chat', methods=['POST'])
def edit_chat():
    chat_id = request.form['id']
    title = request.form['title']
    keywords = request.form['keywords']
    stop_words = request.form['stop_words']

    conn = sqlite3.connect('telegram_chats.db')
    cursor = conn.cursor()

    cursor.execute('UPDATE chats SET title = ?, keywords = ?, stop_words = ? WHERE id = ?', (title, keywords, stop_words, chat_id))
    conn.commit()

    conn.close()

    return 'Chat edited successfully!'

loop = asyncio.get_event_loop()
executor = concurrent.futures.ThreadPoolExecutor()

async def run_app():
    await loop.run_in_executor(executor, app.run)
    await client.run_until_disconnected()

async def main():
    await asyncio.wait([asyncio.ensure_future(run_app())])

loop.run_until_complete(main())


