
import os
import asyncio
import logging
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import discord
from discord.ext import commands
from discord import app_commands

# ==========================================
# CONFIGURATION
# ==========================================

TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")

TIMEZONE_NAME = "America/New_York"
EASTERN = ZoneInfo(TIMEZONE_NAME)

# CRACK AN EGG RELEASE DATE
RELEASE_YEAR = 2026
RELEASE_MONTH = 10
RELEASE_DAY = 10
RELEASE_HOUR = 18  # 6:00 PM Eastern Time
RELEASE_MINUTE = 0

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("crack_an_egg_bot")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# One active countdown per server
countdown_tasks = {}


# ==========================================
# COUNTDOWN HELPERS
# ==========================================

def get_release_time():
    return datetime(
        RELEASE_YEAR,
        RELEASE_MONTH,
        RELEASE_DAY,
        RELEASE_HOUR,
        RELEASE_MINUTE,
        tzinfo=EASTERN
    )


def format_countdown(seconds):
    seconds = max(0, int(seconds))

    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    return (
        f"{days} DAYS • {hours:02} HOURS • "
        f"{minutes:02} MINUTES • {seconds:02} SECONDS"
    )


def countdown_message(release_time):
    now = datetime.now(EASTERN)
    remaining = (release_time - now).total_seconds()

    if remaining <= 0:
        return (
            "🚨🔥 **CRACK AN EGG IS HERE!!!** 🔥🚨\n\n"
            "🥚💥 **THE WAIT IS OVER!** 💥🥚\n"
            "🎮 IT'S TIME TO CRACK SOME EGGS!\n"
            "👑 GET YOUR SQUAD TOGETHER AND JUMP IN!\n\n"
            "🔥 **CRACK AN EGG IS OFFICIALLY LIVE!!!** 🔥"
        )

    return (
        "🥚━━━━━━━━━━━━━━━━━━━━🥚\n"
        "🚨🔥 **CRACK AN EGG RELEASE COUNTDOWN** 🔥🚨\n"
        "🥚━━━━━━━━━━━━━━━━━━━━🥚\n\n"
        "💥 **THE HYPE IS REAL. THE WAIT IS ALMOST OVER.** 💥\n\n"
        f"⏳ **{format_countdown(remaining)}**\n\n"
        "👀 GET READY TO CRACK SOME EGGS!\n"
        "🎮 GET YOUR FRIENDS. GET THE SQUAD READY.\n"
        "🔥 **WE'RE ABOUT TO GO CRAZY!** 🔥\n\n"
        "📅 **OCTOBER 10, 2026**\n"
        "🕕 **6:00 PM EASTERN TIME**\n\n"
        "🥚 **THE NEXT BIG ADVENTURE STARTS HERE!** 🥚"
    )


# ==========================================
# COUNTDOWN TASK
# ==========================================

async def run_countdown(guild_id, channel_id, message_id, release_time):
    task = asyncio.current_task()

    try:
        channel = bot.get_channel(channel_id)

        if channel is None:
            channel = await bot.fetch_channel(channel_id)

        message = await channel.fetch_message(message_id)

        while True:
            remaining = (
                release_time - datetime.now(EASTERN)
            ).total_seconds()

            if remaining <= 0:
                await message.edit(
                    content=countdown_message(release_time),
                    allowed_mentions=discord.AllowedMentions.none()
                )

                await channel.send(
                    "@everyone 🚨🔥 **CRACK AN EGG IS OFFICIALLY LIVE!!!** 🔥🥚\n"
                    "🎮 THE WAIT IS OVER! GET IN GAME NOW!",
                    allowed_mentions=discord.AllowedMentions(
                        everyone=True
                    )
                )
                break

            await message.edit(
                content=countdown_message(release_time),
                allowed_mentions=discord.AllowedMentions.none()
            )

            # Refresh the countdown every second.
            await asyncio.sleep(1)

    except asyncio.CancelledError:
        raise

    except discord.NotFound:
        logger.error(
            "Countdown message or channel was deleted in guild %s.",
            guild_id
        )

    except discord.Forbidden:
        logger.error(
            "Missing permissions to update the countdown in guild %s.",
            guild_id
        )

    except Exception:
        logger.exception("Countdown failed for guild %s.", guild_id)

    finally:
        if countdown_tasks.get(guild_id) is task:
            countdown_tasks.pop(guild_id, None)


# ==========================================
# /SETUP COMMAND
# ==========================================

@bot.tree.command(
    name="setup",
    description="Create the Crack an Egg Discord server channels and roles"
)
@app_commands.guild_only()
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    await interaction.response.defer(
        ephemeral=True,
        thinking=True
    )

    guild = interaction.guild

    for role_name in ["Owner", "Admin", "Mod", "Member"]:
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
            if discord.utils.get(
                guild.voice_channels,
                name="VC"
            ) is None:
                await guild.create_voice_channel(
                    "VC",
                    category=category
                )

    await interaction.followup.send(
        "✅ **Crack an Egg server setup completed!**\n"
        "Existing roles and channels were kept.",
        ephemeral=True
    )


# ==========================================
# /COUNTDOWN COMMAND
# ==========================================

@bot.tree.command(
    name="countdown",
    description="Post the Crack an Egg release countdown"
)
@app_commands.guild_only()
@app_commands.checks.has_permissions(manage_guild=True)
@app_commands.describe(
    channel="Channel where the countdown will appear"
)
async def countdown(
    interaction: discord.Interaction,
    channel: discord.TextChannel
):
    guild = interaction.guild
    release_time = get_release_time()

    if channel.guild.id != guild.id:
        await interaction.response.send_message(
            "❌ Choose a channel in this server.",
            ephemeral=True
        )
        return

    if release_time <= datetime.now(EASTERN):
        await interaction.response.send_message(
            "❌ October 10 at 6:00 PM Eastern has passed. "
            "Update the release date settings at the top of bot.py.",
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
            "❌ I need View Channel and Send Messages permissions.",
            ephemeral=True
        )
        return

    if not permissions.read_message_history:
        await interaction.response.send_message(
            "❌ I also need Read Message History permission.",
            ephemeral=True
        )
        return

    if not permissions.mention_everyone:
        await interaction.response.send_message(
            "❌ Give me the Mention @everyone permission in that channel.",
            ephemeral=True
        )
        return

    await interaction.response.defer(
        ephemeral=True,
        thinking=True
    )

    # Stop the previous countdown in this server.
    old_task = countdown_tasks.get(guild.id)

    if old_task and not old_task.done():
        old_task.cancel()

        try:
            await old_task
        except asyncio.CancelledError:
            pass

    try:
        # Ping everyone when the countdown is first posted.
        message = await channel.send(
            "@everyone\n" + countdown_message(release_time),
            allowed_mentions=discord.AllowedMentions(
                everyone=True
            )
        )

    except discord.Forbidden:
        await interaction.followup.send(
            "❌ Discord denied permission to post in that channel.",
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
        "✅ **HYPE COUNTDOWN POSTED!**\n"
        f"📢 Channel: {channel.mention}\n"
        "📅 October 10, 2026 at 6:00 PM Eastern Time\n"
        f"🕒 Timezone: `{TIMEZONE_NAME}`\n"
        "🔥 The countdown will update every second!",
        ephemeral=True
    )


# ==========================================
# ERROR HANDLING
# ==========================================

@setup.error
async def setup_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):
    if isinstance(error, app_commands.MissingPermissions):
        message = "❌ You need Administrator permission to use `/setup`."
    else:
        logger.error("Setup command failed: %s", error)
        message = "❌ Setup failed. Check the bot console for details."

    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


@countdown.error
async def countdown_error(
    interaction: discord.Interaction,
    error: app_commands.AppCommandError
):
    if isinstance(error, app_commands.MissingPermissions):
        message = "❌ You need Manage Server permission to use `/countdown`."
    else:
        logger.error("Countdown command failed: %s", error)
        message = "❌ Countdown failed. Check the bot console for details."

    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


# ==========================================
# STARTUP
# ==========================================

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
            "Missing bot token. Set DISCORD_TOKEN or TOKEN "
            "in your hosting environment variables."
        )

    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except ZoneInfoNotFoundError:
        raise RuntimeError(
            "Timezone database missing. Install it with: pip install tzdata"
        )
