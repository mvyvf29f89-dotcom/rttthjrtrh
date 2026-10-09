import discord
from discord.ext import commands
import os
import asyncio
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")

intents = discord.Intents.default()
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Active countdown tasks
countdown_tasks = {}


# ==========================================
# /setup
# ==========================================

@bot.tree.command(
    name="setup",
    description="Set up the Crack an Egg server"
)
async def setup(interaction: discord.Interaction):

    if interaction.guild is None:
        await interaction.response.send_message(
            "❌ This command can only be used in a server.",
            ephemeral=True
        )
        return

    if interaction.guild.owner_id != interaction.user.id:
        await interaction.response.send_message(
            "❌ Only the server owner can use this command.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    guild = interaction.guild

    roles = [
        ("Owner", discord.Colour.red()),
        ("Admin", discord.Colour.orange()),
        ("Mod", discord.Colour.blue()),
        ("Member", discord.Colour.green())
    ]

    created_roles = 0

    for role_name, colour in roles:
        existing_role = discord.utils.get(
            guild.roles, name=role_name
        )

        if existing_role is None:
            await guild.create_role(
                name=role_name,
                colour=colour,
                reason="Crack an Egg server setup"
            )
            created_roles += 1

    categories = {
        "📢 INFORMATION": [
            "👋・welcome",
            "📜・rules",
            "📢・announcements",
            "📰・updates",
            "🎁・codes"
        ],
        "💬 COMMUNITY": [
            "💬・general",
            "💡・suggestions",
            "🐛・bug-reports",
            "📸・media",
            "🎮・game-chat",
            "🔊・VC"
        ],
        "🛡️ STAFF": [
            "📋・staff-chat",
            "🚨・reports",
            "📑・mod-logs"
        ]
    }

    created_categories = 0
    created_channels = 0

    for category_name, channel_list in categories.items():
        category = discord.utils.get(
            guild.categories, name=category_name
        )

        if category is None:
            category = await guild.create_category(
                category_name,
                reason="Crack an Egg server setup"
            )
            created_categories += 1

        for channel_name in channel_list:
            existing_channel = discord.utils.get(
                guild.channels, name=channel_name
            )

            if existing_channel is not None:
                continue

            if channel_name == "🔊・VC":
                await guild.create_voice_channel(
                    channel_name,
                    category=category,
                    reason="Crack an Egg server setup"
                )
            else:
                await guild.create_text_channel(
                    channel_name,
                    category=category,
                    reason="Crack an Egg server setup"
                )

            created_channels += 1

    await interaction.followup.send(
        "🥚 **Crack an Egg setup complete!**\n\n"
        f"👑 Roles created: **{created_roles}**\n"
        f"📁 Categories created: **{created_categories}**\n"
        f"💬 Channels created: **{created_channels}**\n\n"
        "⚙️ **Permissions were NOT changed.**",
        ephemeral=True
    )


# ==========================================
# COUNTDOWN DISPLAY
# ==========================================

def format_countdown(seconds):
    seconds = max(0, int(seconds))

    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)

    return (
        f"**{days}** days · "
        f"**{hours}** hours · "
        f"**{minutes}** minutes · "
        f"**{secs}** seconds"
    )


def countdown_message(release_time, timezone_name):
    now = datetime.now(timezone.utc)
    remaining = (release_time - now).total_seconds()

    local_release = release_time.astimezone(
        ZoneInfo(timezone_name)
    )

    if remaining <= 0:
        return (
            "🥚 **CRACK AN EGG IS NOW LIVE!** 🎉\n\n"
            "The wait is over! Go play **Crack an Egg**!\n\n"
            f"🕒 Released: <t:{int(release_time.timestamp())}:F>"
        )

    return (
        "🥚 **CRACK AN EGG RELEASE COUNTDOWN** 🔥\n\n"
        "The game is almost here!\n\n"
        f"⏳ **Time remaining:**\n"
        f"{format_countdown(remaining)}\n\n"
        f"📅 **Release time:** <t:{int(release_time.timestamp())}:F>\n"
        f"🌎 **Timezone:** {timezone_name}\n\n"
        "Get ready to crack some eggs! 🥚"
    )


# ==========================================
# COUNTDOWN BACKGROUND TASK
# ==========================================

async def run_countdown(
    guild_id,
    channel_id,
    message_id,
    release_time,
    timezone_name
):
    try:
        channel = bot.get_channel(channel_id)

        if channel is None:
            channel = await bot.fetch_channel(channel_id)

        message = await channel.fetch_message(message_id)

        while True:
            now = datetime.now(timezone.utc)
            remaining = (release_time - now).total_seconds()

            if remaining <= 0:
                await channel.send(
                    "@everyone 🥚 **CRACK AN EGG IS NOW LIVE!** 🎉🔥\n\n"
                    "The countdown is over! Go play now!",
                    allowed_mentions=discord.AllowedMentions(
                        everyone=True
                    )
                )

                await message.edit(
                    content=countdown_message(
                        release_time, timezone_name
                    ),
                    allowed_mentions=discord.AllowedMentions.none()
                )
                break

            await message.edit(
                content=countdown_message(
                    release_time, timezone_name
                ),
                allowed_mentions=discord.AllowedMentions.none()
            )

            # Update every minute, then refresh more frequently
            # during the final minute.
            await asyncio.sleep(
                1 if remaining <= 60 else 60
            )

    except discord.NotFound:
        print(
            f"Countdown message for guild {guild_id} was deleted."
        )
    except discord.Forbidden:
        print(
            f"Missing permissions to update countdown in guild {guild_id}."
        )
    except Exception as error:
        print(f"Countdown error: {error}")
    finally:
        countdown_tasks.pop(guild_id, None)


# ==========================================
# /countdown
# ==========================================

@bot.tree.command(
    name="countdown",
    description="Post a countdown to the Crack an Egg release"
)
@app_commands.describe(
    channel="Channel where the countdown will be posted",
    year="Release year, e.g. 2026",
    month="Release month, 1-12",
    day="Release day",
    hour="Release hour in 24-hour time, 0-23",
    minute="Release minute, 0-59",
    timezone_name="Timezone, e.g. America/New_York"
)
async def countdown(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    year: int,
    month: int,
    day: int,
    hour: int,
    minute: int,
    timezone_name: str = "America/New_York"
):
    if interaction.guild is None:
        await interaction.response.send_message(
            "❌ Use this command inside your server.",
            ephemeral=True
        )
        return

    if not interaction.user.guild_permissions.manage_guild:
        await interaction.response.send_message(
            "❌ You need Manage Server permission to use this command.",
            ephemeral=True
        )
        return

    try:
        tz = ZoneInfo(timezone_name)
        local_release = datetime(
            year, month, day, hour, minute, tzinfo=tz
        )
        release_time = local_release.astimezone(timezone.utc)

    except (ValueError, ZoneInfoNotFoundError):
        await interaction.response.send_message(
            "❌ Invalid date, time, or timezone.\n"
            "Example timezone: `America/New_York`",
            ephemeral=True
        )
        return

    if release_time <= datetime.now(timezone.utc):
        await interaction.response.send_message(
            "❌ The release time must be in the future.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    # Stop the previous countdown in this server, if there is one.
    old_task = countdown_tasks.get(interaction.guild.id)

    if old_task is not None:
        old_task.cancel()

    # Post one @everyone ping when the countdown begins.
    message = await channel.send(
        "@everyone 🥚 **CRACK AN EGG RELEASE COUNTDOWN!** 🔥\n\n"
        + countdown_message(release_time, timezone_name),
        allowed_mentions=discord.AllowedMentions(
            everyone=True
        )
    )

    task = asyncio.create_task(
        run_countdown(
            interaction.guild.id,
            channel.id,
            message.id,
            release_time,
            timezone_name
        )
    )

    countdown_tasks[interaction.guild.id] = task

    await interaction.followup.send(
        f"✅ Countdown posted in {channel.mention}!\n"
        f"📅 Release: <t:{int(release_time.timestamp())}:F>\n"
        "🔔 Everyone was pinged.",
        ephemeral=True
    )


# Import required for slash-command descriptions.
from discord import app_commands


# ==========================================
# BOT READY
# ==========================================

@bot.event
async def on_ready():
    print("")
    print("================================")
    print(f"🥚 Logged in as: {bot.user}")
    print(f"🆔 Bot ID: {bot.user.id}")
    print("================================")

    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash command(s)")
        print("🥚 Crack an Egg bot is online!")
    except Exception as error:
        print("❌ Slash command sync failed:")
        print(error)


# ==========================================
# START BOT
# ==========================================

if not TOKEN:
    print("❌ BOT TOKEN NOT FOUND")
    print("Set DISCORD_TOKEN or TOKEN in Wispbyte.")
else:
    print("🔑 Bot token found.")
    print("🚀 Starting bot...")
    bot.run(TOKEN)
