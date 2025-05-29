import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone
import math
import json
from typing import Optional

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
    
    def get_user_nation(self, user_id: int) -> Optional[int]:
        """Get a user's registered nation ID."""
        try:
            user_cog = self.bot.get_cog("UserCog")
            if user_cog:
                return user_cog.get_user_nation(user_id)
        except Exception as e:
            error(f"Error getting user nation: {e}", tag="NATION")
        return None
    
    async def warchest_logic(self, interaction, nation_id: int = None, ctx=None):
        try:
            # If no nation_id provided, try to get user's registered nation
            if nation_id is None:
                user_id = interaction.user.id if interaction else ctx.author.id
                nation_id = self.get_user_nation(user_id)
                if nation_id is None:
                    msg = (
                        ":warning: No Nation ID Provided\n"
                        "Please provide a nation ID or register your nation using `/register`."
                    )
                    if interaction:
                        await interaction.response.send_message(msg, ephemeral=True)
                    else:
                        await ctx.send(msg)
                    return
            nation_info = get_data.GET_NATION_DATA(nation_id, self.config.API_KEY)
            info(f"Starting Warchest Calculation For: {nation_info.get('nation_name', 'N/A')} || https://politicsandwar.com/nation/id={nation_id} || By {interaction.user if interaction else ctx.author} In {interaction.channel if interaction else ctx.channel}")
            result, excess, _ = calculate.warchest(nation_info, vars.COSTS, vars.MILITARY_COSTS)
            if result is None:
                error(f"Error calculating warchest for nation ID {nation_id}", tag="WARCH")
                if interaction:
                    await interaction.response.send_message("Error calculating warchest. Please check the nation ID.")
                else:
                    await ctx.send("Error calculating warchest. Please check the nation ID.")
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
            excess_resources = {k: v for k, v in excess.items() if v > 0}
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
            if deposit_url:
                embed.add_field(name="", value=f"[Deposit Excess]({deposit_url})", inline=False)
            if interaction:
                await interaction.response.send_message(embed=embed)
            else:
                await ctx.send(embed=embed)
        except Exception as e:
            error(f"Error in warchest command: {e}", tag="WARCH")
            msg = (
                ":warning: An Error Occurred\n"
                f"**An unexpected error occurred while processing the command.**\n\n"
                f"**Error Type:** `{type(e).__name__}`\n"
                f"**Error Message:** {e}\n\n"
                f"Detailed error information has been logged internally. Please contact <@860564164828725299> if this issue persists."
            )
            if interaction:
                await interaction.response.send_message(msg, ephemeral=True)
            else:
                await ctx.send(msg)

    @app_commands.command(name="warchest", description="Calculate a nation's warchest requirements (5 days of upkeep).")
    @app_commands.describe(nation_id="Nation ID for which to calculate the warchest (optional if you're registered)")
    async def warchest(self, interaction: discord.Interaction, nation_id: int = None):
        await self.warchest_logic(interaction, nation_id)

    @commands.command(name="wc")
    async def warchest_prefix(self, ctx, nation_id: int = None):
        await self.warchest_logic(None, nation_id, ctx=ctx)
    
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
    
    async def wars_logic(self, interaction, nation_id: int = None, ctx=None):
        try:
            # If no nation_id provided, try to get user's registered nation
            if nation_id is None:
                user_id = interaction.user.id if interaction else ctx.author.id
                nation_id = self.get_user_nation(user_id)
                if nation_id is None:
                    msg = (
                        ":warning: No Nation ID Provided\n"
                        "Please provide a nation ID or register your nation using `/register`."
                    )
                    if interaction:
                        await interaction.response.send_message(msg, ephemeral=True)
                    else:
                        await ctx.send(msg)
                    return
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
                return f"🪖{s:>8} 🚜{t:>6} ✈️{a:>4} 🚢{sh:>3}"
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
                return f"{gc:>2} {air:>2} {nb:>2} {pc:>2}"
            def format_offensive_line(war):
                defender = war.get("defender", {})
                opp = f"{defender.get('id', 'N/A')}"
                opp = opp[:12]
                our_stats = format_stats(war.get("attacker", {}))
                opp_stats = format_stats(defender)
                ctrl = format_control(war, True)
                line = f"{opp:<12} | {opp_stats} | {our_stats} | {ctrl}"
                return line[:85]
            def format_defensive_line(war):
                attacker = war.get("attacker", {})
                opp = f"{attacker.get('id', 'N/A')}-{attacker.get('nation_name', 'Unknown')}"
                opp = opp[:12]
                our_stats = format_stats(war.get("defender", {}))
                opp_stats = format_stats(attacker)
                ctrl = format_control(war, False)
                line = f"{opp:<12} | {our_stats} | {opp_stats} | {ctrl}"
                return line[:85]
            def build_section(wars, is_offensive: bool, title: str):
                if not wars:
                    return f"{title}:\nNo active wars."
                lines = [f"{title}:"]
                lines.append(f"{'ID':<12} | {'Opponent Stats':<30} | {'Our Stats':<30} | {'Control':<8}")
                lines.append("-" * 85)
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
            if interaction:
                await interaction.response.send_message(f"```\n{output}\n```")
            else:
                await ctx.send(f"```\n{output}\n```")
        except Exception as e:
            msg = (
                ":warning: An Error Occurred\n"
                f"**An unexpected error occurred while processing the command.**\n\n"
                f"**Error Type:** `{type(e).__name__}`\n"
                f"**Error Message:** {e}\n\n"
                f"Detailed error information has been logged internally. Please contact <@860564164828725299> if this issue persists."
            )
            if interaction:
                await interaction.response.send_message(msg, ephemeral=True)
            else:
                await ctx.send(msg)

    @app_commands.command(name="wars", description="Check the active wars and military of a nation.")
    @app_commands.describe(nation_id="Nation ID to check (optional if you're registered)")
    async def wars(self, interaction: discord.Interaction, nation_id: int = None):
        await self.wars_logic(interaction, nation_id)

    @commands.command(name="w")
    async def wars_prefix(self, ctx, *, search: str = None):
        """Search registered users by Discord, nation name, or nation ID."""
        if not search:
            await ctx.send("Please provide a search string. Example: `!w naturum` or `!w 590508`")
            return
        # Load registrations
        from bot.cogs.user import UserCog  # Avoid circular import at top
        user_cog = self.bot.get_cog('UserCog')
        if not user_cog:
            await ctx.send("UserCog not loaded.")
            return
        registrations = user_cog.load_registrations()
        # Find matches
        matches = []
        search_lower = search.lower()
        for discord_id, reg in registrations.items():
            if isinstance(reg, dict):
                discord_name = reg.get('discord_name', '')
                nation_name = reg.get('nation_name', '')
                nation_id = str(reg.get('nation_id', ''))
                leader_name = reg.get('leader_name', '')
                if (
                    search_lower in discord_name.lower()
                    or search_lower in nation_name.lower()
                    or search_lower in nation_id
                    or search_lower in leader_name.lower()
                ):
                    user_mention = f"<@{discord_id}>"
                    link_text = f"{leader_name}-{nation_name}" if leader_name else nation_name
                    nation_link = f"[{link_text}](https://politicsandwar.com/nation/id={nation_id})"
                    matches.append((user_mention, discord_name, nation_link, nation_id))
        if not matches:
            await ctx.send(f"No registrations found matching `{search}`.")
            return
        # Paginate if too many
        if len(matches) > 20:
            await ctx.send("Too many results, please refine your search.")
            return
        # Build embed
        embed = discord.Embed(
            title=f"Registrations matching '{search}'",
            color=discord.Color.blue()
        )
        for user_mention, discord_name, nation_link, nation_id in matches:
            line = f"{user_mention} | Discord: {discord_name} | Nation: {nation_link} ({nation_id})"
            embed.add_field(
                name="\u200b",
                value=line,
                inline=False
            )
        await ctx.send(embed=embed)

    async def who_logic(self, interaction, nation_id: int = None, ctx=None):
        if interaction is not None:
            await interaction.response.defer()
        try:
            # If no nation_id provided, try to get user's registered nation
            user_id = interaction.user.id if interaction else ctx.author.id
            if nation_id is None:
                nation_id = self.get_user_nation(user_id)
                if nation_id is None:
                    msg_embed = create_embed(
                        title=":warning: No Nation ID Provided",
                        description="Please provide a nation ID or register your nation using `/register`.",
                        color=discord.Color.orange()
                    )
                    if interaction:
                        await interaction.followup.send(embed=msg_embed, ephemeral=True)
                    else:
                        await ctx.send(embed=msg_embed)
                    return
            # Get nation data
            nation = get_data.GET_NATION_DATA(nation_id, self.config.API_KEY)
            if not nation:
                if interaction:
                    await interaction.followup.send("Nation not found.", ephemeral=True)
                else:
                    await ctx.send("Nation not found.")
                return
            # Get city data
            cities = get_data.GET_CITY_DATA(nation_id, self.config.API_KEY)
            if not cities:
                if interaction:
                    await interaction.followup.send("Could not fetch city data.", ephemeral=True)
                else:
                    await ctx.send("Could not fetch city data.")
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
                'coal': sum(city.get('coal_mine', 0) * 3 for city in cities),
                'oil': sum(city.get('oil_refinery', 0) * 3 for city in cities),
                'uranium': sum(city.get('uranium_mine', 0) * 3 for city in cities),
                'iron': sum(city.get('iron_mine', 0) * 3 for city in cities),
                'bauxite': sum(city.get('bauxite_mine', 0) * 3 for city in cities),
                'lead': sum(city.get('lead_mine', 0) * 3 for city in cities),
                'gasoline': sum(city.get('oil_refinery', 0) * 6 for city in cities),
                'munitions': sum(city.get('munitions_factory', 0) * 18 for city in cities),
                'steel': sum(city.get('steel_mill', 0) * 9 for city in cities),
                'aluminum': sum(city.get('aluminum_refinery', 0) * 9 for city in cities),
                'food': sum(city.get('farm', 0) * (city.get('land', 0) / 500) for city in cities)
            }
            # Add continent resource production
            if continent in continent_resources:
                for resource, amount in continent_resources[continent].items():
                    resource_production[resource] += amount * len(cities)
            # Get top 3 resource productions
            top_resources = sorted(resource_production.items(), key=lambda x: x[1], reverse=True)[:3]
            # Get color block based on color
            color = nation.get('color', 'gray').lower()
            color_block = {
                'red': '🟥', 'orange': '🟧', 'yellow': '🟨', 'green': '🟩', 'blue': '🟦',
                'purple': '🟪', 'pink': '💗', 'gray': '⬜', 'black': '⬛', 'brown': '🟫'
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
                if amount > 0:
                    emoji = resource_emojis.get(resource, '')
                    nation_info.append(f"{emoji} {resource.title()}: {format_number(amount)}/day")
            nation_info.extend([
                "",
                f"**Alliance:** {nation.get('alliance', {}).get('name', 'No Alliance')}",
                f"**Last Active:** <t:{int(datetime.fromisoformat(nation.get('last_active', datetime.now(timezone.utc).isoformat()).replace('Z', '+00:00')).timestamp())}:R>"
            ])
            embed = create_embed(
                title=f"Nation Information",
                description="\n".join(nation_info),
                color=discord.Color.blue(),
            )
            if nation.get('flag'):
                embed.set_thumbnail(url=nation['flag'])
            if interaction:
                await interaction.followup.send(embed=embed)
                info(f"Nation lookup completed by {interaction.user}", tag="WHO")
            else:
                await ctx.send(embed=embed)
                info(f"Nation lookup completed by {ctx.author}", tag="WHO")
        except Exception as e:
            error(f"Error in who command: {e}", tag="WHO")
            error_embed = create_embed(
                title=":warning: An Error Occurred",
                description=(
                    f"**An unexpected error occurred while processing the command.**\n\n"
                    f"**Error Type:** `{type(e).__name__}`\n"
                    f"**Error Message:** {e}\n\n"
                    f"Detailed error information has been logged internally. Please contact <@860564164828725299> if this issue persists."
                ),
                color=discord.Color.red(),
            )
            if interaction:
                await interaction.followup.send(embed=error_embed, ephemeral=True)
            else:
                await ctx.send(embed=error_embed)

    @app_commands.command(name="who", description="Show basic information about a nation.")
    @app_commands.describe(
        nation_id="The ID of the nation to look up (optional if you're registered)"
    )
    async def who(
        self,
        interaction: discord.Interaction,
        nation_id: int = None
    ):
        """Show basic information about a nation."""
        await self.who_logic(interaction, nation_id)

    @commands.command(name="who")
    async def who_prefix(self, ctx, nation_id: int = None):
        await self.who_logic(None, nation_id, ctx=ctx)

    async def income_logic(self, interaction, nation_id: int = None, ctx=None):
        await interaction.response.defer()
        
        try:
            # If no nation_id provided, try to get user's registered nation
            if nation_id is None:
                nation_id = self.get_user_nation(interaction.user.id)
                if nation_id is None:
                    await interaction.followup.send(
                        embed=create_embed(
                            title=":warning: No Nation ID Provided",
                            description="Please provide a nation ID or register your nation using `/register`.",
                            color=discord.Color.orange()
                        ),
                        ephemeral=True
                    )
                    return
            
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

    @app_commands.command(name="income", description="Show detailed economic information about a nation.")
    @app_commands.describe(
        nation_id="The ID of the nation to look up (optional if you're registered)"
    )
    async def income(
        self,
        interaction: discord.Interaction,
        nation_id: int = None
    ):
        """Show detailed economic information about a nation."""
        await self.income_logic(interaction, nation_id)

    @commands.command(name="income")
    async def income_prefix(self, ctx, nation_id: int = None):
        await self.income_logic(None, nation_id, ctx=ctx)

    async def build_logic(self, interaction, nation_id: int = None, infra_target: int = None, barracks: int = None, factories: int = None, hangars: int = None, drydocks: int = None, ctx=None):
        await interaction.response.defer()
        
        # --- Fetch nation and city data at the very top ---
        if nation_id is None:
            nation_id = self.get_user_nation(interaction.user.id)
            if nation_id is None:
                await interaction.followup.send(
                    embed=create_embed(
                        title=":warning: No Nation ID Provided",
                        description="Please provide a nation ID or register your nation using `/register`.",
                        color=discord.Color.orange()
                    ),
                    ephemeral=True
                )
                return
        nation = get_data.GET_NATION_DATA(nation_id, self.config.API_KEY)
        if not nation:
            await interaction.followup.send("Nation not found.", ephemeral=True)
            return
        cities = get_data.GET_CITY_DATA(nation_id, self.config.API_KEY)
        if not cities:
            await interaction.followup.send("Could not fetch city data.", ephemeral=True)
            return

        # --- Define infra and land from the first city ---
        infra = cities[0].get('infrastructure', 0)
        land = cities[0].get('land', 0)

        # --- Now parse projects, set variables, and define helper functions as before ---
        projects = nation.get('projects', [])
        project_names = [ (p.get('name') or '').lower() for p in projects ]
        has_gt = 'green technologies' in project_names
        has_mass_irrigation = 'mass irrigation' in project_names
        has_recycling_initiative = 'recycling initiative' in project_names
        has_itc = 'international trade center' in project_names
        has_telecom = 'telecommunications satellite' in project_names
        has_police_training = 'specialized police training program' in project_names
        has_clinical_research = 'clinical research center' in project_names
        # Resource/Manufacturing boosters (for output, not slot allocation)
        has_bauxiteworks = 'bauxiteworks' in project_names
        has_ironworks = 'ironworks' in project_names
        has_arms_stockpile = 'arms stockpile' in project_names
        has_gas_reserve = 'emergency gasoline reserve' in project_names
        has_uranium_enrichment = 'uranium enrichment program' in project_names

        # --- Define police_effect and hospital_effect based on projects ---
        police_effect = 3.5 if has_police_training else 2.5
        hospital_effect = 3.5 if has_clinical_research else 2.5

        # --- Define max_hospitals based on projects ---
        max_hospitals = 6 if has_clinical_research else 5

        # --- Define max_recycling based on projects ---
        max_recycling = 4 if has_recycling_initiative else 3

        # Set all relevant caps/bonuses and pollution variables before calc_pollution
        farm_pollution = 1 if has_gt else 2
        subway_pollution = 70 if has_gt else 45
        recycling_pollution = 75 if has_recycling_initiative else 70
        manuf_pollution_mult = 0.75 if has_gt else 1.0

        # --- Pollution calculation helper and dependencies (move to top) ---
        def calc_pollution(plan):
            pollution = 0
            pollution += plan.get('imp_coalpower', 0) * 8
            pollution += plan.get('imp_oilpower', 0) * 6
            pollution += plan.get('imp_coalmine', 0) * 12
            pollution += plan.get('imp_ironmine', 0) * 12
            pollution += plan.get('imp_uramine', 0) * 20
            pollution += plan.get('imp_leadmine', 0) * 12
            pollution += plan.get('imp_farm', 0) * farm_pollution
            pollution += plan.get('imp_policestation', 0) * 1
            pollution += plan.get('imp_hospital', 0) * 4
            pollution += plan.get('imp_stadium', 0) * 5
            pollution += plan.get('imp_mall', 0) * 2
            pollution += int(plan.get('imp_gasrefinery', 0) * 32 * manuf_pollution_mult)
            pollution += int(plan.get('imp_steelmill', 0) * 40 * manuf_pollution_mult)
            pollution += int(plan.get('imp_aluminumrefinery', 0) * 40 * manuf_pollution_mult)
            pollution += int(plan.get('imp_munitionsfactory', 0) * 32 * manuf_pollution_mult)
            pollution -= plan.get('imp_subway', 0) * subway_pollution
            pollution -= plan.get('imp_recyclingcenter', 0) * recycling_pollution
            return pollution

        try:
            # Set default infra target to first city's infra if not specified
            if infra_target is None and cities:
                infra_target = cities[0].get('infrastructure', 2000)
            
            # Define default military configurations
            default_military = {
                'whale': {'barracks': 0, 'factories': 2, 'hangars': 5, 'drydocks': 0},
                'raider': {'barracks': 5, 'factories': 0, 'hangars': 5, 'drydocks': 0},
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
                "imp_stadium": 0,
                "imp_bank": 0,
                "imp_mall": 0,
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
            power_needed = (infra_target + 1999) // 2000  # Each power plant provides 2000 infra
            uranium_needed = power_needed * 2  # 2 uranium mines needed per nuclear power plant
            
            # Power plants (always use nuclear)
            build_plan["imp_nuclearpower"] = power_needed
            used_improvements += power_needed
            
            # Calculate remaining improvements
            remaining_imp = imp_total - used_improvements
            
            # --- Step 9: Calculate Commerce Improvements First ---
            # Calculate commerce improvements with proper caps
            max_commerce = 1.0  # 100% commerce cap
            current_commerce = 0
            
            # Prioritize stadiums (12% commerce)
            if current_commerce < max_commerce:
                stadiums = min(remaining_imp, 3)  # Max 3 stadiums
                stadium_bonus = stadiums * 0.12
                if current_commerce + stadium_bonus > max_commerce:
                    stadiums = int((max_commerce - current_commerce) / 0.12)
                build_plan["imp_stadium"] = stadiums
                remaining_imp -= stadiums
                used_improvements += stadiums
                current_commerce += stadium_bonus
            
            # Then malls (8% commerce)
            if remaining_imp > 0 and current_commerce < max_commerce:
                malls = min(remaining_imp, 4)  # Max 4 malls
                mall_bonus = malls * 0.08
                if current_commerce + mall_bonus > max_commerce:
                    malls = int((max_commerce - current_commerce) / 0.08)
                build_plan["imp_mall"] = malls
                remaining_imp -= malls
                used_improvements += malls
                current_commerce += mall_bonus
            
            # Then banks (5% commerce)
            if remaining_imp > 0 and current_commerce < max_commerce:
                banks = min(remaining_imp, 5)  # Max 5 banks
                bank_bonus = banks * 0.05
                if current_commerce + bank_bonus > max_commerce:
                    banks = int((max_commerce - current_commerce) / 0.05)
                build_plan["imp_bank"] = banks
                remaining_imp -= banks
                used_improvements += banks
                current_commerce += bank_bonus
            
            # Then supermarkets (3% commerce)
            if remaining_imp > 0 and current_commerce < max_commerce:
                markets = min(remaining_imp, 4)  # Max 4 supermarkets
                market_bonus = markets * 0.03
                if current_commerce + market_bonus > max_commerce:
                    markets = int((max_commerce - current_commerce) / 0.03)
                build_plan["imp_supermarket"] = markets
                remaining_imp -= markets
                used_improvements += markets
                current_commerce += market_bonus
            
            # Then subways (8% commerce)
            if remaining_imp > 0 and current_commerce < max_commerce:
                subways = min(remaining_imp, 1)  # Max 1 subway
                subway_bonus = subways * 0.08
                if current_commerce + subway_bonus > max_commerce:
                    subways = int((max_commerce - current_commerce) / 0.08)
                build_plan["imp_subway"] = subways
                remaining_imp -= subways
                used_improvements += subways
                current_commerce += subway_bonus

            # --- Step 10: Fill with Raw Resources ---
            # List of all possible raw resources in order of priority
            raw_resources = []
            for res in allowed_resources:
                key = f'imp_{res}mine' if res != 'oil' else 'imp_oilwell'
                raw_resources.append((key, resource_caps[res]))
            
            # Fill raw resources first
            for key, cap in raw_resources:
                while build_plan.get(key, 0) < cap and used_improvements < imp_total:
                    build_plan[key] = build_plan.get(key, 0) + 1
                    used_improvements += 1
                    print(f"[DEBUG] Filling raw: {key} now {build_plan[key]}")
                    
                    # Check civil needs after each addition
                    pollution = calc_pollution(build_plan)
                    base_pop = infra * 100
                    pop_density = base_pop / land if land else 0
                    
                    # Calculate disease with more accurate formula
                    disease = ((((pop_density ** 2) * 0.01) - 25) / 100) + (base_pop / 100000) + (pollution * 0.05)
                    hospital_mod = build_plan['imp_hospital'] * hospital_effect
                    disease -= hospital_mod
                    
                    # Only add hospitals if disease > 5.0 (much higher threshold)
                    while disease > 5.0 and build_plan['imp_hospital'] < max_hospitals and used_improvements < imp_total:
                        build_plan['imp_hospital'] += 1
                        used_improvements += 1
                        print(f"[DEBUG] Adding hospital, now {build_plan['imp_hospital']}")
                        hospital_mod = build_plan['imp_hospital'] * hospital_effect
                        disease -= hospital_effect
                    
                    # Only add recycling if pollution > 200 (much higher threshold)
                    while pollution > 200 and build_plan['imp_recyclingcenter'] < max_recycling and used_improvements < imp_total:
                        build_plan['imp_recyclingcenter'] += 1
                        used_improvements += 1
                        print(f"[DEBUG] Adding recycling center, now {build_plan['imp_recyclingcenter']}")
                        pollution = calc_pollution(build_plan)
                    
                    # Only add police if crime > 5.0 (much higher threshold)
                    police_mod = build_plan['imp_policestation'] * police_effect
                    crime = ((103 - (current_commerce * 100)) ** 2 + (infra * 100)) / 111111 - police_mod
                    while crime > 5.0 and build_plan['imp_policestation'] < 5 and used_improvements < imp_total:
                        build_plan['imp_policestation'] += 1
                        used_improvements += 1
                        print(f"[DEBUG] Adding police station, now {build_plan['imp_policestation']}")
                        police_mod = build_plan['imp_policestation'] * police_effect
                        crime = ((103 - (current_commerce * 100)) ** 2 + (infra * 100)) / 111111 - police_mod

            # --- Step 11: Fill with Manufacturing if we have the raw resources ---
            if used_improvements < imp_total:
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

            # --- Step 12: Output Build Plan in Exact Schema/Order ---
            schema_keys = [
                "infra_needed",
                "imp_total",
                "imp_coalpower",
                "imp_oilpower",
                "imp_windpower",
                "imp_nuclearpower",
                "imp_coalmine",
                "imp_oilwell",
                "imp_uramine",
                "imp_leadmine",
                "imp_ironmine",
                "imp_bauxitemine",
                "imp_farm",
                "imp_gasrefinery",
                "imp_aluminumrefinery",
                "imp_munitionsfactory",
                "imp_steelmill",
                "imp_policestation",
                "imp_hospital",
                "imp_recyclingcenter",
                "imp_subway",
                "imp_supermarket",
                "imp_stadium",
                "imp_bank",
                "imp_mall",
                "imp_barracks",
                "imp_factory",
                "imp_hangars",
                "imp_drydock"
            ]
            output_plan = {}
            output_plan["infra_needed"] = infra_target
            output_plan["imp_total"] = imp_total
            for key in schema_keys[2:]:
                output_plan[key] = build_plan.get(key, 0)
            total_used = sum(output_plan.get(k, 0) for k in schema_keys[2:])
            print(f"[DEBUG] Total improvement slots used: {total_used} / {imp_total}")
            print(f"[DEBUG] Final build plan: {json.dumps(output_plan, indent=2)}")
            build_plan = output_plan

            # --- Always send a Discord message ---
            income_info = [
                f"**Commerce Improvements:**",
                f"Supermarkets: {build_plan['imp_supermarket']} (+{build_plan['imp_supermarket']*3}%)",
                f"Banks: {build_plan['imp_bank']} (+{build_plan['imp_bank']*5}%)",
                f"Shopping Malls: {build_plan['imp_mall']} (+{build_plan['imp_mall']*8}%)",
                f"Stadiums: {build_plan['imp_stadium']} (+{build_plan['imp_stadium']*12}%)",
                f"Subways: {build_plan['imp_subway']} (+{build_plan['imp_subway']*8}%)",
                "",
                f"**Resource Production:**"
            ]
            for raw in ['imp_coalmine','imp_oilwell','imp_uramine','imp_ironmine','imp_bauxitemine','imp_leadmine']:
                if build_plan[raw] > 0:
                    income_info.append(f"{raw.replace('imp_','').replace('mine',' Mine').replace('well',' Well').title()}: {build_plan[raw]}")
            for manu in ['imp_gasrefinery','imp_steelmill','imp_aluminumrefinery','imp_munitionsfactory']:
                if build_plan[manu] > 0:
                    income_info.append(f"{manu.replace('imp_','').replace('refinery',' Refinery').replace('mill',' Mill').replace('factory',' Factory').title()}: {build_plan[manu]}")
            income_info.extend(["", f"**MMR Type:** {mmr_type.upper() if isinstance(mmr_type, str) and mmr_type != 'default' else mmr_type}"])
            embed = create_embed(
                title=f"Build Plan",
                description="\n".join(income_info),
                color=discord.Color.blue()
            )
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

    @app_commands.command(name="build", description="Generate an optimized build plan for a nation.")
    @app_commands.describe(
        nation_id="The ID of the nation to generate a build for (optional if you're registered)",
        infra_target="Target infrastructure level (defaults to first city's infra)",
        barracks="Number of barracks (0-5, default based on MMR)",
        factories="Number of factories (0-5, default based on MMR)",
        hangars="Number of hangars (0-5, default based on MMR)",
        drydocks="Number of drydocks (0-3, default based on MMR)"
    )
    async def build(
        self,
        interaction: discord.Interaction,
        nation_id: int = None,
        infra_target: int = None,
        barracks: int = None,
        factories: int = None,
        hangars: int = None,
        drydocks: int = None
    ):
        """Generate an optimized build plan for a nation."""
        await self.build_logic(interaction, nation_id, infra_target, barracks, factories, hangars, drydocks)

    @commands.command(name="build")
    async def build_prefix(self, ctx, nation_id: int = None, infra_target: int = None, barracks: int = None, factories: int = None, hangars: int = None, drydocks: int = None):
        await self.build_logic(None, nation_id, infra_target, barracks, factories, hangars, drydocks, ctx=ctx)

    async def chest_logic(self, interaction, nation_id: int = None, ctx=None):
        # Determine user ID for registration lookup
        user_id = interaction.user.id if interaction else ctx.author.id
        if nation_id is None:
            nation_id = self.get_user_nation(user_id)
            if nation_id is None:
                msg_embed = create_embed(
                    title=":warning: No Nation ID Provided",
                    description="Please provide a nation ID or register your nation using `/register`.",
                    color=discord.Color.orange()
                )
                if interaction:
                    await interaction.response.send_message(embed=msg_embed, ephemeral=True)
                else:
                    await ctx.send(embed=msg_embed)
                return
        nation = get_data.GET_NATION_DATA(nation_id, self.config.API_KEY)
        if not nation:
            if interaction:
                await interaction.response.send_message("Nation not found.", ephemeral=True)
            else:
                await ctx.send("Nation not found.")
            return
        # List of resources to display
        resources = [
            ("money", "<:money:1357103044466184412>", "Money"),
            ("coal", "<:coal:1357102730682040410>", "Coal"),
            ("oil", "<:Oil:1357102740391854140>", "Oil"),
            ("uranium", "<:uranium:1357102742799126558>", "Uranium"),
            ("iron", "<:iron:1357102735488581643>", "Iron"),
            ("bauxite", "<:bauxite:1357102729411039254>", "Bauxite"),
            ("lead", "<:lead:1357102736646209536>", "Lead"),
            ("gasoline", "<:gasoline:1357102734645399602>", "Gasoline"),
            ("munitions", "<:munitions:1357102777389814012>", "Munitions"),
            ("steel", "<:steel:1357105344052072618>", "Steel"),
            ("aluminum", "<:aluminum:1357102728391819356>", "Aluminum"),
            ("food", "<:food:1357102733571784735>", "Food"),
            ("credits", "<:credits:1357102732187537459>", "Credits"),
        ]
        lines = []
        for key, emoji, label in resources:
            value = nation.get(key, 0)
            lines.append(f"{emoji} **{label}:** {format_number(value)}")
        embed = create_embed(
            title=f"Resource Chest for {nation.get('nation_name', 'N/A')}",
            description="\n".join(lines),
            color=discord.Color.gold()
        )
        if interaction:
            await interaction.response.send_message(embed=embed)
        else:
            await ctx.send(embed=embed)

    @commands.command(name="nw")
    async def chest_prefix(self, ctx, nation_id: int = None):
        await self.chest_logic(None, nation_id, ctx=ctx)

    async def raid_logic(self, interaction, nation_id: int = None, ctx=None):
        """Find profitable raid targets within a nation's war range."""
        try:
            # If no nation_id provided, try to get user's registered nation
            if nation_id is None:
                user_id = interaction.user.id if interaction else ctx.author.id
                nation_id = self.get_user_nation(user_id)
                if nation_id is None:
                    msg = (
                        ":warning: No Nation ID Provided\n"
                        "Please provide a nation ID or register your nation using `/register`."
                    )
                    if interaction:
                        await interaction.response.send_message(msg, ephemeral=True)
                    else:
                        await ctx.send(msg)
                    return

            # Get the nation's data
            nation = get_data.GET_NATION_DATA(nation_id, self.config.API_KEY)
            if not nation:
                if interaction:
                    await interaction.response.send_message("Nation not found.", ephemeral=True)
                else:
                    await ctx.send("Nation not found.")
                return

            # Calculate war range
            score = float(nation.get('score', 0))
            min_score = score * 0.75
            max_score = score * 1.75

            # Get all nations in range
            nations = get_data.GET_ALL_NATIONS(self.config.API_KEY)
            if not nations:
                msg = "Could not fetch nations data. Please try again later."
                if interaction:
                    await interaction.response.send_message(msg, ephemeral=True)
                else:
                    await ctx.send(msg)
                return

            # Filter and sort potential targets
            targets = []
            for target in nations:
                if not target:  # Skip if target data is None
                    continue
                    
                target_score = float(target.get('score', 0))
                if min_score <= target_score <= max_score:
                    # Skip if in same alliance
                    if target.get('alliance', {}).get('id') == nation.get('alliance', {}).get('id'):
                        continue
                    
                    # Calculate income potential
                    cities = target.get('cities', [])
                    if not cities:  # Skip if no city data
                        continue
                        
                    infra = sum(city.get('infrastructure', 0) for city in cities)
                    income = infra * 2  # Base income per infra
                    
                    # Calculate military strength
                    soldiers = target.get('soldiers', 0)
                    tanks = target.get('tanks', 0)
                    aircraft = target.get('aircraft', 0)
                    ships = target.get('ships', 0)
                    
                    # Skip if too strong
                    if soldiers > 100000 or tanks > 1000 or aircraft > 100 or ships > 50:
                        continue
                    
                    # Calculate profit potential (income * 0.1 for 10% loot)
                    profit = income * 0.1
                    
                    targets.append({
                        'id': target.get('id'),
                        'name': target.get('nation_name'),
                        'leader': target.get('leader_name'),
                        'score': target_score,
                        'cities': len(cities),
                        'infra': infra,
                        'income': income,
                        'profit': profit,
                        'soldiers': soldiers,
                        'tanks': tanks,
                        'aircraft': aircraft,
                        'ships': ships
                    })

            # Sort by profit potential
            targets.sort(key=lambda x: x['profit'], reverse=True)
            
            # Take top 10 targets
            targets = targets[:10]
            
            if not targets:
                if interaction:
                    await interaction.response.send_message("No suitable targets found in your war range.", ephemeral=True)
                else:
                    await ctx.send("No suitable targets found in your war range.")
                return

            # Format output
            output = []
            for target in targets:
                output.append(
                    f"**[{target['name']}](https://politicsandwar.com/nation/id={target['id']})** "
                    f"({target['leader']})\n"
                    f"Score: {target['score']:.2f} | Cities: {target['cities']} | "
                    f"Income: ${format_number(target['income'])}/day | "
                    f"Profit: ${format_number(target['profit'])}/day\n"
                    f"Military: 🪖{format_number(target['soldiers'])} "
                    f"🚜{format_number(target['tanks'])} "
                    f"✈️{format_number(target['aircraft'])} "
                    f"🚢{format_number(target['ships'])}"
                )

            embed = create_embed(
                title=f"Raid Targets for {nation.get('nation_name', 'N/A')}",
                description="\n\n".join(output),
                color=discord.Color.red()
            )
            
            if interaction:
                await interaction.response.send_message(embed=embed)
            else:
                await ctx.send(embed=embed)

        except Exception as e:
            error(f"Error in raid command: {e}", tag="RAID")
            msg = (
                ":warning: An Error Occurred\n"
                f"**An unexpected error occurred while processing the command.**\n\n"
                f"**Error Type:** `{type(e).__name__}`\n"
                f"**Error Message:** {e}\n\n"
                f"Detailed error information has been logged internally. Please contact <@860564164828725299> if this issue persists."
            )
            if interaction:
                await interaction.response.send_message(msg, ephemeral=True)
            else:
                await ctx.send(msg)

    @app_commands.command(name="raid", description="Find profitable raid targets within your war range.")
    @app_commands.describe(nation_id="The ID of the nation to check (optional if you're registered)")
    async def raid(self, interaction: discord.Interaction, nation_id: int = None):
        """Find profitable raid targets within your war range."""
        await self.raid_logic(interaction, nation_id)

    @commands.command(name="raid")
    async def raid_prefix(self, ctx, nation_id: int = None):
        await self.raid_logic(None, nation_id, ctx=ctx)

class NationGroup(app_commands.Group):
    def __init__(self, cog):
        super().__init__(name="nation", description="Nation-related commands")
        self.cog = cog

    @app_commands.command(name="chest", description="Show the current amount of resources on a nation.")
    @app_commands.describe(nation_id="The nation ID to check (optional if you're registered)")
    async def chest(self, interaction: discord.Interaction, nation_id: int = None):
        await self.cog.chest_logic(interaction, nation_id)

async def setup(bot: commands.Bot):
    """Set up the nation cog."""
    cog = NationCog(bot)
    await bot.add_cog(cog)
    bot.tree.add_command(NationGroup(cog)) 