import discord
from discord import app_commands
from discord.ext import commands
import requests
import time
from datetime import datetime, timezone
import pytz
import math
import random
import os

import warchest as wc

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")
ALLIANCE_ID = os.getenv("ALLIANCE_ID")

# Set up bot with intents
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"Logged in as {bot.user}")

@bot.tree.command(name="ping", description="Check the bot's latency.")
async def ping(interaction: discord.Interaction):
    latency = bot.latency * 1000  # Convert from seconds to milliseconds
    await interaction.response.send_message(f"Pong! Latency: {latency:,.2f} ms")



# Cost constants per turn (calculated from daily cost divided by 12 turns)
COSTS = {
    "coal_power": 100,          # $100/turn
    "oil_power": 150,           # $150/turn
    "nuclear_power": 875,       # $875/turn
    "wind_power": 42,           # $42/turn
    "farm": 25,                 # $25/turn
    "uranium_mine": 417,        # $417/turn
    "iron_mine": 134,           # $134/turn
    "coal_mine": 34,            # $34/turn
    "oil_refinery": 334,        # $334/turn
    "steel_mill": 334,          # $334/turn
    "aluminum_refinery": 209,   # $209/turn
    "munitions_factory": 292,   # $292/turn
    "police_station": 63,       # $63/turn
    "hospital": 84,             # $84/turn
    "recycling_center": 209,    # $209/turn
    "subway": 271,              # $271/turn
    "supermarket": 50,          # $50/turn
    "bank": 150,              # $150/turn
    "shopping_mall": 450,       # $450/turn
    "stadium": 1013             # $1013/turn
}

# Military upkeep costs per turn (derived from daily cost/12)
MILITARY_COSTS = {
    "soldiers": 1.88 / 12,      # per soldier
    "tanks": 75 / 12,           # per tank
    "aircraft": 750 / 12,       # per aircraft
    "ships": 5062.5 / 12        # per ship
}


# -------------------------------
# Existing Activity Audit Command and Paginator
# -------------------------------
class ActivityPaginator(discord.ui.View):
    def __init__(self, results, timeout=120):
        super().__init__(timeout=timeout)
        self.results = results
        self.current_page = 0
        self.items_per_page = 4  # Adjust as needed for grid display
        self.pages = []
        self.create_pages()

    def create_pages(self):
        # Split results into pages
        for i in range(0, len(self.results), self.items_per_page):
            page = self.results[i : i + self.items_per_page]
            self.pages.append(page)
        # If there are no results, create a default page.
        if not self.pages:
            self.pages.append(["**All Good!** No inactive members found."])

    def get_embed(self):
        embed = discord.Embed(
            title=":alarm_clock: **Activity Audit Results**",
            description="Below is a grid view of alliance members inactive for more than 24 hours.\nUse the buttons below to navigate through pages.",
            color=discord.Color.purple(),
            timestamp=datetime.utcnow()
        )
        page_results = self.pages[self.current_page].copy()
        # Ensure grid consistency: if odd number of items, add an empty field.
        if len(page_results) % 2 != 0:
            page_results.append("\u200b")
        # Add fields in grid style (2 columns)
        for idx, result in enumerate(page_results, start=1):
            embed.add_field(name="\u200b", value=result, inline=True)
        embed.set_footer(text=f"Page {self.current_page + 1}/{len(self.pages)} • Activity audit performed by the alliance audit bot")
        return embed

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        else:
            await interaction.response.defer()



@bot.tree.command(name="audit", description="Audit alliance members based on different criteria.")
@app_commands.describe(type="Type of audit to perform: activity, warchest, nsp")
async def audit(interaction: discord.Interaction, type: str):
    query = f"""{{
    nations(first:500, vmode: false, alliance_id:{ALLIANCE_ID}) {{data {{
        id
        nation_name
        leader_name
        soldiers
        tanks
        aircraft
        ships
        money
        oil
        uranium
        iron
        bauxite
        lead
        coal
        gasoline
        munitions
        steel
        aluminum
        food
        credits
        population
        defensive_wars_count
        last_active
        discord
        cities {{
            date
            infrastructure
            coal_power
            oil_power
            nuclear_power
            wind_power
            farm
            uranium_mine
            iron_mine
            coal_mine
            oil_refinery
            steel_mill
            aluminum_refinery
            munitions_factory
            police_station
            hospital
            recycling_center
            subway
            supermarket
            bank
            shopping_mall
            stadium
            barracks
            factory
            hangar
            drydock
        }}
    }}}}}}"""
    
    url = f"https://api.politicsandwar.com/graphql?api_key={API_KEY}&query={query}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        await interaction.response.send_message(f"API request failed: {e}")
        return
    
    try:
        data = response.json()
        members = data.get("data", {}).get("nations", {}).get("data", [])
        if not members:
            await interaction.response.send_message("No members found in the API response.")
            return
    except (ValueError, KeyError, TypeError) as e:
        await interaction.response.send_message(f"Error parsing API response: {e}")
        return

    audit_results = []
    current_time = time.time()
    one_day_seconds = 86400  # 1 day in seconds

    print(f"Starting Audit For {len(members)} Members Of Alliance: https://politicsandwar.com/alliance/id={ALLIANCE_ID}")

    for member in members:
        print(f"Checking {member['leader_name']} || {member['nation_name']} || {member['id']} || https://politicsandwar.com/nation/id={member['id']}\n")
        if type == "activity":
            last_active_str = member.get("last_active", "1970-01-01T00:00:00+00:00")
            try:
                last_active_dt = datetime.fromisoformat(last_active_str.replace("Z", "+00:00"))
                last_active_unix = last_active_dt.timestamp()  # Convert to Unix time
                
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
            except ValueError:
                audit_results.append(f"Error parsing last_active for {member['leader_name']}")
        elif type == "warchest":
            wc_result, _ = wc.calculate(member, COSTS, MILITARY_COSTS)
            if wc_result is None:
                audit_results.append(f"Error calculating warchest for {member['leader_name']}")
                continue

            # Create a clickable nation URL for consistency.
            nation_url = f"https://politicsandwar.com/nation/id={member['id']}"
            header = (
                f"**Leader:** [{member['leader_name']}]({nation_url})\n"
                f"**Nation:** {member['nation_name']}\n"
            )

            # Build a list of deficits, compact and separated by a vertical bar.
            deficits = []
            if wc_result['money_deficit'] > 0:
                deficits.append(f"<:money:1357103044466184412> {wc_result['money_deficit']:,.2f}\n")
            if wc_result['coal_deficit'] > 0:
                deficits.append(f"<:coal:1357102730682040410> {wc_result['coal_deficit']:,.2f}\n")
            if wc_result['oil_deficit'] > 0:
                deficits.append(f"<:Oil:1357102740391854140> {wc_result['oil_deficit']:,.2f}\n")
            if wc_result['uranium_deficit'] > 0:
                deficits.append(f"<:uranium:1357102742799126558> {wc_result['uranium_deficit']:,.2f}\n")
            if wc_result['iron_deficit'] > 0:
                deficits.append(f"<:iron:1357102735488581643> {wc_result['iron_deficit']:,.2f}\n")
            if wc_result['bauxite_deficit'] > 0:
                deficits.append(f"<:bauxite:1357102729411039254> {wc_result['bauxite_deficit']:,.2f}\n")
            if wc_result['lead_deficit'] > 0:
                deficits.append(f"<:lead:1357102736646209536> {wc_result['lead_deficit']:,.2f}\n")
            if wc_result['gasoline_deficit'] > 0:
                deficits.append(f"<:gasoline:1357102734645399602> {wc_result['gasoline_deficit']:,.2f}\n")
            if wc_result['munitions_deficit'] > 0:
                deficits.append(f"<:munitions:1357102777389814012> {wc_result['munitions_deficit']:,.2f}\n")
            if wc_result['steel_deficit'] > 0:
                deficits.append(f"<:steel:1357105344052072618> {wc_result['steel_deficit']:,.2f}\n")
            if wc_result['aluminum_deficit'] > 0:
                deficits.append(f"<:aluminum:1357102728391819356> {wc_result['aluminum_deficit']:,.2f}\n")
            if wc_result['food_deficit'] > 0:
                deficits.append(f"<:food:1357102733571784735> {wc_result['food_deficit']:,.2f}\n")
            if wc_result['credits_deficit'] > 0:
                deficits.append(f"<:credits:1357102732187537459> {wc_result['credits_deficit']:,.2f}")
            
            if deficits:
                # Join deficits using a separator for compactness.
                deficits_str = "".join(deficits)
            else:
                deficits_str = "**All Good!** No deficits found."
                
            result = header + f"**Warchest Deficits:**\n{deficits_str}"
            audit_results.append(result)
        else:
            await interaction.response.send_message("Invalid audit type. Use 'activity', 'warchest', or 'nsp'.")
            return

    # Use your existing paginator to paginate the audit_results.
    paginator = ActivityPaginator(audit_results)
    await interaction.response.send_message(embed=paginator.get_embed(), view=paginator)




@bot.tree.command(name="warchest", description="Calculate a nation's warchest requirements (5 days of upkeep).")
@app_commands.describe(nation_id="Nation ID for which to calculate the warchest.")
async def warchest(interaction: discord.Interaction, nation_id: str):
    query = f'''
    {{
      nations(id:{nation_id}) {{ data {{
        id
        nation_name
        leader_name
        soldiers
        tanks
        aircraft
        ships
        money
        coal
        oil
        uranium
        iron
        bauxite
        lead
        gasoline
        munitions
        steel
        aluminum
        food
        credits
        population
        cities {{
          date
          infrastructure
          coal_power
          oil_power
          nuclear_power
          wind_power
          farm
          uranium_mine
          iron_mine
          coal_mine
          oil_refinery
          steel_mill
          aluminum_refinery
          munitions_factory
          police_station
          hospital
          recycling_center
          subway
          supermarket
          bank
          shopping_mall
          stadium
          barracks
          factory
          hangar
          drydock
        }}
      }}}}
    }}
    '''
    url = f"https://api.politicsandwar.com/graphql?api_key={API_KEY}&query={query}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        await interaction.response.send_message(f"API request failed: {e}")
        return

    try:
        nation = response.json()
        # Extract the nation info from the nested structure.
        nation_list = nation.get("data", {}).get("nations", {}).get("data", [])
        if not nation_list:
            await interaction.response.send_message("Nation not found in the API response.")
            return
        nation_info = nation_list[0]
    except Exception as e:
        await interaction.response.send_message(f"Error parsing API response: {e}")
        return

    print(f"Starting Warchest Calculation For: {nation_info.get('nation_name', 'N/A')} || https://politicsandwar.com/nation/id={nation_id}")

    result, excess = wc.calculate(nation_info, COSTS, MILITARY_COSTS)
    txt = ""
    if result is None:
        await interaction.response.send_message("Error calculating warchest. Please check the nation ID.")
        return
    else:
        txt = f"""
    <:money:1357103044466184412> {result['money_deficit']:,.2f}
    <:coal:1357102730682040410>  {result['coal_deficit']:,.2f}
    <:Oil:1357102740391854140> {result['oil_deficit']:,.2f}
    <:uranium:1357102742799126558> {result['uranium_deficit']:,.2f}
    <:iron:1357102735488581643>  {result['iron_deficit']:,.2f}
    <:bauxite:1357102729411039254>  {result['bauxite_deficit']:,.2f}
    <:lead:1357102736646209536> {result['lead_deficit']:,.2f}
    <:gasoline:1357102734645399602>  {result['gasoline_deficit']:,.2f}
    <:munitions:1357102777389814012> {result['munitions_deficit']:,.2f}
    <:steel:1357105344052072618>  {result['steel_deficit']:,.2f}
    <:aluminum:1357102728391819356>  {result['aluminum_deficit']:,.2f}
    <:food:1357102733571784735>  {result['food_deficit']:,.2f}
    <:credits:1357102732187537459>  {result['credits_deficit']:,.2f} credits
        """

    # https://politicsandwar.com/alliance/id=13033&display=bank&d_note=TmIa7cRfmLAP&d_money=43258792&d_food=667&d_uranium=217&d_steel=321&d_aluminum=96

    base_url = f"https://politicsandwar.com/alliance/id={ALLIANCE_ID}&display=bank&d_note=safekeepings"

    # Generate query parameters only for non-zero excess values
    query_params = "&".join(
        f"d_{key}={value}" for key, value in excess.items() if value > 0
    )

    # Combine base URL with query parameters
    deposit_url = f"{base_url}&{query_params}" if query_params else base_url




    # Build the embed modal with all resource deficits.
    embed = discord.Embed(
        title=f':moneybag: Warchest for {nation_info.get('nation_name', 'N/A')} "{nation_info.get('leader_name', 'N/A')}"',
        description="Warchest for 60 Turns (5 Days)",
        color=discord.Color.purple(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="Required On-Hand", value=txt, inline=False)
    embed.add_field(name="", value=f"[Deposit Excess]({deposit_url})", inline=False)
    embed.set_footer(text="Maintained By Ivy")

    await interaction.response.send_message(embed=embed)



@bot.tree.command(name="wars", description="Check the active wars and military of a nation.")
@app_commands.describe(nation_id="Nation ID to check.")
async def audit(interaction: discord.Interaction, nation_id: str):
    query = f'''
    {{
      nations(id:{nation_id}) {{ data {{
        id
        nation_name
        leader_name
        soldiers
        tanks
        aircraft
        ships
        gasoline
        munitions
        
        wars {{
            id
            attacker
            defender
            war_type
            turns_left
            att_points
            def_points
            att_peace
            def_peace
            att_resistance
            def_resistance
            att_fortify
            def_fortify
            ground_control
            air_superiority
            naval_blockade
        }}

        cities {{
            infrastructure
        }}
      }}}}
    }}
    '''
    url = f"https://api.politicsandwar.com/graphql?api_key={API_KEY}&query={query}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        await interaction.response.send_message(f"API request failed: {e}")
        return

    try:
        nation = response.json()
        # Extract the nation info from the nested structure.
        nation_list = nation.get("data", {}).get("nations", {}).get("data", [])
        if not nation_list:
            await interaction.response.send_message("Nation not found in the API response.")
            return
        nation_info = nation_list[0]
    except Exception as e:
        await interaction.response.send_message(f"Error parsing API response: {e}")
        return
    

    print(f"Checking Wars For: {nation_info.get('nation_name', 'N/A')} || https://politicsandwar.com/nation/id={nation_id}")

    # Check if the nation is in a war
    if not nation_info.get("wars"):
        await interaction.response.send_message("This nation is not in any wars.")
        return
    
    


bot.run(BOT_TOKEN)
