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
import data as get_data
import vars as vars

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")
ALLIANCE_ID = os.getenv("ALLIANCE_ID")


COSTS = vars.COSTS
MILITARY_COSTS = vars.MILITARY_COSTS

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
    members = get_data.GET_ALLIANCE_MEMBERS(ALLIANCE_ID, API_KEY)

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
async def warchest(interaction: discord.Interaction, nation_id: int):
    nation_info = get_data.GET_NATION_DATA(nation_id, API_KEY)

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
        title=f''':moneybag: Warchest for {nation_info.get('nation_name', 'N/A')} "{nation_info.get('leader_name', 'N/A')}"''',
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
async def wars(interaction: discord.Interaction, nation_id: int):
    infra = 0.0
    nation = get_data.GET_NATION_DATA(nation_id, API_KEY)
    print(f"Starting Wars Checker For: {nation.get('nation_name', 'N/A')} || https://politicsandwar.com/nation/id={nation_id}")

    for city in nation.get("cities", []):
        infra += city.get("infrastructure", 0)

    # Separate wars into defensive and offensive
    defensive_wars = []  # where this nation is defender
    offensive_wars = []  # where this nation is attacker
    
    self_side = ""
    enemy_side = ""

    # Helper to format one side's info
    def format_side(war, side: str):
        data = war.get(side, {})
        # If fortified then add the fortress symbol
        fort = "🏰" if war.get(f"{side}_fortify") else ""
        n_id = data.get("id", "N/A")
        n_name = data.get("nation_name", f"Nation {n_id}")
        url = f"https://politicsandwar.com/nation/id={n_id}"
        # Military counts
        mil = f"{data.get('soldiers',0)} {data.get('tanks',0)} {data.get('aircraft',0)} {data.get('ships',0)}"
        # MAPs and resistance depending on side
        maps = war.get("att_points") if side == "attacker" else war.get("def_points")
        res = war.get("att_resistance") if side == "attacker" else war.get("def_resistance")
        
        print(f"Formate Side: {fort}{n_id} [ {n_name} ]({url}) | {mil} | {maps} | {res}")
        return f"{fort}{n_id} [ {n_name} ]({url}) | {mil} | {maps} | {res}"
    
    # Loop through wars from the nation data
    for war in nation.get("wars", []):
        # Determine if our nation is attacker or defender.
        if nation_id == war.get("attacker", {}).get("id"):
            self_side = "attacker"
            enemy_side = "defender"
            offensive_wars.append(war)
        else:
            self_side = "defender"
            enemy_side = "attacker"
            defensive_wars.append(war)

    # Build war line for each war
    def build_war_line(war, self_side: str, enemy_side: str):
        # War id and turns left
        war_id = war.get("id", "N/A")
        turns = war.get("turns_left", "?")
        
        # Flags for overall war advantages
        gc = "AT" if war.get("ground_control") == "attacker" else "DF"
        air = "AT" if war.get("air_superiority") == "attacker" else "DF"
        nb = "AT" if war.get("naval_blockade") == "attacker" else "DF"
        peace = "AT" if war.get("att_peace") else ("DF" if war.get("def_peace") else "")
        flags = f"{gc} {air} {nb} {peace}"
        
        self_info = format_side(war, self_side)
        enemy_info = format_side(war, enemy_side)
        print(f"Build War Line: {war_id} (t{turns}) | {self_info} | {flags} | {enemy_info}")
        return f"{war_id} (t{turns}) | {self_info} | {flags} | {enemy_info}"

    # Build strings for each section
    def format_wars_list(wars_list, self_side: str, enemy_side: str):
        lines = []
        for w in wars_list:
            lines.append(build_war_line(w, self_side, enemy_side))
        print(lines)
        return "\n".join(lines) if lines else "None"

    # For wars where our nation is defender, self_side is "defender"
    def_wars_str = format_wars_list(defensive_wars, "defender", "attacker")
    # For wars where our nation is attacker, self_side is "attacker"
    off_wars_str = format_wars_list(offensive_wars, "attacker", "defender")

    # Build the main embed
    embed = discord.Embed(
        title=f"Wars for {nation.get('nation_name', 'N/A')} \"{nation.get('leader_name', 'N/A')}\"",
        description=f"Nation: **[{nation.get('nation_name', 'N/A')}](https://politicsandwar.com/nation/id={nation_id})** \"{nation.get('leader_name', 'N/A')}\"\nInfra: {infra:,.2f} | Score: {nation.get('score', 0):,.2f}",
        color=discord.Color.purple(),
        timestamp=datetime.now(timezone.utc)
    )

    embed.add_field(name="Defensive Wars", value=def_wars_str, inline=False)
    embed.add_field(name="Offensive Wars", value=off_wars_str, inline=False)
    embed.set_footer(text="Maintained By Ivy")

    await interaction.response.send_message(embed=embed)

    

bot.run(BOT_TOKEN)
