import discord
from discord.ext import commands
from PIL import Image, ImageOps
import pytesseract
import requests
from bs4 import BeautifulSoup
import io
import re
import asyncio

intents = discord.Intents.all()

TOKEN = 'TOKENHERE'
BLACKLISTED_PHRASES = ["tzgnis", "canceljohnnys", "kickpredators", "degen", "degen_news", "degennews", "degenews", "dox", "doxxing"]

bot = commands.Bot(command_prefix='!', intents=intents)

removed_messages = set()

def perform_ocr(image):
    try:
        image = ImageOps.grayscale(image)
        image = ImageOps.autocontrast(image)

        extracted_text = pytesseract.image_to_string(image, config='--psm 6')
        return extracted_text
    except Exception as e:
        print(f"Error performing OCR: {e}")
    return None

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    for attachment in message.attachments:
        if attachment.content_type.startswith('image'):
            await process_image_attachment(message, attachment)

    image_links = find_image_links(message.content)
    for link in image_links:
        await process_linked_image(message, link)

    if is_website_link(message.content):
        await process_website_link(message)

    await bot.process_commands(message)

async def process_image_attachment(message, attachment):
    try:
        image_bytes = await attachment.read()
        image = Image.open(io.BytesIO(image_bytes))
        
        extracted_text = perform_ocr(image)
        print(f"Extracted text from image: {extracted_text}")

        for phrase in BLACKLISTED_PHRASES:
            if phrase.lower() in extracted_text.lower():
                await handle_blacklisted_message(message)
                return
    except Exception as e:
        print(f"Error processing image attachment: {e}")

async def process_linked_image(message, link):
    try:
        print(f"Processing linked image: {link}")
        response = requests.get(link)

        if response.status_code == 200:
            print(f"Image URL: {link}")

            extracted_text = perform_ocr(Image.open(io.BytesIO(response.content)))

            if extracted_text:
                print(f"Extracted text from linked image: {extracted_text}")

                for phrase in BLACKLISTED_PHRASES:
                    if phrase.lower() in extracted_text.lower():
                        await handle_blacklisted_message(message)
                        return
            else:
                print(f"Error: Failed to extract text from linked image: {link}")
        else:
            print(f"Error: Received status code {response.status_code} for linked image: {link}")
    except Exception as e:
        print(f"Error processing linked image: {e}")

def find_image_links(text):
    return re.findall(r'(https?://\S+\.(?:png|jpg|jpeg|gif|bmp|tiff))', text)

def is_website_link(text):
    return text.startswith(('http://', 'https://'))

async def process_website_link(message):
    try:
        url = message.content
        for phrase in BLACKLISTED_PHRASES:
            if phrase.lower() in url.lower():
                await handle_blacklisted_message(message)
                return

        response = requests.get(url)

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            page_content = soup.get_text()

            for phrase in BLACKLISTED_PHRASES:
                if phrase.lower() in page_content.lower():
                    await handle_blacklisted_message(message)
                    return
    except Exception as e:
        print(f"Error processing website link: {e}")

async def handle_blacklisted_message(message):
    if message.id not in removed_messages:
        await message.reply("Your message contains blacklisted content and has been removed.")
        await message.delete()
        removed_messages.add(message.id)

        await asyncio.sleep(3)
        async for own_message in message.channel.history():
            if own_message.author == bot.user and own_message.id != message.id:
                await own_message.delete()

bot.run(TOKEN)
