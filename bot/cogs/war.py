from typing import List, Optional, Dict
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta

from bot.utils.config import config
from bot.utils.paginator import ActivityPaginator
from bot.utils.helpers import create_embed, format_number
from bot.handler import info, error, warning
from bot import data as get_data

class WarCog(commands.Cog):
    """Cog for war-related commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = config
    
    def format_war_info(self, war: Dict) -> str:
        """Format war information into a compact string."""
        attacker = war.get('attacker', {})
        defender = war.get('defender', {})
        
        # Basic war info
        info = [
            f"**War ID:** {war['id']}",
            f"**Type:** {war.get('war_type', 'N/A')}",
            f"**Turns Left:** {war.get('turns_left', 'N/A')}",
            f"**Reason:** {war.get('reason', 'N/A')}",
            "",
            f"**Attacker:** [{attacker.get('leader_name', 'N/A')}](https://politicsandwar.com/nation/id={attacker.get('id', '')})",
            f"**Defender:** [{defender.get('leader_name', 'N/A')}](https://politicsandwar.com/nation/id={defender.get('id', '')})",
            "",
            f"**Points:** {war.get('att_points', 0)} vs {war.get('def_points', 0)}",
            f"**Resistance:** {war.get('att_resistance', 0)}% vs {war.get('def_resistance', 0)}%",
            "",
            f"**Control:** {war.get('ground_control', 'None')} Ground | {war.get('air_superiority', 'None')} Air | {war.get('naval_blockade', 'None')} Naval"
        ]
        
        return "\n".join(info)
    
    @app_commands.command(name="war", description="Show active wars for a nation.")
    @app_commands.describe(
        nation_id="The ID of the nation to check wars for"
    )
    async def war(
        self,
        interaction: discord.Interaction,
        nation_id: int
    ):
        """Show active wars for a nation."""
        await interaction.response.defer()
        
        # Get active wars for the nation
        params = {
            "active": True,
            "nation_id": [nation_id],
            "first": 50
        }
        
        wars = get_data.GET_WARS(params, self.config.API_KEY)
        if not wars:
            await interaction.followup.send("No active wars found for this nation.", ephemeral=True)
            return
        
        # Format results
        results = [self.format_war_info(war) for war in wars]
        
        # Use paginator to display results
        paginator = ActivityPaginator(results)
        await interaction.followup.send(embed=paginator.get_embed(), view=paginator)
        
        info(f"War lookup completed by {interaction.user}", tag="WAR")

async def setup(bot: commands.Bot):
    """Set up the war cog."""
    await bot.add_cog(WarCog(bot)) 