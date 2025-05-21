import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone

from bot.utils.config import config
from bot.utils.helpers import create_embed
from bot.handler import info, error, warning

class UtilityCog(commands.Cog):
    """Cog for utility commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = config
    
    @app_commands.command(name="ping", description="Check the bot's latency.")
    async def ping(self, interaction: discord.Interaction):
        """Check the bot's latency."""
        try:
            latency = self.bot.latency * 1000
            info(f"Ping command executed by {interaction.user} in {interaction.channel}", tag="PING")
            
            await interaction.response.send_message(
                embed=create_embed(
                    title="Pong! 🏓",
                    description=f"Latency: {latency:,.2f} ms",
                    color=discord.Color.green()
                ),
                ephemeral=True
            )
        except Exception as e:
            error(f"Error in ping command: {e}")
            await interaction.response.send_message(
                embed=create_embed(
                    title="Error",
                    description="Failed to check latency",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
    
    @app_commands.command(name="help", description="Get help with the bot commands.")
    async def help(self, interaction: discord.Interaction):
        """Get help with the bot commands."""
        embed = create_embed(
            title="Help",
            description="Here are the available commands:",
            color=discord.Color.blue(),
            fields=[
                {"name": "/audit", "value": "Audit alliance members based on different criteria.", "inline": False},
                {"name": "/warchest", "value": "Calculate a nation's warchest requirements (5 days of upkeep).", "inline": False},
                {"name": "/bank", "value": "Check the bank balance of a nation.", "inline": False},
                {"name": "/wars", "value": "Check the active wars and military of a nation.", "inline": False},
                {"name": "/suggest", "value": "Suggest something to the bot.", "inline": False},
                {"name": "/report-a-bug", "value": "Report a bug to the bot.", "inline": False}
            ]
        )
        
        await interaction.response.send_message(embed=embed)
        info(f"Help command executed by {interaction.user} in {interaction.channel}", tag="HELP")

async def setup(bot: commands.Bot):
    """Set up the utility cog."""
    await bot.add_cog(UtilityCog(bot)) 