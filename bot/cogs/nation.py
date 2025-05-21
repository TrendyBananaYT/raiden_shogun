import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone
import math
import json

from bot.utils.config import config
from bot.utils.helpers import create_embed, format_number
from bot.handler import info, error, warning
from bot import data as get_data
from bot import calculate
from bot import vars as vars

class NationCog(commands.Cog):
    """Cog for nation-related commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = config
    
    @app_commands.command(name="warchest", description="Calculate a nation's warchest requirements (5 days of upkeep).")
    @app_commands.describe(nation_id="Nation ID for which to calculate the warchest.")
    async def warchest(self, interaction: discord.Interaction, nation_id: int):
        """Calculate a nation's warchest requirements."""
        try:
            nation_info = get_data.GET_NATION_DATA(nation_id, self.config.API_KEY)
            
            info(f"Starting Warchest Calculation For: {nation_info.get('nation_name', 'N/A')} || https://politicsandwar.com/nation/id={nation_id} || By {interaction.user} In {interaction.channel}")
            
            result, excess, _ = calculate.warchest(nation_info, vars.COSTS, vars.MILITARY_COSTS)
            
            if result is None:
                error(f"Error calculating warchest for nation ID {nation_id}", tag="WARCH")
                await interaction.response.send_message("Error calculating warchest. Please check the nation ID.")
                return
            
            txt = f"""
            <:money:1357103044466184412> {format_number(result['money_deficit'])}
            <:coal:1357102730682040410>  {format_number(result['coal_deficit'])}
            <:Oil:1357102740391854140> {format_number(result['oil_deficit'])}
            <:uranium:1357102742799126558> {format_number(result['uranium_deficit'])}
            <:iron:1357102735488581643>  {format_number(result['iron_deficit'])}
            <:bauxite:1357102729411039254>  {format_number(result['bauxite_deficit'])}
            <:lead:1357102736646209536> {format_number(result['lead_deficit'])}
            <:gasoline:1357102734645399602>  {format_number(result['gasoline_deficit'])}
            <:munitions:1357102777389814012> {format_number(result['munitions_deficit'])}
            <:steel:1357105344052072618>  {format_number(result['steel_deficit'])}
            <:aluminum:1357102728391819356>  {format_number(result['aluminum_deficit'])}
            <:food:1357102733571784735>  {format_number(result['food_deficit'])}
            <:credits:1357102732187537459>  {format_number(result['credits_deficit'])} credits
            """
            
            # Only include resources that have a positive excess (more than 5 days worth)
            excess_resources = {k: v for k, v in excess.items() if v > 0}
            
            # Generate deposit URL only if there are excess resources
            if excess_resources:
                base_url = f"https://politicsandwar.com/alliance/id={self.config.ALLIANCE_ID}&display=bank&d_note=safekeepings"
                query_params = "&".join(
                    f"d_{key}={math.floor(value * 100) / 100}" for key, value in excess_resources.items()
                )
                deposit_url = f"{base_url}&{query_params}"
            else:
                deposit_url = None
            
            embed = create_embed(
                title=f':moneybag: Warchest for {nation_info.get("nation_name", "N/A")} "{nation_info.get("leader_name", "N/A")}"',
                description="Warchest for 60 Turns (5 Days)",
                color=discord.Color.purple(),
                fields=[
                    {"name": "Required On-Hand", "value": txt, "inline": False},
                ],
                footer="Maintained By Ivy"
            )
            
            # Only add deposit link if there are excess resources
            if deposit_url:
                embed.add_field(name="", value=f"[Deposit Excess]({deposit_url})", inline=False)
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            error(f"Error in warchest command: {e}", tag="WARCH")
            await interaction.response.send_message(
                embed=create_embed(
                    title=":warning: An Error Occurred",
                    description=(
                        f"**An unexpected error occurred while processing the command.**\n\n"
                        f"**Error Type:** `{type(e).__name__}`\n"
                        f"**Error Message:** {e}\n\n"
                        f"Detailed error information has been logged internally. Please contact <@860564164828725299> if this issue persists."
                    ),
                    color=discord.Color.red(),
                ),
                ephemeral=True
            )
    
    @app_commands.command(name="bank", description="Check the bank balance of a nation.")
    @app_commands.describe(nation_id="Nation ID to check.")
    async def bank(self, interaction: discord.Interaction, nation_id: int):
        """Check the bank balance of a nation."""
        nation = get_data.GET_NATION_DATA(nation_id, self.config.API_KEY)
        nation_name = nation.get("nation_name", "N/A")
        alliance = nation.get("alliance", {})
        alliance_name = alliance.get("name", "None")
        alliance_id = alliance.get("id", "N/A")
        
        header_info = (
            f"**{nation_name} of {alliance_name}**\n"
            f"Nation: {nation_id}-{nation_name} | Alliance: {alliance_name} (ID: {alliance_id})\n"
            f"Score: {nation.get('score', 'N/A')} | Pop: {nation.get('population', 'N/A')} | Leader: {nation.get('leader_name', 'N/A')}\n"
            f"{'-'*85}\n"
        )
        
        bank_balance = nation.get("bank_balance", {})
        bank_text = "\n".join([f"{key}: {value}" for key, value in bank_balance.items() if value > 0])
        
        if not bank_text:
            bank_text = "No funds available."
        
        output = header_info + "\n" + bank_text
        output = "\n" + output + "\n"
        
        await interaction.response.send_message(
            embed=create_embed(
                description=output,
                color=discord.Color.purple()
            )
        )
    
    @app_commands.command(name="wars", description="Check the active wars and military of a nation.")
    @app_commands.describe(nation_id="Nation ID to check.")
    async def wars(self, interaction: discord.Interaction, nation_id: int):
        """Check the active wars and military of a nation."""
        nation = get_data.GET_NATION_DATA(nation_id, self.config.API_KEY)
        nation_name = nation.get("nation_name", "N/A")
        alliance = nation.get("alliance", {})
        alliance_name = alliance.get("name", "None")
        alliance_id = alliance.get("id", "N/A")
        
        header_info = (
            f"**{nation_name} of {alliance_name}**\n"
            f"Nation: {nation_id}-{nation_name} | Alliance: {alliance_name} (ID: {alliance_id})\n"
            f"Score: {nation.get('score', 'N/A')} | Pop: {nation.get('population', 'N/A')} | Leader: {nation.get('leader_name', 'N/A')}\n"
            f"{'-'*85}\n"
        )
        
        wars_list = nation.get("wars", [])
        offensive_wars = []
        defensive_wars = []
        
        for war in wars_list:
            try:
                turns_left = int(war.get("turns_left", 0))
            except Exception:
                turns_left = 0
            if turns_left <= 0:
                continue
            attacker_id = int(war.get("attacker", {}).get("id", -1))
            defender_id = int(war.get("defender", {}).get("id", -1))
            if nation_id == attacker_id:
                offensive_wars.append(war)
            elif nation_id == defender_id:
                defensive_wars.append(war)
        
        offensive_wars = offensive_wars[:7]
        defensive_wars = defensive_wars[:3]
        
        def format_stats(nation):
            s = nation.get("soldiers", 0)
            t = nation.get("tanks", 0)
            a = nation.get("aircraft", 0)
            sh = nation.get("ships", 0)
            return f"🪖{s} 🚜{t} ✈️{a} 🚢{sh}"
        
        def format_control(war, is_offensive: bool):
            if is_offensive:
                gc = "AT" if war.get("ground_control", False) else "_"
                air = "AT" if war.get("air_superiority", False) else "_"
                nb = "AT" if war.get("naval_blockade", False) else "_"
                pc = "AT" if war.get("att_peace", False) else "_"
            else:
                gc = "DF" if war.get("ground_control", False) else "_"
                air = "DF" if war.get("air_superiority", False) else "_"
                nb = "DF" if war.get("naval_blockade", False) else "_"
                pc = "DF" if war.get("def_peace", False) else "_"
            return f"{gc} {air} {nb} {pc}"
        
        def format_offensive_line(war):
            defender = war.get("defender", {})
            opp = f"{defender.get('id', 'N/A')}"
            opp = opp[:12]
            our_stats = format_stats(war.get("attacker", {}))
            opp_stats = format_stats(defender)
            ctrl = format_control(war, True)
            line = f"{opp:<12} | {opp_stats:<12} | {our_stats:<12} | {ctrl}"
            return line[:85]
        
        def format_defensive_line(war):
            attacker = war.get("attacker", {})
            opp = f"{attacker.get('id', 'N/A')}-{attacker.get('nation_name', 'Unknown')}"
            opp = opp[:12]
            our_stats = format_stats(war.get("defender", {}))
            opp_stats = format_stats(attacker)
            ctrl = format_control(war, False)
            line = f"{opp:<12} | {our_stats:<12} | {opp_stats:<12} {ctrl}"
            return line[:85]
        
        def build_section(wars, is_offensive: bool, title: str):
            if not wars:
                return f"{title}:\nNo active wars."
            lines = [f"{title}:"]
            for war in wars:
                if is_offensive:
                    lines.append(format_offensive_line(war))
                else:
                    lines.append(format_defensive_line(war))
            return "\n".join(lines)
        
        off_text = build_section(offensive_wars, True, "Offensive Wars")
        def_text = build_section(defensive_wars, False, "Defensive Wars")
        
        output = header_info + "\n" + off_text + "\n\n" + def_text
        output = "\n" + output + "\n"
        
        await interaction.response.send_message(
            embed=create_embed(
                description=output,
                color=discord.Color.purple()
            )
        )

    @app_commands.command(name="who", description="Show basic information about a nation.")
    @app_commands.describe(
        nation_id="The ID of the nation to look up"
    )
    async def who(
        self,
        interaction: discord.Interaction,
        nation_id: int
    ):
        """Show basic information about a nation."""
        await interaction.response.defer()
        
        try:
            # Get nation data
            nation = get_data.GET_NATION_DATA(nation_id, self.config.API_KEY)
            if not nation:
                await interaction.followup.send("Nation not found.", ephemeral=True)
                return
            
            # Get city data
            cities = get_data.GET_CITY_DATA(nation_id, self.config.API_KEY)
            if not cities:
                await interaction.followup.send("Could not fetch city data.", ephemeral=True)
                return
            
            # Calculate total infrastructure and land
            total_infra = sum(city.get('infrastructure', 0) for city in cities)
            total_land = sum(city.get('land', 0) for city in cities)
            
            # Get continent resources
            continent = nation.get('continent', '').lower()
            continent_resources = {
                'africa': {'oil': 3, 'bauxite': 3, 'uranium': 3},
                'antarctica': {'oil': 3, 'coal': 3, 'uranium': 3},
                'asia': {'oil': 3, 'iron': 3, 'uranium': 3},
                'australia': {'coal': 3, 'bauxite': 3, 'lead': 3},
                'europe': {'coal': 3, 'iron': 3, 'lead': 3},
                'north america': {'coal': 3, 'iron': 3, 'uranium': 3},
                'south america': {'oil': 3, 'bauxite': 3, 'lead': 3}
            }
            
            # Calculate resource production from buildings and continent
            resource_production = {
                'coal': sum(city.get('coal_mine', 0) * 3 for city in cities),  # 3 per day per mine
                'oil': sum(city.get('oil_refinery', 0) * 3 for city in cities),  # 3 per day per refinery
                'uranium': sum(city.get('uranium_mine', 0) * 3 for city in cities),  # 3 per day per mine
                'iron': sum(city.get('iron_mine', 0) * 3 for city in cities),  # 3 per day per mine
                'bauxite': sum(city.get('bauxite_mine', 0) * 3 for city in cities),  # 3 per day per mine
                'lead': sum(city.get('lead_mine', 0) * 3 for city in cities),  # 3 per day per mine
                'gasoline': sum(city.get('oil_refinery', 0) * 6 for city in cities),  # 6 per day per refinery
                'munitions': sum(city.get('munitions_factory', 0) * 18 for city in cities),  # 18 per day per factory
                'steel': sum(city.get('steel_mill', 0) * 9 for city in cities),  # 9 per day per mill
                'aluminum': sum(city.get('aluminum_refinery', 0) * 9 for city in cities),  # 9 per day per refinery
                'food': sum(city.get('farm', 0) * (city.get('land', 0) / 500) for city in cities)  # Land/500 per farm
            }
            
            # Add continent resource production
            if continent in continent_resources:
                for resource, amount in continent_resources[continent].items():
                    resource_production[resource] += amount * len(cities)  # Each city gets the continent bonus
            
            # Get top 3 resource productions
            top_resources = sorted(resource_production.items(), key=lambda x: x[1], reverse=True)[:3]
            
            # Get color block based on color
            color = nation.get('color', 'gray').lower()
            color_block = {
                'red': '🟥',
                'orange': '🟧',
                'yellow': '🟨',
                'green': '🟩',
                'blue': '🟦',
                'purple': '🟪',
                'pink': '💗',
                'gray': '⬜',
                'black': '⬛',
                'brown': '🟫'
            }.get(color, '⬜')
            
            # Format basic info
            nation_info = [
                f"**[{nation.get('nation_name', 'N/A')}](https://politicsandwar.com/nation/id={nation_id})**",
                f"👑 **Leader:** {nation.get('leader_name', 'N/A')}",
                f"⭐ **Score:** {nation.get('score', 0):,.2f}",
                f"🏙️ **Cities:** {len(cities)}",
                f"<:population:1357366133233029413> **Population:** {format_number(nation.get('population', 0))}",
                f"**Total Infrastructure:** {format_number(total_infra)}",
                f"**Total Land:** {format_number(total_land)}",
                f"**Color:** {color_block}",
                "",
                f"**Military:**",
                f"<:military_helmet:1357103044466184412> Soldiers: {format_number(nation.get('soldiers', 0))}",
                f"<:tank:1357398163442635063> Tanks: {format_number(nation.get('tanks', 0))}",
                f":airplane: Aircraft: {format_number(nation.get('aircraft', 0))}",
                f":ship: Ships: {format_number(nation.get('ships', 0))}",
                "",
                f"**Top Resource Production:**",
            ]
            
            # Add top 3 resources with their emojis
            resource_emojis = {
                'coal': '<:coal:1357102730682040410>',
                'oil': '<:Oil:1357102740391854140>',
                'uranium': '<:uranium:1357102742799126558>',
                'iron': '<:iron:1357102735488581643>',
                'bauxite': '<:bauxite:1357102729411039254>',
                'lead': '<:lead:1357102736646209536>',
                'gasoline': '<:gasoline:1357102734645399602>',
                'munitions': '<:munitions:1357102777389814012>',
                'steel': '<:steel:1357105344052072618>',
                'aluminum': '<:aluminum:1357102728391819356>',
                'food': '<:food:1357102733571784735>'
            }
            
            for resource, amount in top_resources:
                if amount > 0:  # Only show resources with production
                    emoji = resource_emojis.get(resource, '')
                    nation_info.append(f"{emoji} {resource.title()}: {format_number(amount)}/day")
            
            nation_info.extend([
                "",
                f"**Alliance:** {nation.get('alliance', {}).get('name', 'No Alliance')}",
                f"**Last Active:** <t:{int(datetime.fromisoformat(nation.get('last_active', datetime.now(timezone.utc).isoformat()).replace('Z', '+00:00')).timestamp())}:R>"
            ])
            
            # Create embed
            embed = create_embed(
                title=f"Nation Information",
                description="\n".join(nation_info),
                color=discord.Color.blue(),
            )
            
            # Add nation flag as thumbnail
            if nation.get('flag'):
                embed.set_thumbnail(url=nation['flag'])
            
            await interaction.followup.send(embed=embed)
            info(f"Nation lookup completed by {interaction.user}", tag="WHO")
            
        except Exception as e:
            error(f"Error in who command: {e}", tag="WHO")
            await interaction.followup.send(
                embed=create_embed(
                    title=":warning: An Error Occurred",
                    description=(
                        f"**An unexpected error occurred while processing the command.**\n\n"
                        f"**Error Type:** `{type(e).__name__}`\n"
                        f"**Error Message:** {e}\n\n"
                        f"Detailed error information has been logged internally. Please contact <@860564164828725299> if this issue persists."
                    ),
                    color=discord.Color.red(),
                ),
                ephemeral=True
            )

    @app_commands.command(name="income", description="Show detailed economic information about a nation.")
    @app_commands.describe(
        nation_id="The ID of the nation to look up"
    )
    async def income(
        self,
        interaction: discord.Interaction,
        nation_id: int
    ):
        """Show detailed economic information about a nation."""
        await interaction.response.defer()
        
        try:
            # Get nation data
            nation = get_data.GET_NATION_DATA(nation_id, self.config.API_KEY)
            if not nation:
                await interaction.followup.send("Nation not found.", ephemeral=True)
                return
            
            # Get city data
            cities = get_data.GET_CITY_DATA(nation_id, self.config.API_KEY)
            if not cities:
                await interaction.followup.send("Could not fetch city data.", ephemeral=True)
                return
            
            # Calculate total infrastructure and land
            total_infra = sum(city.get('infrastructure', 0) for city in cities)
            total_land = sum(city.get('land', 0) for city in cities)
            
            # Calculate resource production from buildings
            resource_production = {
                'coal': sum(city.get('coal_mine', 0) * 3 for city in cities),  # 3 per day per mine
                'oil': sum(city.get('oil_refinery', 0) * 3 for city in cities),  # 3 per day per refinery
                'uranium': sum(city.get('uranium_mine', 0) * 3 for city in cities),  # 3 per day per mine
                'iron': sum(city.get('iron_mine', 0) * 3 for city in cities),  # 3 per day per mine
                'bauxite': sum(city.get('bauxite_mine', 0) * 3 for city in cities),  # 3 per day per mine
                'lead': sum(city.get('lead_mine', 0) * 3 for city in cities),  # 3 per day per mine
                'gasoline': sum(city.get('oil_refinery', 0) * 6 for city in cities),  # 6 per day per refinery
                'munitions': sum(city.get('munitions_factory', 0) * 18 for city in cities),  # 18 per day per factory
                'steel': sum(city.get('steel_mill', 0) * 9 for city in cities),  # 9 per day per mill
                'aluminum': sum(city.get('aluminum_refinery', 0) * 9 for city in cities),  # 9 per day per refinery
                'food': sum(city.get('farm', 0) * (city.get('land', 0) / 500) for city in cities)  # Land/500 per farm
            }
            
            # Calculate commerce income
            commerce_income = 0
            commerce_bonus = 0
            
            for city in cities:
                infra = city.get('infrastructure', 0)
                # Base commerce income is $2 per infrastructure
                base_income = infra * 2
                
                # Calculate improvement bonuses
                improvement_bonus = (
                    city.get('supermarket', 0) * 0.03 +  # +3% per supermarket
                    city.get('bank', 0) * 0.05 +        # +5% per bank
                    city.get('shopping_mall', 0) * 0.09 +  # +9% per mall
                    city.get('stadium', 0) * 0.12 +     # +12% per stadium
                    city.get('subway', 0) * 0.08        # +8% per subway
                )
                
                # Add city's commerce income with its bonuses
                commerce_income += base_income * (1 + improvement_bonus)
                commerce_bonus += improvement_bonus
            
            # Calculate average commerce bonus
            avg_commerce_bonus = commerce_bonus / len(cities) if cities else 0
            
            # Format economic info
            economic_info = [
                f"**{nation.get('nation_name', 'N/A')}**",
                f"**Cities:** {len(cities)}",
                f"**Total Infrastructure:** {format_number(total_infra)}",
                f"**Total Land:** {format_number(total_land)}",
                "",
                f"**Commerce Income:**",
                f"<:money:1357103044466184412> Base Income: ${format_number(total_infra * 2)}/day",
                f"<:money:1357103044466184412> Average Commerce Bonus: +{avg_commerce_bonus*100:.1f}%",
                f"<:money:1357103044466184412> Total Commerce: ${format_number(commerce_income)}/day",
                "",
                f"**Resource Production:**",
                f"<:coal:1357102730682040410> Coal: {format_number(resource_production['coal'])}/day",
                f"<:Oil:1357102740391854140> Oil: {format_number(resource_production['oil'])}/day",
                f"<:uranium:1357102742799126558> Uranium: {format_number(resource_production['uranium'])}/day",
                f"<:iron:1357102735488581643> Iron: {format_number(resource_production['iron'])}/day",
                f"<:bauxite:1357102729411039254> Bauxite: {format_number(resource_production['bauxite'])}/day",
                f"<:lead:1357102736646209536> Lead: {format_number(resource_production['lead'])}/day",
                f"<:gasoline:1357102734645399602> Gasoline: {format_number(resource_production['gasoline'])}/day",
                f"<:munitions:1357102777389814012> Munitions: {format_number(resource_production['munitions'])}/day",
                f"<:steel:1357105344052072618> Steel: {format_number(resource_production['steel'])}/day",
                f"<:aluminum:1357102728391819356> Aluminum: {format_number(resource_production['aluminum'])}/day",
                f"<:food:1357102733571784735> Food: {format_number(resource_production['food'])}/day"
            ]
            
            # Create embed
            embed = create_embed(
                title=f"Economic Information",
                description="\n".join(economic_info),
                color=discord.Color.green()
            )
            
            await interaction.followup.send(embed=embed)
            info(f"Economic lookup completed by {interaction.user}", tag="INCOME")
            
        except Exception as e:
            error(f"Error in income command: {e}", tag="INCOME")
            await interaction.followup.send(
                embed=create_embed(
                    title=":warning: An Error Occurred",
                    description=(
                        f"**An unexpected error occurred while processing the command.**\n\n"
                        f"**Error Type:** `{type(e).__name__}`\n"
                        f"**Error Message:** {e}\n\n"
                        f"Detailed error information has been logged internally. Please contact <@860564164828725299> if this issue persists."
                    ),
                    color=discord.Color.red()
                ),
                ephemeral=True
            )

    @app_commands.command(name="build", description="Generate an optimized build plan for a nation.")
    @app_commands.describe(
        nation_id="The ID of the nation to generate a build for",
        infra_target="Target infrastructure level (defaults to first city's infra)",
        barracks="Number of barracks (0-5, default based on MMR)",
        factories="Number of factories (0-5, default based on MMR)",
        hangars="Number of hangars (0-5, default based on MMR)",
        drydocks="Number of drydocks (0-3, default based on MMR)"
    )
    async def build(
        self,
        interaction: discord.Interaction,
        nation_id: int,
        infra_target: int = None,
        barracks: int = None,
        factories: int = None,
        hangars: int = None,
        drydocks: int = None
    ):
        """Generate an optimized build plan for a nation."""
        await interaction.response.defer()
        
        try:
            # Get nation data
            nation = get_data.GET_NATION_DATA(nation_id, self.config.API_KEY)
            if not nation:
                await interaction.followup.send("Nation not found.", ephemeral=True)
                return
            
            # Get city data
            cities = get_data.GET_CITY_DATA(nation_id, self.config.API_KEY)
            if not cities:
                await interaction.followup.send("Could not fetch city data.", ephemeral=True)
                return
            
            # Set default infra target to first city's infra if not specified
            if infra_target is None and cities:
                infra_target = cities[0].get('infrastructure', 2000)
            
            # Define default military configurations
            default_military = {
                'whale': {'barracks': 0, 'factories': 2, 'hangars': 5, 'drydocks': 0},
                'raider': {'barracks': 0, 'factories': 5, 'hangars': 5, 'drydocks': 0},
                'default': {'barracks': 0, 'factories': 0, 'hangars': 0, 'drydocks': 0}
            }
            
            # Get MMR type based on city count or custom values
            mmr_type = 'default'
            city_count = len(cities)
            
            if barracks is not None or factories is not None or hangars is not None or drydocks is not None:
                mmr_type = f"CUSTOM ({barracks or 0}/{factories or 0}/{hangars or 0}/{drydocks or 0})"
            elif city_count >= 15:
                mmr_type = 'whale'
            elif city_count > 0:
                mmr_type = 'raider'
            
            military_config = default_military.get(mmr_type, default_military['default'])
            
            # Get continent and determine natural resources
            continent = nation.get('continent', '').lower()
            continent_resources = {
                'na': {'coal': 3, 'iron': 3, 'uranium': 3},
                'sa': {'oil': 3, 'bauxite': 3, 'lead': 3},
                'as': {'oil': 3, 'iron': 3, 'uranium': 3},
                'an': {'oil': 3, 'coal': 3, 'uranium': 3},
                'eu': {'coal': 3, 'iron': 3, 'lead': 3},
                'af': {'oil': 3, 'bauxite': 3, 'uranium': 3},
                'au': {'coal': 3, 'bauxite': 3, 'lead': 3}
            }
            
            # Calculate improvements needed based on infrastructure
            imp_total = infra_target // 50  # 1 improvement per 50 infrastructure
            
            # Initialize build plan and improvement counter
            build_plan = {
                "infra_needed": infra_target,
                "imp_total": imp_total,
                "imp_coalpower": 0,
                "imp_oilpower": 0,
                "imp_windpower": 0,
                "imp_nuclearpower": 0,
                "imp_coalmine": 0,
                "imp_oilwell": 0,
                "imp_uramine": 0,
                "imp_leadmine": 0,
                "imp_ironmine": 0,
                "imp_bauxitemine": 0,
                "imp_farm": 0,
                "imp_gasrefinery": 0,
                "imp_aluminumrefinery": 0,
                "imp_munitionsfactory": 0,
                "imp_steelmill": 0,
                "imp_policestation": 0,
                "imp_hospital": 0,
                "imp_recyclingcenter": 0,
                "imp_subway": 0,
                "imp_supermarket": 0,
                "imp_bank": 0,
                "imp_mall": 0,
                "imp_stadium": 0,
                "imp_barracks": barracks if barracks is not None else military_config['barracks'],
                "imp_factory": factories if factories is not None else military_config['factories'],
                "imp_hangars": hangars if hangars is not None else military_config['hangars'],
                "imp_drydock": drydocks if drydocks is not None else military_config['drydocks']
            }
            
            # Track used improvements separately
            used_improvements = 0
            
            # Validate military building counts
            build_plan["imp_barracks"] = max(0, min(5, build_plan["imp_barracks"]))
            build_plan["imp_factory"] = max(0, min(5, build_plan["imp_factory"]))
            build_plan["imp_hangars"] = max(0, min(5, build_plan["imp_hangars"]))
            build_plan["imp_drydock"] = max(0, min(3, build_plan["imp_drydock"]))
            
            # Add military improvements to used count
            used_improvements += (
                build_plan["imp_barracks"] +
                build_plan["imp_factory"] +
                build_plan["imp_hangars"] +
                build_plan["imp_drydock"]
            )
            
            # Calculate required power and uranium
            power_needed = infra_target // 500  # Each power plant provides 500 infra
            uranium_needed = 0
            
            # Power plants (prioritize nuclear for high infra)
            if infra_target >= 2000:
                build_plan["imp_nuclearpower"] = 1  # Nuclear power plant for 2000 infra
                used_improvements += 1
                uranium_needed = 2  # 2 uranium mines needed for nuclear power plant (2.4 uranium per 1000 infra)
            else:
                # Use continent's natural resources for power
                if continent in continent_resources:
                    if 'coal' in continent_resources[continent]:
                        build_plan["imp_coalpower"] = power_needed
                        used_improvements += power_needed
                    elif 'oil' in continent_resources[continent]:
                        build_plan["imp_oilpower"] = power_needed
                        used_improvements += power_needed
            
            # Essential civil improvements
            build_plan["imp_policestation"] = 1    # Crime reduction
            build_plan["imp_hospital"] = 1         # Disease reduction
            build_plan["imp_recyclingcenter"] = 1  # Pollution reduction
            build_plan["imp_subway"] = 1           # Commerce + pollution reduction
            used_improvements += 4  # Add all civil improvements
            
            # Calculate remaining improvements
            remaining_imp = imp_total - used_improvements
            
            # Commerce improvements (prioritize highest bonus, cap at 100%)
            if remaining_imp > 0:
                max_commerce = 1.0  # 100% commerce cap
                current_commerce = 0
                
                # Prioritize stadiums (12% commerce)
                if current_commerce < max_commerce:
                    stadiums = min(remaining_imp, 3)
                    stadium_bonus = stadiums * 0.12
                    if current_commerce + stadium_bonus > max_commerce:
                        stadiums = int((max_commerce - current_commerce) / 0.12)
                    build_plan["imp_stadium"] = stadiums
                    remaining_imp -= stadiums
                    used_improvements += stadiums
                    current_commerce += stadium_bonus
                
                # Then malls (9% commerce)
                if remaining_imp > 0 and current_commerce < max_commerce:
                    malls = min(remaining_imp, 4)
                    mall_bonus = malls * 0.09
                    if current_commerce + mall_bonus > max_commerce:
                        malls = int((max_commerce - current_commerce) / 0.09)
                    build_plan["imp_mall"] = malls
                    remaining_imp -= malls
                    used_improvements += malls
                    current_commerce += mall_bonus
                
                # Then banks (5% commerce)
                if remaining_imp > 0 and current_commerce < max_commerce:
                    banks = min(remaining_imp, 5)
                    bank_bonus = banks * 0.05
                    if current_commerce + bank_bonus > max_commerce:
                        banks = int((max_commerce - current_commerce) / 0.05)
                    build_plan["imp_bank"] = banks
                    remaining_imp -= banks
                    used_improvements += banks
                    current_commerce += bank_bonus
                
                # No supermarkets in 0345 build plan
                build_plan["imp_supermarket"] = 0
            
            # Resource buildings based on continent (only if we have remaining improvements)
            if remaining_imp > 0 and continent in continent_resources:
                # First add uranium mines if needed for nuclear power
                if uranium_needed > 0 and 'uranium' in continent_resources[continent]:
                    # If we're using nuclear power, prioritize maxing uranium mines first
                    if build_plan["imp_nuclearpower"] > 0:
                        uranium_mines = min(remaining_imp, 5)  # Max 5 uranium mines
                        build_plan["imp_uramine"] = uranium_mines
                        remaining_imp -= uranium_mines
                        used_improvements += uranium_mines
                    else:
                        uranium_mines = min(uranium_needed, remaining_imp, 5)  # Just enough for power
                        build_plan["imp_uramine"] = uranium_mines
                        remaining_imp -= uranium_mines
                        used_improvements += uranium_mines
                
                # Then prioritize one resource type to maximize for 50% bonus
                # Choose the resource with the highest max limit
                resource_limits = {
                    'coal': 10,  # Max 10 coal mines
                    'oil': 10,   # Max 10 oil wells
                    'iron': 10,  # Max 10 iron mines
                    'bauxite': 10,  # Max 10 bauxite mines
                    'lead': 10,  # Max 10 lead mines
                    'uranium': 5   # Max 5 uranium mines
                }
                
                # Get available resources for this continent
                available_resources = [r for r in continent_resources[continent].keys() if r in resource_limits]
                
                if available_resources:
                    # If we're using nuclear power, prioritize uranium first
                    if build_plan["imp_nuclearpower"] > 0 and 'uranium' in available_resources:
                        best_resource = 'uranium'
                    else:
                        # Choose the resource with the highest max limit that we can fully build
                        best_resource = max(available_resources, key=lambda r: resource_limits[r])
                    
                    max_buildings = resource_limits[best_resource]
                    
                    if best_resource == 'coal':
                        build_plan["imp_coalmine"] = min(remaining_imp, max_buildings)
                        remaining_imp -= build_plan["imp_coalmine"]
                        used_improvements += build_plan["imp_coalmine"]
                    elif best_resource == 'oil':
                        build_plan["imp_oilwell"] = min(remaining_imp, max_buildings)
                        remaining_imp -= build_plan["imp_oilwell"]
                        used_improvements += build_plan["imp_oilwell"]
                    elif best_resource == 'iron':
                        build_plan["imp_ironmine"] = min(remaining_imp, max_buildings)
                        remaining_imp -= build_plan["imp_ironmine"]
                        used_improvements += build_plan["imp_ironmine"]
                    elif best_resource == 'bauxite':
                        build_plan["imp_bauxitemine"] = min(remaining_imp, max_buildings)
                        remaining_imp -= build_plan["imp_bauxitemine"]
                        used_improvements += build_plan["imp_bauxitemine"]
                    elif best_resource == 'lead':
                        build_plan["imp_leadmine"] = min(remaining_imp, max_buildings)
                        remaining_imp -= build_plan["imp_leadmine"]
                        used_improvements += build_plan["imp_leadmine"]
            
            # Manufacturing buildings (only if we have the raw resources and remaining improvements)
            if remaining_imp > 0:
                # Prioritize manufacturing based on available raw resources
                if build_plan["imp_oilwell"] == 10:  # If we have max oil wells
                    refineries = min(remaining_imp, 5)
                    build_plan["imp_gasrefinery"] = refineries
                    remaining_imp -= refineries
                    used_improvements += refineries
                
                if remaining_imp > 0 and build_plan["imp_ironmine"] == 10 and build_plan["imp_coalmine"] == 10:
                    mills = min(remaining_imp, 5)
                    build_plan["imp_steelmill"] = mills
                    remaining_imp -= mills
                    used_improvements += mills
                
                if remaining_imp > 0 and build_plan["imp_bauxitemine"] == 10:
                    refineries = min(remaining_imp, 5)
                    build_plan["imp_aluminumrefinery"] = refineries
                    remaining_imp -= refineries
                    used_improvements += refineries
                
                if remaining_imp > 0 and build_plan["imp_leadmine"] == 10:
                    factories = min(remaining_imp, 5)
                    build_plan["imp_munitionsfactory"] = factories
                    remaining_imp -= factories
                    used_improvements += factories
            
            # Calculate income changes
            base_income = infra_target * 2  # $2 per infrastructure
            
            # Calculate commerce bonus
            commerce_bonus = (
                build_plan["imp_supermarket"] * 0.03 +  # +3% per supermarket
                build_plan["imp_bank"] * 0.05 +        # +5% per bank
                build_plan["imp_mall"] * 0.09 +        # +9% per mall
                build_plan["imp_stadium"] * 0.12 +     # +12% per stadium
                build_plan["imp_subway"] * 0.08        # +8% per subway
            )
            
            total_income = base_income * (1 + commerce_bonus)
            
            # Format income info
            income_info = [
                f"**Commerce Improvements:**",
                f"Supermarkets: {build_plan['imp_supermarket']} (+{build_plan['imp_supermarket']*3}%)",
                f"Banks: {build_plan['imp_bank']} (+{build_plan['imp_bank']*5}%)",
                f"Shopping Malls: {build_plan['imp_mall']} (+{build_plan['imp_mall']*9}%)",
                f"Stadiums: {build_plan['imp_stadium']} (+{build_plan['imp_stadium']*12}%)",
                f"Subways: {build_plan['imp_subway']} (+{build_plan['imp_subway']*8}%)",
                "",
                f"**Resource Production:**"
            ]
            
            # Add resource production only if greater than 0
            if build_plan['imp_coalmine'] > 0:
                income_info.append(f"Coal Mines: {build_plan['imp_coalmine']} (+{build_plan['imp_coalmine']*3}/day)")
            if build_plan['imp_oilwell'] > 0:
                income_info.append(f"Oil Wells: {build_plan['imp_oilwell']} (+{build_plan['imp_oilwell']*3}/day)")
            if build_plan['imp_uramine'] > 0:
                income_info.append(f"Uranium Mines: {build_plan['imp_uramine']} (+{build_plan['imp_uramine']*3}/day)")
            if build_plan['imp_ironmine'] > 0:
                income_info.append(f"Iron Mines: {build_plan['imp_ironmine']} (+{build_plan['imp_ironmine']*3}/day)")
            if build_plan['imp_bauxitemine'] > 0:
                income_info.append(f"Bauxite Mines: {build_plan['imp_bauxitemine']} (+{build_plan['imp_bauxitemine']*3}/day)")
            if build_plan['imp_leadmine'] > 0:
                income_info.append(f"Lead Mines: {build_plan['imp_leadmine']} (+{build_plan['imp_leadmine']*3}/day)")
            
            income_info.extend([
                "",
                f"**MMR Type:** {mmr_type.upper() if isinstance(mmr_type, str) and mmr_type != 'default' else mmr_type}"
            ])
            
            # Create embed
            embed = create_embed(
                title=f"Build Plan",
                description="\n".join(income_info),
                color=discord.Color.blue()
            )
            
            # Add build plan as JSON in a code block
            embed.add_field(
                name="Build Plan JSON",
                value=f"```json\n{json.dumps(build_plan, indent=4)}\n```",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            info(f"Build plan generated for {nation.get('nation_name', 'N/A')} by {interaction.user}", tag="BUILD")
            
        except Exception as e:
            error(f"Error in build command: {e}", tag="BUILD")
            await interaction.followup.send(
                embed=create_embed(
                    title=":warning: An Error Occurred",
                    description=(
                        f"**An unexpected error occurred while processing the command.**\n\n"
                        f"**Error Type:** `{type(e).__name__}`\n"
                        f"**Error Message:** {e}\n\n"
                        f"Detailed error information has been logged internally. Please contact <@860564164828725299> if this issue persists."
                    ),
                    color=discord.Color.red()
                ),
                ephemeral=True
            )

async def setup(bot: commands.Bot):
    """Set up the nation cog."""
    await bot.add_cog(NationCog(bot)) 