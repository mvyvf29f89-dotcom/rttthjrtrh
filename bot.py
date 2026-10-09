import discord
from discord.ext import commands
import os

# Get the bot token from Wispbyte
# Supports either DISCORD_TOKEN or TOKEN
TOKEN = os.getenv("DISCORD_TOKEN") or os.getenv("TOKEN")

intents = discord.Intents.default()
intents.guilds = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)


# ==========================================
# /setup
# ==========================================

@bot.tree.command(
    name="setup",
    description="Set up the Crack an Egg server"
)
async def setup(interaction: discord.Interaction):

    # Make sure this is being used inside a server
    if interaction.guild is None:
        await interaction.response.send_message(
            "❌ This command can only be used in a server.",
            ephemeral=True
        )
        return

    # Only the server owner can use /setup
    if interaction.guild.owner_id != interaction.user.id:
        await interaction.response.send_message(
            "❌ Only the server owner can use this command.",
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=True)

    guild = interaction.guild

    # ==========================================
    # ROLES
    # ==========================================

    roles = [
        ("Owner", discord.Colour.red()),
        ("Admin", discord.Colour.orange()),
        ("Mod", discord.Colour.blue()),
        ("Member", discord.Colour.green())
    ]

    created_roles = 0

    for role_name, colour in roles:

        existing_role = discord.utils.get(
            guild.roles,
            name=role_name
        )

        if existing_role is None:

            await guild.create_role(
                name=role_name,
                colour=colour,
                reason="Crack an Egg server setup"
            )

            created_roles += 1

    # ==========================================
    # CATEGORIES + CHANNELS
    # ==========================================

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

    # ==========================================
    # CREATE CATEGORIES
    # ==========================================

    for category_name, channel_list in categories.items():

        category = discord.utils.get(
            guild.categories,
            name=category_name
        )

        # Create category if it doesn't exist
        if category is None:

            category = await guild.create_category(
                category_name,
                reason="Crack an Egg server setup"
            )

            created_categories += 1

        # ==========================================
        # CREATE CHANNELS
        # ==========================================

        for channel_name in channel_list:

            existing_channel = discord.utils.get(
                guild.channels,
                name=channel_name
            )

            # Don't duplicate existing channels
            if existing_channel is not None:
                continue

            # Voice channel
            if channel_name == "🔊・VC":

                await guild.create_voice_channel(
                    channel_name,
                    category=category,
                    reason="Crack an Egg server setup"
                )

            # Text channel
            else:

                await guild.create_text_channel(
                    channel_name,
                    category=category,
                    reason="Crack an Egg server setup"
                )

            created_channels += 1

    # ==========================================
    # FINISHED
    # ==========================================

    await interaction.followup.send(
        "🥚 **Crack an Egg setup complete!**\n\n"
        f"👑 Roles created: **{created_roles}**\n"
        f"📁 Categories created: **{created_categories}**\n"
        f"💬 Channels created: **{created_channels}**\n\n"
        "⚙️ **Permissions were NOT changed.**",
        ephemeral=True
    )


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

    print("")
    print("================================")
    print("❌ BOT TOKEN NOT FOUND")
    print("================================")
    print("Set one of these Wispbyte variables:")
    print("DISCORD_TOKEN")
    print("or")
    print("TOKEN")
    print("================================")

else:

    print("🔑 Bot token found.")
    print("🚀 Starting bot...")

    bot.run(TOKEN)