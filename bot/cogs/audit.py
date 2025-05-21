from typing import List, Optional, Dict
import discord
from discord import app_commands
from discord.ext import commands
import time
from datetime import datetime, timezone, timedelta

from bot.utils.config import config
from bot.utils.paginator import ActivityPaginator, GridPaginator, PaginatorView
from bot.utils.helpers import create_embed, format_number
from bot.handler import info, error, warning
from bot import data as get_data
from bot import calculate
from bot import vars as vars

class AuditCog(commands.Cog):
    """Cog for audit-related commands."""
    
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
        
        # Resource thresholds for deposit excess check (in thousands)
        self.deposit_thresholds = {
            "money": 100000,  # $100M
            "coal": 1000,     # 1M coal
            "oil": 1000,      # 1M oil
            "uranium": 100,   # 100k uranium
            "iron": 1000,     # 1M iron
            "bauxite": 1000,  # 1M bauxite
            "lead": 1000,     # 1M lead
            "gasoline": 100,  # 100k gasoline
            "munitions": 100, # 100k munitions
            "steel": 100,     # 100k steel
            "aluminum": 100,  # 100k aluminum
            "food": 1000,     # 1M food
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
    
    def create_mmr_grid_items(self, cities: List[Dict], role: str) -> List[Dict[str, str]]:
        """Create grid items for city MMR display."""
        items = []
        for city in cities:
            city_id = city.get("id")
            city_name = city.get("name", "Unknown")
            mmr_status = self.check_city_mmr(city, role)
            
            # Create status indicators
            status = []
            if not mmr_status["barracks"]:
                status.append(f"B: {city.get('barracks', 0)}/{self.mmr_requirements[role]['barracks']}")
            if not mmr_status["factory"]:
                status.append(f"F: {city.get('factory', 0)}/{self.mmr_requirements[role]['factory']}")
            if not mmr_status["hangar"]:
                status.append(f"H: {city.get('hangar', 0)}/{self.mmr_requirements[role]['hangar']}")
            if not mmr_status["drydock"]:
                status.append(f"D: {city.get('drydock', 0)}/{self.mmr_requirements[role]['drydock']}")
            
            # Create city link with status
            status_text = " | ".join(status) if status else "✅"
            city_link = f"[{city_name}](https://politicsandwar.com/city/id={city_id})" if city_id else city_name
            items.append({
                "content": f"{city_link}\n{status_text}"
            })
        
        return items
    
    def check_deposit_excess(self, nation: Dict) -> List[str]:
        """Check if a nation has excess resources that should be deposited."""
        excess = []
        
        # Resource emojis
        resource_emojis = {
            "money": "<:money:1357103044466184412>",
            "coal": "<:coal:1357102730682040410>",
            "oil": "<:Oil:1357102740391854140>",
            "uranium": "<:uranium:1357102742799126558>",
            "iron": "<:iron:1357102735488581643>",
            "bauxite": "<:bauxite:1357102729411039254>",
            "lead": "<:lead:1357102736646209536>",
            "gasoline": "<:gasoline:1357102734645399602>",
            "munitions": "<:munitions:1357102777389814012>",
            "steel": "<:steel:1357105344052072618>",
            "aluminum": "<:aluminum:1357102728391819356>",
            "food": "<:food:1357102733571784735>",
            "credits": "<:credits:1357102732187537459>"
        }
        
        # Get warchest calculation to determine required resources for 60 turns
        _, excess_dict, _ = calculate.warchest(nation, vars.COSTS, vars.MILITARY_COSTS)
        
        # Check each resource against its 60-turn requirement
        for resource, excess_amount in excess_dict.items():
            if excess_amount > 0:  # If they have more than 60 turns worth
                emoji = resource_emojis.get(resource, "")
                excess.append(f"{emoji} {format_number(excess_amount)}")
        
        return excess
    
    async def perform_member_audit(self, member: Dict, audit_results: List[str], needers: List[str]) -> None:
        """Perform all audits on a single member."""
        nation_id = int(member['id'])
        nation_url = f"https://politicsandwar.com/nation/id={nation_id}"
        header = (
            f"**Leader:** [{member['leader_name']}]({nation_url})\n"
            f"**Nation:** {member['nation_name']}\n"
            f"**Discord:** {member.get('discord', 'N/A')}\n"
        )
        
        # Activity Check
        last_active_str = member.get("last_active", "1970-01-01T00:00:00+00:00")
        try:
            last_active_dt = datetime.fromisoformat(last_active_str.replace("Z", "+00:00"))
            last_active_unix = last_active_dt.timestamp()
            
            if (time.time() - last_active_unix) >= 86400:  # 24 hours
                audit_results.append(
                    f"{header}\n"
                    f"**Last Active:** <t:{int(last_active_unix)}:F>\n"
                    f"**Defensive Wars:** {member['defensive_wars_count']}"
                )
                needers.append(f"@{member.get('discord','N/A')}")
        except ValueError:
            error(f"Error parsing last_active for {member['leader_name']}", tag="AUDIT")
        
        # Warchest Check
        wc_result, _, wc_supply = calculate.warchest(member, vars.COSTS, vars.MILITARY_COSTS)
        if wc_result is not None:
            deficits = []
            if wc_result['money_deficit'] > 0.25 * wc_supply['money']:
                deficits.append(f"<:money:1357103044466184412> {wc_result['money_deficit']:,.2f}\n")
            if wc_result['coal_deficit'] > 0.25 * wc_supply['coal']:
                deficits.append(f"<:coal:1357102730682040410> {wc_result['coal_deficit']:,.2f}\n")
            if wc_result['oil_deficit'] > 0.25 * wc_supply['oil']:
                deficits.append(f"<:Oil:1357102740391854140> {wc_result['oil_deficit']:,.2f}\n")
            if wc_result['uranium_deficit'] > 0.25 * wc_supply['uranium']:
                deficits.append(f"<:uranium:1357102742799126558> {wc_result['uranium_deficit']:,.2f}\n")
            if wc_result['iron_deficit'] > 0.25 * wc_supply['iron']:
                deficits.append(f"<:iron:1357102735488581643> {wc_result['iron_deficit']:,.2f}\n")
            if wc_result['bauxite_deficit'] > 0.25 * wc_supply['bauxite']:
                deficits.append(f"<:bauxite:1357102729411039254> {wc_result['bauxite_deficit']:,.2f}\n")
            if wc_result['lead_deficit'] > 0.25 * wc_supply['lead']:
                deficits.append(f"<:lead:1357102736646209536> {wc_result['lead_deficit']:,.2f}\n")
            if wc_result['gasoline_deficit'] > 0.25 * wc_supply['gasoline']:
                deficits.append(f"<:gasoline:1357102734645399602> {wc_result['gasoline_deficit']:,.2f}\n")
            if wc_result['munitions_deficit'] > 0.25 * wc_supply['munitions']:
                deficits.append(f"<:munitions:1357102777389814012> {wc_result['munitions_deficit']:,.2f}\n")
            if wc_result['steel_deficit'] > 0.25 * wc_supply['steel']:
                deficits.append(f"<:steel:1357105344052072618> {wc_result['steel_deficit']:,.2f}\n")
            if wc_result['aluminum_deficit'] > 0.25 * wc_supply['aluminum']:
                deficits.append(f"<:aluminum:1357102728391819356> {wc_result['aluminum_deficit']:,.2f}\n")
            if wc_result['food_deficit'] > 0.25 * wc_supply['food']:
                deficits.append(f"<:food:1357102733571784735> {wc_result['food_deficit']:,.2f}\n")
            if wc_result['credits_deficit'] > 10:
                deficits.append(f"<:credits:1357102732187537459> {wc_result['credits_deficit']:,.2f}")
            
            if deficits:
                audit_results.append(f"{header}\n**Warchest Deficits:**\n{''.join(deficits)}")
                needers.append(f"@{member.get('discord','N/A')}")
        
        # MMR Check
        cities = get_data.GET_CITY_DATA(nation_id, self.config.API_KEY)
        if cities:
            role = "Whale" if len(cities) >= 15 else "Raider"
            mmr_violations = []
            for city in cities:
                mmr_status = self.check_city_mmr(city, role)
                if not all(mmr_status.values()):
                    city_name = city.get("name", "Unknown")
                    missing = []
                    if not mmr_status["barracks"]:
                        missing.append(f"Barracks: {city.get('barracks', 0)}/{self.mmr_requirements[role]['barracks']}")
                    if not mmr_status["factory"]:
                        missing.append(f"Factory: {city.get('factory', 0)}/{self.mmr_requirements[role]['factory']}")
                    if not mmr_status["hangar"]:
                        missing.append(f"Hangar: {city.get('hangar', 0)}/{self.mmr_requirements[role]['hangar']}")
                    if not mmr_status["drydock"]:
                        missing.append(f"Drydock: {city.get('drydock', 0)}/{self.mmr_requirements[role]['drydock']}")
                    mmr_violations.append(f"{city_name}: {', '.join(missing)}")
            
            if mmr_violations:
                audit_results.append(
                    f"{header}\n"
                    f"**Role:** {role}\n"
                    f"**MMR Violations:**\n" + "\n".join(mmr_violations)
                )
                needers.append(f"@{member.get('discord','N/A')}")
        
        # Deposit Excess Check
        excess = self.check_deposit_excess(member)
        if excess:
            audit_results.append(
                f"{header}\n"
                f"**Excess Resources (Should Deposit):**\n" + "\n".join(excess)
            )
            needers.append(f"@{member.get('discord','N/A')}")
    
    @app_commands.command(name="audit", description="Audit alliance members for various requirements.")
    @app_commands.describe(
        type="Type of audit to perform",
        cities="Only audit members with ≤ this many cities (for warchest)"
    )
    @app_commands.choices(type=[
        app_commands.Choice(name="activity", value="activity"),
        app_commands.Choice(name="warchest", value="warchest"),
        app_commands.Choice(name="spies", value="spies"),
        app_commands.Choice(name="projects", value="projects"),
        app_commands.Choice(name="bloc", value="bloc"),
        app_commands.Choice(name="military", value="military"),
        app_commands.Choice(name="mmr", value="mmr"),
        app_commands.Choice(name="deposit", value="deposit"),
    ])
    async def audit(
        self,
        interaction: discord.Interaction,
        type: str,
        cities: int = 100
    ):
        """Audit alliance members based on different criteria."""
        await interaction.response.defer()
        
        members = get_data.GET_ALLIANCE_MEMBERS(self.config.ALLIANCE_ID, self.config.API_KEY)
        audit_results = []
        current_time = time.time()
        one_day_seconds = 86400
        type = type.lower()
        
        info(f"Starting Audit For {len(members)} Members Of Alliance: https://politicsandwar.com/alliance/id={self.config.ALLIANCE_ID}")
        
        need_login = []
        needers = []
        summary = []
        
        for member in members:
            if member.get("alliance_position", "") != "APPLICANT":
                if type == "activity":
                    summary = "### The Following People Need To Log In"
                    
                    last_active_str = member.get("last_active", "1970-01-01T00:00:00+00:00")
                    try:
                        last_active_dt = datetime.fromisoformat(last_active_str.replace("Z", "+00:00"))
                        last_active_unix = last_active_dt.timestamp()
                        
                        if (current_time - last_active_unix) >= one_day_seconds:
                            nation_url = f"https://politicsandwar.com/nation/id={member['id']}"
                            discord_username = member.get("discord", "N/A")
                            result = (
                                f"**Leader:** [{member['leader_name']}]({nation_url})\n"
                                f"**Nation:** {member['nation_name']}\n"
                                f"**Last Active:** <t:{int(last_active_unix)}:F>\n"
                                f"**Defensive Wars:** {member['defensive_wars_count']}\n"
                                f"**Discord:** {discord_username}"
                            )
                            audit_results.append(result)
                            needers.append(f"@{member.get('discord','N/A')}")
                    except ValueError:
                        error(f"Error parsing last_active for {member['leader_name']}", tag="AUDIT")
                        audit_results.append(f"Error parsing last_active for {member['leader_name']}")
                
                elif type == "warchest":
                    summary = "### The Following People Need To Fix Their Warchests"
                    
                    if cities >= len(member.get("cities", [])):
                        wc_result, _, wc_supply = calculate.warchest(member, vars.COSTS, vars.MILITARY_COSTS)
                        if wc_result is None:
                            audit_results.append(f"Error calculating warchest for {member['leader_name']}")
                            continue
                        
                        nation_url = f"https://politicsandwar.com/nation/id={member['id']}"
                        header = (
                            f"**Leader:** [{member['leader_name']}]({nation_url})\n"
                            f"**Nation:** {member['nation_name']}\n"
                            f"**Discord:** {member.get('discord', 'N/A')}\n"
                        )
                        
                        deficits = []
                        if wc_result['money_deficit'] > 0.25 * wc_supply['money']:
                            deficits.append(f"<:money:1357103044466184412> {wc_result['money_deficit']:,.2f}\n")
                        if wc_result['coal_deficit'] > 0.25 * wc_supply['coal']:
                            deficits.append(f"<:coal:1357102730682040410> {wc_result['coal_deficit']:,.2f}\n")
                        if wc_result['oil_deficit'] > 0.25 * wc_supply['oil']:
                            deficits.append(f"<:Oil:1357102740391854140> {wc_result['oil_deficit']:,.2f}\n")
                        if wc_result['uranium_deficit'] > 0.25 * wc_supply['uranium']:
                            deficits.append(f"<:uranium:1357102742799126558> {wc_result['uranium_deficit']:,.2f}\n")
                        if wc_result['iron_deficit'] > 0.25 * wc_supply['iron']:
                            deficits.append(f"<:iron:1357102735488581643> {wc_result['iron_deficit']:,.2f}\n")
                        if wc_result['bauxite_deficit'] > 0.25 * wc_supply['bauxite']:
                            deficits.append(f"<:bauxite:1357102729411039254> {wc_result['bauxite_deficit']:,.2f}\n")
                        if wc_result['lead_deficit'] > 0.25 * wc_supply['lead']:
                            deficits.append(f"<:lead:1357102736646209536> {wc_result['lead_deficit']:,.2f}\n")
                        if wc_result['gasoline_deficit'] > 0.25 * wc_supply['gasoline']:
                            deficits.append(f"<:gasoline:1357102734645399602> {wc_result['gasoline_deficit']:,.2f}\n")
                        if wc_result['munitions_deficit'] > 0.25 * wc_supply['munitions']:
                            deficits.append(f"<:munitions:1357102777389814012> {wc_result['munitions_deficit']:,.2f}\n")
                        if wc_result['steel_deficit'] > 0.25 * wc_supply['steel']:
                            deficits.append(f"<:steel:1357105344052072618> {wc_result['steel_deficit']:,.2f}\n")
                        if wc_result['aluminum_deficit'] > 0.25 * wc_supply['aluminum']:
                            deficits.append(f"<:aluminum:1357102728391819356> {wc_result['aluminum_deficit']:,.2f}\n")
                        if wc_result['food_deficit'] > 0.25 * wc_supply['food']:
                            deficits.append(f"<:food:1357102733571784735> {wc_result['food_deficit']:,.2f}\n")
                        if wc_result['credits_deficit'] > 10:
                            deficits.append(f"<:credits:1357102732187537459> {wc_result['credits_deficit']:,.2f}")
                        
                        if deficits:
                            deficits_str = "".join(deficits)
                            needers.append(f"@{member.get('discord','N/A')}")
                        else:
                            deficits_str = "**All Good!** No deficits found."
                        
                        result = header + f"**Warchest Deficits:**\n{deficits_str}"
                        audit_results.append(result)
                
                elif type == "spies":
                    summary = "### The Following People Need To Train More Spies"
                    
                    # Get nation data to check for Intelligence Agency project
                    nation_id = int(member['id'])
                    nation_data = get_data.GET_NATION_DATA(nation_id, self.config.API_KEY)
                    
                    # Check if nation has Intelligence Agency project
                    has_intel_agency = any(project.get('name') == 'Intelligence Agency' for project in nation_data.get('projects', []))
                    required_spies = 60 if has_intel_agency else 50
                    
                    # Check if nation has enough spies
                    if member.get("spies", 0) < required_spies:
                        nation_url = f"https://politicsandwar.com/nation/id={member['id']}"
                        result = (
                            f"**Leader:** [{member['leader_name']}]({nation_url})\n"
                            f"**Nation:** {member['nation_name']}\n"
                            f"**Discord:** {member.get('discord', 'N/A')}\n\n"
                            f"**Current Spies:** {member.get('spies', 0)}\n"
                            f"**Required Spies:** {required_spies}\n"
                            f"**Has Intelligence Agency:** {'Yes' if has_intel_agency else 'No'}"
                        )
                        audit_results.append(result)
                        needers.append(f"@{member.get('discord','N/A')}")
                
                elif type == "mmr":
                    summary = "### The Following People Need To Fix Their MMR"
                    
                    # Get city data for MMR check
                    nation_id = int(member['id'])  # Convert to integer
                    cities = get_data.GET_CITY_DATA(nation_id, self.config.API_KEY)
                    if not cities:
                        audit_results.append(f"Error fetching city data for {member['leader_name']}")
                        continue
                    
                    # Determine role based on city count
                    role = "Whale" if len(cities) >= 15 else "Raider"
                    
                    # Check MMR requirements
                    mmr_violations = []
                    for city in cities:
                        mmr_status = self.check_city_mmr(city, role)
                        if not all(mmr_status.values()):
                            city_name = city.get("name", "Unknown")
                            missing = []
                            if not mmr_status["barracks"]:
                                missing.append(f"Barracks: {city.get('barracks', 0)}/{self.mmr_requirements[role]['barracks']}")
                            if not mmr_status["factory"]:
                                missing.append(f"Factory: {city.get('factory', 0)}/{self.mmr_requirements[role]['factory']}")
                            if not mmr_status["hangar"]:
                                missing.append(f"Hangar: {city.get('hangar', 0)}/{self.mmr_requirements[role]['hangar']}")
                            if not mmr_status["drydock"]:
                                missing.append(f"Drydock: {city.get('drydock', 0)}/{self.mmr_requirements[role]['drydock']}")
                            mmr_violations.append(f"{city_name}: {', '.join(missing)}")
                    
                    if mmr_violations:
                        nation_url = f"https://politicsandwar.com/nation/id={nation_id}"
                        result = (
                            f"**Leader:** [{member['leader_name']}]({nation_url})\n"
                            f"**Nation:** {member['nation_name']}\n"
                            f"**Role:** {role}\n"
                            f"**Discord:** {member.get('discord', 'N/A')}\n\n"
                            + "\n".join(mmr_violations)
                        )
                        audit_results.append(result)
                        needers.append(f"@{member.get('discord','N/A')}")
                
                elif type == "deposit":
                    summary = "### The Following People Need To Deposit Resources"
                    
                    # Only check nations with city count <= specified limit
                    if cities >= len(member.get("cities", [])):
                        excess = self.check_deposit_excess(member)
                        if excess:
                            nation_url = f"https://politicsandwar.com/nation/id={member['id']}"
                            result = (
                                f"**Leader:** [{member['leader_name']}]({nation_url})\n"
                                f"**Nation:** {member['nation_name']}\n"
                                f"**Discord:** {member.get('discord', 'N/A')}\n\n"
                                f"**Excess Resources:**\n" + "\n".join(excess)
                            )
                            audit_results.append(result)
                            needers.append(f"@{member.get('discord','N/A')}")
        
        # Use paginator to display results
        paginator = ActivityPaginator(audit_results)
        await interaction.followup.send(embed=paginator.get_embed(), view=paginator)
        
        await interaction.followup.send(
            f"```{summary}\n" + f"{needers or ['No Violators!']}```".replace("'", "").replace("[", "").replace("]", "").replace(",", "")
        )
        
        info(f"Audit completed for {len(members)} members of alliance: {self.config.ALLIANCE_ID}", tag="AUDIT")
    
    @app_commands.command(name="audit_member", description="Audit a specific alliance member for all requirements.")
    @app_commands.describe(nation_id="The ID of the nation to audit.")
    async def audit_member(self, interaction: discord.Interaction, nation_id: int):
        """Audit a specific alliance member."""
        await interaction.response.defer()
        
        # Get alliance members
        members = get_data.GET_ALLIANCE_MEMBERS(self.config.ALLIANCE_ID, self.config.API_KEY)
        
        # Find the specific member
        member = next((m for m in members if int(m['id']) == nation_id), None)
        if not member:
            await interaction.followup.send("Nation not found in alliance.", ephemeral=True)
            return
        
        audit_results = []
        needers = []
        
        # Perform all audits on the member
        await self.perform_member_audit(member, audit_results, needers)
        
        if not audit_results:
            await interaction.followup.send("No issues found for this nation.", ephemeral=True)
            return
        
        # Use paginator to display results
        paginator = ActivityPaginator(audit_results)
        await interaction.followup.send(embed=paginator.get_embed(), view=paginator)
        
        if needers:
            await interaction.followup.send(
                f"```The Following Issues Need Attention:\n{needers[0]}```"
            )
        
        info(f"Member audit completed for nation {nation_id} by {interaction.user}", tag="AUDIT")

async def setup(bot: commands.Bot):
    """Set up the audit cog."""
    await bot.add_cog(AuditCog(bot)) 