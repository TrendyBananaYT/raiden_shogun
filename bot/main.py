# Import Discord libraries
import discord
from discord import app_commands, AllowedMentions
from discord.ext import commands
from discord.ui import View, Button, Select

# Import standard libraries
from datetime import datetime, timezone
import pytz
import math
import random
import os
import asyncio
import json
import time
import traceback
import sys
from typing import Optional, List, Dict, Any

# Import custom modules
import calculate
import data as get_data
import vars as vars
import db as dataBase
from handler import debug, info, success, warning, error, fatal, missing_data, latency_check
from utils.config import config

# Constants
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")
ALLIANCE_ID = os.getenv("ALLIANCE_ID")

# Configuration
COSTS = vars.COSTS
MILITARY_COSTS = vars.MILITARY_COSTS

# Initialize bot with intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

async def check_latency():
    """Monitor bot latency."""
    while True:
        try:
            latency = bot.latency * 1000
            latency_check(latency, tag="LATENCY")

            await bot.change_presence(
                activity=discord.Game(name=f"Latency: {latency:,.2f}ms")
            )

            await asyncio.sleep(60)
        except Exception as e:
            error(f"Error in latency check: {e}", tag="LATENCY")
            await asyncio.sleep(60)  # Still wait before retrying

@bot.event
async def on_ready():
    """Event handler for when the bot is ready."""
    try:
        # Load cogs
        for cog in ["bot.cogs.audit", "bot.cogs.utility", "bot.cogs.nation", "bot.cogs.feedback", "bot.cogs.military", "bot.cogs.war"]:
            try:
                await bot.load_extension(cog)
                info(f"Successfully loaded extension: {cog}")
            except Exception as e:
                error(f"Failed to load extension {cog}: {e}")
                fatal(f"Extension load error details: {traceback.format_exc()}")
                raise  # Re-raise to prevent bot from starting with missing functionality
        
        # Sync commands
        try:
            synced = await bot.tree.sync()
            info(f"Successfully synced {len(synced)} commands")
        except Exception as e:
            error(f"Failed to sync commands: {e}")
            fatal(f"Command sync error details: {traceback.format_exc()}")
            raise  # Re-raise to prevent bot from starting with unsynced commands
        
        success(f"Bot is ready! Logged in as {bot.user} (ID: {bot.user.id})")
        
        # Start latency monitoring
        if not hasattr(bot, 'latency_task'):
            bot.latency_task = bot.loop.create_task(check_latency())
            info("Started latency monitoring task")
    except Exception as e:
        fatal(f"Critical error during bot startup: {e}")
        fatal(f"Startup error details: {traceback.format_exc()}")
        raise

@bot.event
async def on_error(event, *args, **kwargs):
    """Global error handler for all events."""
    error(f"Error in {event}: {sys.exc_info()}", tag="EVENT_ERROR")
    fatal(f"Event error details: {traceback.format_exc()}")

@bot.event
async def on_command_error(ctx, error):
    """Global error handler for all commands."""
    if isinstance(error, commands.CommandNotFound):
        warning(f"Command not found: {ctx.message.content}", tag="COMMAND")
        return
    
    if isinstance(error, commands.MissingPermissions):
        warning(f"Missing permissions for command: {ctx.message.content}", tag="PERMISSIONS")
        await ctx.send("You don't have permission to use this command.")
        return
    
    if isinstance(error, commands.MissingRequiredArgument):
        warning(f"Missing required argument for command: {ctx.message.content}", tag="ARGUMENTS")
        await ctx.send(f"Missing required argument: {error.param.name}")
        return
    
    error(f"Command error in {ctx.command}: {error}", tag="COMMAND_ERROR")
    fatal(f"Command error details: {traceback.format_exc()}")

def main():
    """Main entry point for the bot."""
    try:
        # Validate configuration before starting
        if not config.BOT_TOKEN:
            fatal("Bot token not found in configuration")
            sys.exit(1)
        
        if not config.API_KEY:
            fatal("API key not found in configuration")
            sys.exit(1)
        
        if not config.ALLIANCE_ID:
            fatal("Alliance ID not found in configuration")
            sys.exit(1)
        
        info("Starting bot...")
        bot.run(config.BOT_TOKEN)
    except discord.LoginFailure:
        fatal("Failed to login: Invalid bot token")
        sys.exit(1)
    except discord.HTTPException as e:
        fatal(f"HTTP error occurred: {e}")
        sys.exit(1)
    except Exception as e:
        fatal(f"Unexpected error during bot startup: {e}")
        fatal(f"Startup error details: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main()

