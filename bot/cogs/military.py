import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone
from typing import Dict, List, Optional

from bot.utils.config import config
from bot.utils.helpers import create_embed, format_number
from bot.utils.paginator import GridPaginator, PaginatorView
from bot.handler import info, error, warning
from bot import data as get_data
from bot import vars as vars

class MilitaryCog(commands.Cog):
    """Cog for military-related commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = config
        
        # MMR requirements for different roles
        self.mmr_requirements = {
            "Raider": {
                "barracks": 5,
                "factory": 0,
                "hangar": 5,
                "drydock": 0
            },
            "Whale": {
                "barracks": 0,
                "factory": 2,
                "hangar": 5,
                "drydock": 0
            }
        }
    
    def calculate_military_capacity(self, cities: List[Dict]) -> Dict[str, int]:
        """Calculate total military capacity from cities and research."""
        capacity = {
            "soldiers": 0,
            "tanks": 0,
            "aircraft": 0,
            "ships": 0
        }
        
        # Calculate from cities
        for city in cities:
            capacity["soldiers"] += city.get("barracks", 0) * 3000
            capacity["tanks"] += city.get("factory", 0) * 250
            capacity["aircraft"] += city.get("hangar", 0) * 15
            capacity["ships"] += city.get("drydock", 0) * 5
        
        return capacity
    
    def calculate_military_usage(self, nation: Dict) -> Dict[str, int]:
        """Get current military usage."""
        return {
            "soldiers": nation.get("soldiers", 0),
            "tanks": nation.get("tanks", 0),
            "aircraft": nation.get("aircraft", 0),
            "ships": nation.get("ships", 0)
        }
    
    def check_city_mmr(self, city: Dict, role: str) -> Dict[str, bool]:
        """Check if a city meets MMR requirements for a role."""
        requirements = self.mmr_requirements[role]
        return {
            "barracks": city.get("barracks", 0) >= requirements["barracks"],
            "factory": city.get("factory", 0) >= requirements["factory"],
            "hangar": city.get("hangar", 0) >= requirements["hangar"],
            "drydock": city.get("drydock", 0) >= requirements["drydock"]
        }
    
    def create_city_grid_items(self, cities: List[Dict], role: str) -> List[Dict[str, str]]:
        """Create grid items for city display."""
        items = []
        for city in cities:
            city_id = city.get("id")
            city_name = city.get("name", "Unknown")
            mmr_status = self.check_city_mmr(city, role)
            
            # Create status indicators
            status = []
            if not mmr_status["barracks"]:
                status.append(f"❌ B: {city.get('barracks', 0)}/{self.mmr_requirements[role]['barracks']}")
            if not mmr_status["factory"]:
                status.append(f"❌ F: {city.get('factory', 0)}/{self.mmr_requirements[role]['factory']}")
            if not mmr_status["hangar"]:
                status.append(f"❌ H: {city.get('hangar', 0)}/{self.mmr_requirements[role]['hangar']}")
            if not mmr_status["drydock"]:
                status.append(f"❌ D: {city.get('drydock', 0)}/{self.mmr_requirements[role]['drydock']}")
            
            # Create city link with status
            status_text = " | ".join(status) if status else "✅"
            city_link = f"[{city_name}](https://politicsandwar.com/city/id={city_id})" if city_id else city_name
            items.append({
                "content": f"{city_link}\n{status_text}"
            })
        
        return items
    
    @app_commands.command(name="military", description="Check a nation's military capacity and usage.")
    @app_commands.describe(nation_id="The ID of the nation to check.")
    async def military(self, interaction: discord.Interaction, nation_id: int):
        """Check a nation's military capacity and usage."""
        try:
            await interaction.response.defer()
            
            # Get nation and city data
            nation = get_data.GET_NATION_DATA(nation_id, self.config.API_KEY)
            if not nation:
                await interaction.followup.send("Nation not found.", ephemeral=True)
                return
                
            cities = get_data.GET_CITY_DATA(nation_id, self.config.API_KEY)
            if not cities:
                await interaction.followup.send("Could not fetch city data.", ephemeral=True)
                return
            
            # Calculate capacities and usage
            capacity = self.calculate_military_capacity(cities)
            usage = self.calculate_military_usage(nation)
            
            # Create city links
            city_links = []
            for city in cities:
                city_id = city.get("id")
                city_name = city.get("name", "Unknown")
                if city_id:
                    city_links.append(f"[{city_name}](https://politicsandwar.com/city/id={city_id})")
            
            # Create embed
            embed = create_embed(
                title=f"Military Status for {nation.get('nation_name', 'Unknown')}",
                description=(
                    f"Leader: {nation.get('leader_name', 'Unknown')}\n\n"
                    f"**Cities:** {', '.join(city_links)}"
                ),
                color=discord.Color.blue(),
                fields=[
                    {
                        "name": "Ground Forces",
                        "value": (
                            f"**Soldiers:** {format_number(usage['soldiers'])} / {format_number(capacity['soldiers'])}\n"
                            f"**Tanks:** {format_number(usage['tanks'])} / {format_number(capacity['tanks'])}"
                        ),
                        "inline": True
                    },
                    {
                        "name": "Air & Naval Forces",
                        "value": (
                            f"**Aircraft:** {format_number(usage['aircraft'])} / {format_number(capacity['aircraft'])}\n"
                            f"**Ships:** {format_number(usage['ships'])} / {format_number(capacity['ships'])}"
                        ),
                        "inline": True
                    },
                    {
                        "name": "Utilization",
                        "value": (
                            f"**Ground:** {format_number((usage['soldiers'] + usage['tanks']) / (capacity['soldiers'] + capacity['tanks']) * 100)}%\n"
                            f"**Air/Naval:** {format_number((usage['aircraft'] + usage['ships']) / (capacity['aircraft'] + capacity['ships']) * 100)}%"
                        ),
                        "inline": True
                    }
                ]
            )
            
            await interaction.followup.send(embed=embed)
            info(f"Military command executed for nation {nation_id} by {interaction.user}", tag="MILITARY")
            
        except Exception as e:
            error(f"Error in military command: {e}", tag="MILITARY")
            await interaction.followup.send("An error occurred while fetching military information.", ephemeral=True)
    
    @app_commands.command(name="mmr", description="Check a nation's MMR (Military Management Rating) status.")
    @app_commands.describe(nation_id="The ID of the nation to check.")
    async def mmr(self, interaction: discord.Interaction, nation_id: int):
        """Check a nation's MMR status."""
        try:
            await interaction.response.defer()
            
            # Get nation and city data
            nation = get_data.GET_NATION_DATA(nation_id, self.config.API_KEY)
            if not nation:
                await interaction.followup.send("Nation not found.", ephemeral=True)
                return
                
            cities = get_data.GET_CITY_DATA(nation_id, self.config.API_KEY)
            if not cities:
                await interaction.followup.send("Could not fetch city data.", ephemeral=True)
                return
            
            # Determine role based on city count
            role = "Whale" if len(cities) >= 15 else "Raider"
            
            # Create grid items for cities
            grid_items = self.create_city_grid_items(cities, role)
            
            # Create grid paginator
            paginator = GridPaginator(grid_items)
            embeds = paginator.get_embeds(
                title=f"MMR Status for {nation.get('nation_name', 'Unknown')}",
                description=(
                    f"**Role:** {role}\n"
                    f"**Cities:** {len(cities)}\n\n"
                    f"**Required MMR for {role}:**\n"
                    f"Barracks: {self.mmr_requirements[role]['barracks']}\n"
                    f"Factory: {self.mmr_requirements[role]['factory']}\n"
                    f"Hangar: {self.mmr_requirements[role]['hangar']}\n"
                    f"Drydock: {self.mmr_requirements[role]['drydock']}"
                ),
                color=discord.Color.blue()
            )
            
            # Create and send paginated view
            view = PaginatorView(embeds)
            await interaction.followup.send(embed=embeds[0], view=view)
            
            info(f"MMR command executed for nation {nation_id} by {interaction.user}", tag="MMR")
            
        except Exception as e:
            error(f"Error in MMR command: {e}", tag="MMR")
            await interaction.followup.send("An error occurred while checking MMR status.", ephemeral=True)

async def setup(bot: commands.Bot):
    """Set up the military cog."""
    await bot.add_cog(MilitaryCog(bot)) 