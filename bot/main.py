import discord
from discord import app_commands, AllowedMentions
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
import db as dataBase

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



@bot.tree.command(name="suggest", description="Suggest Something To The Bot! (Please Only Suggest One Thing At A Time)")
@app_commands.describe(suggestion="Your suggestion.")
async def suggest(interaction: discord.Interaction, suggestion: str):
    try:
        embed = discord.Embed(
            title="Suggestion Received",
            description=f"From: {interaction.user.mention}\n",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Suggestion", value=suggestion, inline=False)

        channel = bot.get_channel(vars.SUGGESTIONS_CHANNEL_ID)
        if channel is None:
            await interaction.response.send_message("Suggestion channel not found. Please try again later.", ephemeral=True)
            return
        
        await channel.send(
            embed=embed,
            content=f"<@&{vars.DEVELOPER_ROLE_ID}>",
            allowed_mentions=discord.AllowedMentions(roles=True)
        )
        await interaction.response.send_message("Your suggestion has been sent!", ephemeral=True)

        suggestion_data = {
            "user_id": interaction.user.id,
            "username": str(interaction.user),
            "suggestion": suggestion,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        dataBase.insert(suggestion_data, 'suggestions')

    
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)



@bot.tree.command(name="report-a-bug", description="Report A Bug To The Bot! (Please Only Report One Bug At A Time)")
@app_commands.describe(report="The Bug.")
async def report(interaction: discord.Interaction, report: str):
    try:
        embed = discord.Embed(
            title="Suggestion Received",
            description=f"From: {interaction.user.mention}\n",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Bug Report", value=report, inline=False)

        channel = bot.get_channel(vars.BUG_REPORTS_CHANNEL_ID)
        if channel is None:
            await interaction.response.send_message("Bug Reports channel not found. Please try again later.", ephemeral=True)
            return
        
        await channel.send(
            embed=embed,
            content=f"<@&{vars.DEVELOPER_ROLE_ID}>",
            allowed_mentions=discord.AllowedMentions(roles=True)
        )
        await interaction.response.send_message("Your report has been sent!", ephemeral=True)

        report_data = {
            "user_id": interaction.user.id,
            "username": str(interaction.user),
            "bug_report": report,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        dataBase.insert(report_data, 'bug_reports')

    
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)


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
    # Retrieve nation data (including wars) from your API.
    nation = get_data.GET_NATION_DATA(nation_id, API_KEY)
    nation_name = nation.get("nation_name", "N/A")
    alliance = nation.get("alliance", {})
    alliance_name = alliance.get("name", "None")
    alliance_id = alliance.get("id", "N/A")
    
    print(f"Starting Wars Checker For: {nation_name} || https://politicsandwar.com/nation/id={nation_id}")
    
    embed = discord.Embed(
        title=f"Wars for {nation_name}",
        description="All current active wars (turns left > 0):",
        color=discord.Color.purple(),
        timestamp=datetime.now(timezone.utc)
    )
    
    # Nation info
    embed.add_field(
        name="Nation",
        value=f"[{nation_id} - {nation_name}](https://politicsandwar.com/nation/id={nation_id}) of "
              f"[{alliance_name}](https://politicsandwar.com/alliance/id={alliance_id})",
        inline=False
    )
    embed.add_field(name="Score", value=str(nation.get("score", "N/A")), inline=False)
    
    wars_list = nation.get("wars", [])
    active_wars = [war for war in wars_list if int(war.get("turns_left", 0)) > 0]

    war_texts = []

    def bool_to_control(value):
        return "AT" if value else "DF"
    
    for war in active_wars:
        if nation_id == int(war.get("defender", {}).get("id", -1)):
            war_type = "defensive"
        elif nation_id == int(war.get("attacker", {}).get("id", -1)):
            war_type = "offensive"
        else:
            continue

        turns_left = war.get("turns_left", "N/A")
        ground_control = bool_to_control(war.get("ground_control", False))
        air_superiority = bool_to_control(war.get("air_superiority", False))
        naval_blockade = bool_to_control(war.get("naval_blockade", False))
        att_peace = bool_to_control(war.get("att_peace", False))
        def_peace = bool_to_control(war.get("def_peace", False))
        
        att_controls = f"{ground_control} {air_superiority} {naval_blockade} {att_peace}"
        def_controls = f"{ground_control} {air_superiority} {naval_blockade} {def_peace}"
        
        attacker = war.get("attacker", {})
        a_id = attacker.get("id", "N/A")
        a_name = attacker.get("nation_name", "Unknown")
        a_url = f"https://politicsandwar.com/nation/id={a_id}"
        a_fort = "🏰" if war.get("att_fortify", False) else ""
        a_soldiers = attacker.get("soldiers", "0")
        a_tanks = attacker.get("tanks", "0")
        a_aircraft = attacker.get("aircraft", "0")
        a_ships = attacker.get("ships", "0")
        a_stats = f"{a_soldiers} {a_tanks} {a_aircraft} {a_ships}"
        a_MAPs = war.get("att_points", "N/A")
        a_res = war.get("att_resistance", "N/A")
        
        defender = war.get("defender", {})
        d_id = defender.get("id", "N/A")
        d_name = defender.get("nation_name", "Unknown")
        d_url = f"https://politicsandwar.com/nation/id={d_id}"
        d_fort = "🏰" if war.get("def_fortify", False) else ""
        d_soldiers = defender.get("soldiers", "0")
        d_tanks = defender.get("tanks", "0")
        d_aircraft = defender.get("aircraft", "0")
        d_ships = defender.get("ships", "0")
        d_stats = f"{d_soldiers} {d_tanks} {d_aircraft} {d_ships}"
        d_MAPs = war.get("def_points", "N/A")
        d_res = war.get("def_resistance", "N/A")
        
        war_line = (
            f"T:{turns_left} | "
            f"{a_fort}{a_id} [{a_name}]({a_url}) | {a_stats} | {a_MAPs} | {a_res} | {att_controls} | "
            f"{d_fort}{d_id} [{d_name}]({d_url}) | {d_stats} | {d_MAPs} | {d_res} | {def_controls}"
        )

        war_texts.append(war_line)
    
    war_text = "```\n" + "\n".join(war_texts) + "\n```" if war_texts else "No active wars."
    embed.add_field(name="Active Wars", value=war_text, inline=False)
    
    embed.set_footer(text="Maintained By Ivy")
    await interaction.response.send_message(war_text)

    

bot.run(BOT_TOKEN)
