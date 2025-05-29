import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from typing import Dict, Optional
from bot.utils.helpers import create_embed
from bot.handler import info, error, warning
from bot import data as get_data

class UserCog(commands.Cog):
    """Cog for user-related commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = bot.config
        self.registrations_file = "data/registrations.json"
        self.ensure_registrations_file()
    
    def ensure_registrations_file(self):
        """Ensure the registrations file exists."""
        os.makedirs("data", exist_ok=True)
        if not os.path.exists(self.registrations_file):
            with open(self.registrations_file, "w") as f:
                json.dump({}, f)
    
    def load_registrations(self) -> Dict:
        """Load registrations from file."""
        try:
            with open(self.registrations_file, "r") as f:
                return json.load(f)
        except Exception as e:
            error(f"Error loading registrations: {e}", tag="USER")
            return {}
    
    def save_registrations(self, registrations: Dict):
        """Save registrations to file."""
        try:
            with open(self.registrations_file, "w") as f:
                json.dump(registrations, f, indent=4)
        except Exception as e:
            error(f"Error saving registrations: {e}", tag="USER")
    
    def get_user_nation(self, user_id: int) -> Optional[int]:
        """Get a user's registered nation ID."""
        registrations = self.load_registrations()
        user_data = registrations.get(str(user_id), {})
        return user_data.get('nation_id') if isinstance(user_data, dict) else user_data
    
    @app_commands.command(name="register", description="Register your Politics and War nation with your Discord account.")
    @app_commands.describe(nation_id="Your Politics and War nation ID")
    async def register(self, interaction: discord.Interaction, nation_id: int):
        """Register a user's PnW nation with their Discord account."""
        await interaction.response.defer()
        
        try:
            # Get nation data to verify the nation exists
            nation = get_data.GET_NATION_DATA(nation_id, self.config.API_KEY)
            if not nation:
                await interaction.followup.send(
                    embed=create_embed(
                        title=":warning: Nation Not Found",
                        description="Could not find a nation with that ID. Please check the ID and try again.",
                        color=discord.Color.red()
                    ),
                    ephemeral=True
                )
                return
            
            # Load current registrations
            registrations = self.load_registrations()
            
            # Check if this nation is already registered
            for user_id, user_data in registrations.items():
                reg_nation_id = user_data.get('nation_id') if isinstance(user_data, dict) else user_data
                if str(reg_nation_id) == str(nation_id):
                    await interaction.followup.send(
                        embed=create_embed(
                            title=":warning: Nation Already Registered",
                            description=f"This nation is already registered to <@{user_id}>.",
                            color=discord.Color.orange()
                        ),
                        ephemeral=True
                    )
                    return
            
            # Register the nation with user info
            registrations[str(interaction.user.id)] = {
                'nation_id': nation_id,
                'discord_name': str(interaction.user),
                'nation_name': nation['nation_name']
            }
            self.save_registrations(registrations)
            
            # Send confirmation
            await interaction.followup.send(
                embed=create_embed(
                    title=":white_check_mark: Registration Successful",
                    description=(
                        f"Successfully registered your nation:\n"
                        f"**Discord User:** {interaction.user}\n"
                        f"**Nation:** [{nation['nation_name']}](https://politicsandwar.com/nation/id={nation_id})\n"
                        f"**Leader:** {nation['leader_name']}"
                    ),
                    color=discord.Color.green()
                )
            )
            
            info(f"User {interaction.user} registered nation {nation_id}", tag="USER")
            
        except Exception as e:
            error(f"Error in register command: {e}", tag="USER")
            await interaction.followup.send(
                embed=create_embed(
                    title=":warning: Registration Failed",
                    description="An error occurred while registering your nation. Please try again later.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    """Set up the user cog."""
    await bot.add_cog(UserCog(bot)) 