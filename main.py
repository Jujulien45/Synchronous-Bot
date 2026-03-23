import discord
from discord.ext import commands
from cachetools import LRUCache
from dotenv import load_dotenv
import os

# Initialize bot with a command prefix
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

CHANEL_ID_1 = 1485674293160448123
CHANEL_ID_2 = 1485674218732650536

message_map = LRUCache(10_000)




@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

@bot.command()
async def ping(ctx):
    await ctx.send('pong')

@bot.event
async def on_message(message : discord.Message):
    if message.author == bot.user:
        return
    

    if message.channel.id == CHANEL_ID_1:
        target_channel = bot.get_channel(CHANEL_ID_2)
    elif message.channel.id == CHANEL_ID_2:
        target_channel = bot.get_channel(CHANEL_ID_1)
    else:
        return
    
    
    content = f"{message.guild.name}: De **{message.author.display_name}**.\n{message.content}"
    # Embeds
    embeds = message.embeds  # liste d'embeds déjà formatés

    # Fichiers/images
    files = []
    for attachment in message.attachments:
        files.append(await attachment.to_file())

    reply_to = None
    if message.reference and message.reference.message_id in message_map:
        mirrored_id = message_map[message.reference.message_id]
        try:
            reply_to = await target_channel.fetch_message(mirrored_id)
        except discord.NotFound:
            pass
    
    if reply_to:
        sent = await reply_to.reply(content=content, embeds=embeds, files=files)
    else:
        sent = await target_channel.send(content=content, embeds=embeds, files=files)



    message_map[message.id] = sent.id
    message_map[sent.id] = message.id


    await bot.process_commands(message)

@bot.event
async def on_reaction_add(reaction : discord.Reaction, user):
    if user.bot:
        return  # Ignore les réactions du bot lui-même

    if reaction.message.channel.id == CHANEL_ID_1:
        target_channel = bot.get_channel(CHANEL_ID_2)
    elif reaction.message.channel.id == CHANEL_ID_2:
        target_channel = bot.get_channel(CHANEL_ID_1)
    else:
        return

    react_to = None

    if reaction.message.id in message_map:
        mirrored_id = message_map[reaction.message.id]
        try:
            react_to = await target_channel.fetch_message(mirrored_id)
        except discord.NotFound:
            pass

    if react_to:
        await react_to.add_reaction(reaction.emoji)
    
    

# Run the bot with your token



load_dotenv("config.env")

token = os.getenv("DISCORD_TOKEN")


bot.run(token)
