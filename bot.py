
import os
import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import discord
from discord.ext import commands
from discord import app_commands

# ---------------- CONFIG ----------------

TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")
TIMEZONE_NAME = "America/New_York"
EASTERN = ZoneInfo(TIMEZONE_NAME)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("crack_an_egg_bot")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

countdown_tasks = {}

# ---------------- COUNTDOWN HELPERS ----------------

def format_countdown(seconds):
    seconds = max(0, int(seconds))
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    return f"{days}d {hours:02}h {minutes:02}m {seconds:02}s"


def countdown_message(release_time):
    now = datetime.now(EASTERN)
    remaining = (release_time - now).total_seconds()

    if remaining <= 0:
        return "🎉 **CRACK AN EGG IS NOW LIVE!**"

    return (
        "🥚 **CRACK AN EGG RELEASE COUNTDOWN**\n"
        f"⏳ Time remaining: **{format_countdown(remaining)}**\n"
        "🕒 Timezone: **America/New_York (Eastern Time)**"
    )


async def run_countdown(guild_id, channel_id, message_id, release_time):
    task = asyncio.current_task()

    try:
        channel = bot.get_channel(channel_id)

        if channel is None:
            channel = await bot.fetch_channel(channel_id)

        message = await channel.fetch_message(message_id)

        while True:
            now = datetime.now(EASTERN)
            remaining = (release_time - now).total_seconds()

            if remaining <= 0:
                await message.edit(
                    content="🎉 **CRACK AN EGG IS NOW LIVE!**"
                )
                await channel.send(
                    "@everyone 🎉 **CRACK AN EGG IS NOW LIVE!**",
                    allowed_mentions=discord.AllowedMentions(everyone=True)
                )
                break

            await message.edit(
                content=countdown_message(release_time),
                allowed_mentions=discord.AllowedMentions.none()
            )

            # Update once per second
            await asyncio.sleep(1)

    except asyncio.CancelledError:
        raise
    except Exception:
        logger.exception("Countdown failed for guild %s", guild_id)
    finally:
        if countdown_tasks.get(guild_id) is task:
            countdown_tasks.pop(guild_id, None)


# ---------------- BOT SETUP COMMAND ----------------

@bot.tree.command(
    name="setup",
    description="Create the Crack an Egg Discord server channels and roles"
)
@app_commands.guild_only()
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True, thinking=True)

    guild = interaction.guild

    role_names = ["Owner", "Admin", "Mod", "Member"]

    for role_name in role_names:
        if discord.utils.get(guild.roles, name=role_name) is None:
            await guild.create_role(name=role_name)

    categories = {
        "INFORMATION": [
            "welcome",
            "rules",
            "announcements",
            "updates",
            "codes"
        ],
        "COMMUNITY": [
            "general",
            "suggestions",
            "bug-reports",
            "media",
            "game-chat"
        ],
        "STAFF": [
            "staff-chat",
            "reports",
            "mod-logs"
        ]
    }

    for category_name, channel_names in categories.items():
        category = discord.utils.get(
            guild.categories,
            name=category_name
        )

        if category is None:
            category = await guild.create_category(category_name)

        for channel_name in channel_names:
            existing = discord.utils.get(
                guild.text_channels,
                name=channel_name
            )

            if existing is None:
                await guild.create_text_channel(
                    channel_name,
                    category=category
                )

        if category_name == "COMMUNITY":
            voice_name = "VC"
            existing_voice = discord.utils.get(
                guild.voice_channels,
                name=voice_name
            )

            if existing_voice is None:
                await guild.create_voice_channel(
                    voice_name,
                    category=category
                )

    await interaction.followup.send(
        "✅ Server setup completed! Existing channels and roles were kept.",
        ephemeral=True
    )


# ---------------- RELEASE COUNTDOWN COMMAND ----------------

@bot.tree.command(
    name="countdown",
    description="Post a live Crack an Egg release countdown"
)
@app_commands.guild_only()
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(
    channel="Channel where the countdown will appear",
    year="Release year (Eastern Time)",
    month="Release month (1-12)",
    day="Release day",
    hour="Release hour (24-hour time, Eastern Time)",
    minute="Release minute (Eastern Time)"
)
@app_commands.rename(
    year="year",
    month="month",
    day="day",
    hour="hour",
    minute="minute"
)
async def countdown(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    year: app_commands.Range[int, 2026, 2100],
    month: app_commands.Range[int, 1, 12],
    day: app_commands.Range[int, 1, 31],
    hour: app_commands.Range[int, 0, 23],
    minute: app_commands.Range[int, 0, 59]
):
    guild = interaction.guild

    if channel.guild.id != guild.id:
        await interaction.response.send_message(
            "❌ Choose a channel in this server.",
            ephemeral=True
        )
        return

    try:
        release_time = datetime(
            year, month, day, hour, minute,
            tzinfo=EASTERN
        )
    except ValueError:
        await interaction.response.send_message(
            "❌ That date is invalid. Check the month and day.",
            ephemeral=True
        )
        return

    if release_time <= datetime.now(EASTERN):
        await interaction.response.send_message(
            "❌ The release time must be in the future.",
            ephemeral=True
        )
        return

    bot_member = guild.get_member(bot.user.id)

    if bot_member is None:
        await interaction.response.send_message(
            "❌ I couldn't verify my server permissions. Try again.",
            ephemeral=True
        )
        return

    permissions = channel.permissions_for(bot_member)

    if not permissions.view_channel or not permissions.send_messages:
        await interaction.response.send_message(
            "❌ I need permission to view and send messages in that channel.",
            ephemeral=True
        )
        return

    if not permissions.read_message_history:
        await interaction.response.send_message(
            "❌ I also need Read Message History in that channel.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True, thinking=True)

    # Stop an existing countdown for this server, if one exists.
    old_task = countdown_tasks.get(guild.id)

    if old_task and not old_task.done():
        old_task.cancel()
        try:
            await old_task
        except asyncio.CancelledError:
            pass

    try:
        message = await channel.send(
            "@everyone\n" + countdown_message(release_time),
            allowed_mentions=discord.AllowedMentions(everyone=True)
        )
    except discord.Forbidden:
        await interaction.followup.send(
            "❌ I can't post there. Check my channel permissions.",
            ephemeral=True
        )
        return

    task = asyncio.create_task(
        run_countdown(
            guild.id,
            channel.id,
            message.id,
            release_time
        )
    )
    countdown_tasks[guild.id] = task

    await interaction.followup.send(
        f"✅ Countdown posted in {channel.mention}!\n"
        f"Release time: **{release_time.strftime('%B %d, %Y at %I:%M %p')} Eastern Time**\n"
        "The displayed countdown updates every second.",
        ephemeral=True
    )


# ---------------- STARTUP ----------------

@bot.event
async def on_ready():
    logger.info("Logged in as %s", bot.user)

    try:
        synced = await bot.tree.sync()
        logger.info("Synced %s slash commands.", len(synced))
    except Exception:
        logger.exception("Slash command sync failed")


async def main():
    if not TOKEN:
        raise RuntimeError(
            "Missing bot token. Set DISCORD_TOKEN or TOKEN in your host's environment variables."
        )

    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except ZoneInfoNotFoundError:
        raise RuntimeError(
            "Timezone database missing. Install tzdata: pip install tzdata"
        )
