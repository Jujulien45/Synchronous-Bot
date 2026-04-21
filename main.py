import discord
from discord import app_commands
from discord.ext import commands, tasks
from cachetools import LRUCache
from dotenv import load_dotenv
from datetime import time
import pytz
import os

# Initialize bot with a command prefix
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

CHANEL_ID_1 = 1485674293160448123
CHANEL_ID_2 = 1485674218732650536

message_map = LRUCache(10_000)

# Stored schedule: {guild_id: {"hour": int, "minute": int, "tz": str, "channel": int}}
schedules = {}
active_task = None


# ── Scheduling helpers ────────────────────────────────────────────────────────

def make_task(hour, minute, channel_id):
    tz = pytz.timezone("Europe/Brussels")
    target = time(hour=hour, minute=minute, tzinfo=tz)

    @tasks.loop(time=target)
    async def scheduled_message():
        channel = bot.get_channel(channel_id)
        if channel:
            discord.message.Me
            await channel.send(f"<576664068408999938>, Il est {hour:02d}:{minute:02d}, dans 5 min le cours d'info commence!")

    return scheduled_message


# ── Slash commands ────────────────────────────────────────────────────────────

@bot.tree.command(name="setschedule", description="Schedule a daily message at a specific time")
@app_commands.describe(
    hour="Hour in 24h format (0-23)",
    minute="Minute (0-59)",
    channel="Channel to send the message in"
)
async def set_schedule(
    interaction: discord.Interaction,
    hour: int,
    minute: int,
    channel: discord.TextChannel
):
    global active_task

    if not (0 <= hour <= 23):
        await interaction.response.send_message("❌ Hour must be between 0 and 23.", ephemeral=True)
        return
    if not (0 <= minute <= 59):
        await interaction.response.send_message("❌ Minute must be between 0 and 59.", ephemeral=True)
        return

    if active_task and active_task.is_running():
        active_task.cancel()

    active_task = make_task(hour, minute, channel.id)
    active_task.start()

    schedules[interaction.guild_id] = {
        "hour": hour, "minute": minute, "channel": channel.id
    }

    await interaction.response.send_message(
        f"✅ Scheduled! I'll send a message in {channel.mention} every day at **{hour:02d}:{minute:02d}**."
    )


@bot.tree.command(name="viewschedule", description="See the current scheduled message time")
async def view_schedule(interaction: discord.Interaction):
    schedule = schedules.get(interaction.guild_id)
    if not schedule:
        await interaction.response.send_message("📭 No schedule set. Use `/setschedule` to create one.", ephemeral=True)
        return

    channel = bot.get_channel(schedule["channel"])
    await interaction.response.send_message(
        f"📅 Current schedule: **{schedule['hour']:02d}:{schedule['minute']:02d}** in {channel.mention if channel else 'unknown channel'}."
    )


@bot.tree.command(name="stopschedule", description="Stop the scheduled daily message")
async def stop_schedule(interaction: discord.Interaction):
    global active_task
    if active_task and active_task.is_running():
        active_task.cancel()
        schedules.pop(interaction.guild_id, None)
        await interaction.response.send_message("🛑 Scheduled message stopped.")
    else:
        await interaction.response.send_message("⚠️ No schedule is currently running.", ephemeral=True)


# ── Bot events ────────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'Logged in as {bot.user.name}')


@bot.command()
async def ping(ctx):
    await ctx.send('pong')


@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    if message.channel.id == CHANEL_ID_1:
        target_channel = bot.get_channel(CHANEL_ID_2)
    elif message.channel.id == CHANEL_ID_2:
        target_channel = bot.get_channel(CHANEL_ID_1)
    else:
        await bot.process_commands(message)
        return

    content = f"{message.guild.name}: De **{message.author.display_name}**.\n{message.content}"
    embeds = message.embeds
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
async def on_reaction_add(reaction: discord.Reaction, user):
    if user.bot:
        return

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


# ── Run ───────────────────────────────────────────────────────────────────────

load_dotenv("config.env")
token = os.getenv("DISCORD_TOKEN")
bot.run(token)