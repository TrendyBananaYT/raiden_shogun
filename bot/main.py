"""
Importing Required Discord Libraries
"""
import discord
from discord import app_commands, AllowedMentions
from discord.ext import commands
import requests

"""
Importing The Required Libraries and Modules.
"""
import time
from datetime import datetime, timezone
import pytz
import math
import random
import os
import traceback
import time
import asyncio
import json


"""
Importing Custom Libraries
"""
import calculate
import data as get_data
import vars as vars
import db as dataBase
from handler import debug, info, success, warning, error, fatal, missing_data, latency_check as debug, info, success, warning, error, fatal, latency_check


BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")
ALLIANCE_ID = os.getenv("ALLIANCE_ID")

COSTS = vars.COSTS
MILITARY_COSTS = vars.MILITARY_COSTS

# Set up bot with intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

async def check_latency():
        while True:
            latency = bot.latency * 1000
            latency_check(latency, tag="LATENCY")

            await bot.change_presence(
                activity=discord.Game(name=f"Latency: {latency:,.2f}ms")
            )

            await asyncio.sleep(60)

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

    if not hasattr(bot, 'latency_task'):
        bot.latency_task = bot.loop.create_task(check_latency())

    

    
@bot.tree.command(name="ping", description="Check the bot's latency.")
async def ping(interaction: discord.Interaction):
    latency = bot.latency * 1000  # Convert from seconds to milliseconds
    info(f"Ping command executed by {interaction.user} in {interaction.channel}", tag="PING")
    latency_check(latency, tag="PING")

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
            title="**Audit Results**",
            description="Below is a grid view of alliance members Violating the audit ran.\nUse the buttons below to navigate through pages.",
            color=discord.Color.purple(),
            timestamp=datetime.now(timezone.utc)
        )
        page_results = self.pages[self.current_page].copy()
        # Ensure grid consistency: if odd number of items, add an empty field.
        if len(page_results) % 2 != 0:
            page_results.append("\u200b")
        # Add fields in grid style (2 columns)
        for idx, result in enumerate(page_results, start=1):
            embed.add_field(name="\u200b", value=result, inline=True)
        embed.set_footer(text=f"Page {self.current_page + 1}/{len(self.pages)} • Bot Maintained By Ivy Banana <3") 
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
async def audit(interaction: discord.Interaction, type: str, cities: int = 100):
    await interaction.response.defer()

    members = get_data.GET_ALLIANCE_MEMBERS(ALLIANCE_ID, API_KEY)

    audit_results = []
    current_time = time.time()
    one_day_seconds = 86400  # 1 day in seconds
    type = type.lower()

    info(f"Starting Audit For {len(members)} Members Of Alliance: https://politicsandwar.com/alliance/id={ALLIANCE_ID}")

    need_login   = []
    needers = []
    summary = []

    for member in members:
        if member.get("alliance_position", "") != "APPLICANT":
            if type == "activity":
                summary = "### The Following People Need To Log In"

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
                        needers.append(f"@{member.get('discord','N/A')}")
                except ValueError:
                    error(f"Error parsing last_active for {member['leader_name']}", tag="AUDIT")
                    audit_results.append(f"Error parsing last_active for {member['leader_name']}")
            elif type == "warchest":
                summary = "### The Following People Need To Fix Their Warchests"

                if cities >= len(member.get("cities", [])):
                    wc_result, _, wc_supply = calculate.warchest(member, COSTS, MILITARY_COSTS)
                    if wc_result is None:
                        audit_results.append(f"Error calculating warchest for {member['leader_name']}")
                        continue

                    # Create a clickable nation URL for consistency.
                    nation_url = f"https://politicsandwar.com/nation/id={member['id']}"
                    header = (
                        f"**Leader:** [{member['leader_name']}]({nation_url})\n"
                        f"**Nation:** {member['nation_name']}\n"
                        f"**Discord:** {member.get('discord', 'N/A')}\n"
                    )

                    # Build a list of deficits, compact and separated by a vertical bar.
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
                        # Join deficits using a separator for compactness.
                        deficits_str = "".join(deficits)
                        needers.append(f"@{member.get('discord','N/A')}")
                    else:
                        deficits_str = "**All Good!** No deficits found."
                        
                    result = header + f"**Warchest Deficits:**\n{deficits_str}"
                    audit_results.append(result)
                    
            elif type == "spies":
                summary = "### The Following People Need To Buy Spies"

                max_spies = 2
                match member.get("central_intelligence_agency", False):
                    case True:
                        max_spies = 3
                    case False:
                        max_spies = 2

                if member.get("spies", 0) < 50 and member.get("spies_today", 0) < max_spies:
                    nation_url = f"https://politicsandwar.com/nation/id={member['id']}"
                    result = (
                        f"**Leader:** [{member['leader_name']}]({nation_url})\n"
                        f"**Nation:** {member['nation_name']}\n"
                        f"**Spies:** {member['spies']}\n"
                        f"**Discord:** {member.get('discord', 'N/A')}"
                    )
                    audit_results.append(result)
                    needers.append(f"@{member.get('discord','N/A')}")
            elif type == "project":
                member = get_data.GET_NATION_DATA(member.get("id", 0), API_KEY)
                if member.get("propaganda_bureau", False) == False or member.get("central_intelligence_agency", False) == False:
                    nation_url = f"https://politicsandwar.com/nation/id={member['id']}"
                    result = (
                        f"**Leader:** [{member['leader_name']} - {member['nation_name']}]({nation_url})\n"
                        f"**Discord:** {member.get('discord', 'N/A')}"
                        f"**Missing Projects:**\n"
                        f"**Propaganda Bureau:** {member.get('propaganda_bureau', False)}\n"
                        f"**Central Intelligence Agency:** {member.get('central_intelligence_agency', False)}\n"
                    )
                    
                    audit_results.append(result)
                    needers.append(f"@{member.get('discord','N/A')}")

                if member.get("activity_center", False) == False and len(member.get("cities", {})) < 15:
                    result = result + f"**Activity Center:** {member.get('activity_center', False)}\n"

                    audit_results.append(result)
                    needers.append(f"@{member.get('discord','N/A')}")
            else:
                warning(f"Invalid audit type: '{type}'.", tag="AUDIT")
                await interaction.response.send_message("Invalid audit type. Use 'activity', 'warchest', or 'nsp'.")
                return

    # Use your existing paginator to paginate the audit_results.
    paginator = ActivityPaginator(audit_results)
    await interaction.followup.send(embed=paginator.get_embed(), view=paginator)

    await interaction.followup.send(f"```{summary}\n" + f"{needers or ["No Violators!"]}```".replace("'", "").replace("[", "").replace("]", "").replace(",", ""))




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
        error(f"Error while processing suggestion: {e}", tag="SUGGESTION")
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
        error(f"Error while processing bug report: {e}", tag="BUG_REPORT")
        await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)


@bot.tree.command(name="warchest", description="Calculate a nation's warchest requirements (5 days of upkeep).")
@app_commands.describe(nation_id="Nation ID for which to calculate the warchest.")
async def warchest(interaction: discord.Interaction, nation_id: int):
    try:
        nation_info = get_data.GET_NATION_DATA(nation_id, API_KEY)

        info(f"Starting Warchest Calculation For: {nation_info.get('nation_name', 'N/A')} || https://politicsandwar.com/nation/id={nation_id} || By {interaction.user} In {interaction.channel}")

        result, excess, _ = calculate.warchest(nation_info, COSTS, MILITARY_COSTS)
        txt = ""
        if result is None:
            error(f"Error calculating warchest for nation ID {nation_id}", tag="WARCH")
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

        # Base URL for deposit with the alliance details
        base_url = f"https://politicsandwar.com/alliance/id={ALLIANCE_ID}&display=bank&d_note=safekeepings"

        # Generate query parameters only for non-zero excess values
        query_params = "&".join(
            f"d_{key}={math.floor(value * 100) / 100}" for key, value in excess.items() if value > 0
        )

        # Combine base URL with query parameters if available
        deposit_url = f"{base_url}&{query_params}" if query_params else base_url

        # Build the embed with resource deficits.
        embed = discord.Embed(
            title=f':moneybag: Warchest for {nation_info.get("nation_name", "N/A")} "{nation_info.get("leader_name", "N/A")}"',
            description="Warchest for 60 Turns (5 Days)",
            color=discord.Color.purple(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Required On-Hand", value=txt, inline=False)
        embed.add_field(name="", value=f"[Deposit Excess]({deposit_url})", inline=False)
        embed.set_footer(text="Maintained By Ivy")

        await interaction.response.send_message(embed=embed)
    except Exception as e:
        # Optionally log the full traceback to your logs for debugging
        full_trace = traceback.format_exc()
        warning(e)
        
        # Build an error embed for Discord without sensitive details
        error_embed = discord.Embed(
            title=":warning: An Error Occurred",
            description=(
                f"**An unexpected error occurred while processing the command.**\n\n"
                f"**Error Type:** `{type(e).__name__}`\n"
                f"**Error Message:** {e}\n\n"
                f"Detailed error information has been logged internally. Please contact <@{vars.IVY_ID}> if this issue persists."
            ),
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)
        return


@bot.tree.command(name="bank", description="Check the bank balance of a nation.")
@app_commands.describe(nation_id="Nation ID to check.")
async def bank(interaction: discord.Interaction, nation_id: int):
    # Retrieve nation data from your API.
    nation = get_data.GET_NATION_DATA(nation_id, API_KEY)
    nation_name = nation.get("nation_name", "N/A")
    alliance = nation.get("alliance", {})
    alliance_name = alliance.get("name", "None")
    alliance_id = alliance.get("id", "N/A")
    
    # Prepare basic nation information (only once).
    header_info = (
        f"**{nation_name} of {alliance_name}**\n"
        f"Nation: {nation_id}-{nation_name} | Alliance: {alliance_name} (ID: {alliance_id})\n"
        f"Score: {nation.get('score', 'N/A')} | Pop: {nation.get('population', 'N/A')} | Leader: {nation.get('leader_name', 'N/A')}\n"
        f"{'-'*85}\n"
    )
    
    # Build the bank balance text.
    bank_balance = nation.get("bank_balance", {})
    bank_text = "\n".join([f"{key}: {value}" for key, value in bank_balance.items() if value > 0])
    
    # If no balance, indicate it.
    if not bank_text:
        bank_text = "No funds available."
    
    # Combine header and bank balance.
    output = header_info + "\n" + bank_text
    # Wrap in a code block for monospace display.
    output = "\n" + output + "\n"
    
    await interaction.response.send_message(embed=discord.Embed(description=output, color=discord.Color.purple()))


@bot.tree.command(name="wars", description="Check the active wars and military of a nation.")
@app_commands.describe(nation_id="Nation ID to check.")
async def wars(interaction: discord.Interaction, nation_id: int):
    # Retrieve nation data from your API.
    nation = get_data.GET_NATION_DATA(nation_id, API_KEY)
    nation_name = nation.get("nation_name", "N/A")
    alliance = nation.get("alliance", {})
    alliance_name = alliance.get("name", "None")
    alliance_id = alliance.get("id", "N/A")
    
    # Prepare basic nation information (only once).
    header_info = (
        f"**{nation_name} of {alliance_name}**\n"
        f"Nation: {nation_id}-{nation_name} | Alliance: {alliance_name} (ID: {alliance_id})\n"
        f"Score: {nation.get('score', 'N/A')} | Pop: {nation.get('population', 'N/A')} | Leader: {nation.get('leader_name', 'N/A')}\n"
        f"{'-'*85}\n"
    )
    
    wars_list = nation.get("wars", [])
    offensive_wars = []  # where our nation is attacker.
    defensive_wars = []  # where our nation is defender.
    
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
    
    # --- Helper Functions ---
    def format_stats(nation):
        # Produce a compact emoji stat string.
        s = nation.get("soldiers", 0)
        t = nation.get("tanks", 0)
        a = nation.get("aircraft", 0)
        sh = nation.get("ships", 0)
        # For example: "🪖123 🚜45 ✈️67 🚢89"
        return f"🪖{s} 🚜{t} ✈️{a} 🚢{sh}"
    
    def format_control(war, is_offensive: bool):
        # For offensive wars, each control flag is "AT" if true, "_" if false.
        # For defensive wars, use "DF" if true, "_" if false.
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
    
    def truncate(text, length):
        return text if len(text) <= length else text[:length-2] + ".."
    
    def format_offensive_line(war):
        # Opponent is defender.
        defender = war.get("defender", {})
        opp = f"{defender.get('id', 'N/A')}"
        opp = truncate(opp, 12)
        our_stats = format_stats(war.get("attacker", {}))
        opp_stats = format_stats(defender)
        ctrl = format_control(war, True)
        # Format: [opp] (12) | opp_stats (12) || our_stats (12) | ctrl (7)
        line = f"{opp:<12} | {opp_stats:<12} | {our_stats:<12} | {ctrl}"
        return line[:85]
    
    def format_defensive_line(war):
        # Our nation is defender; opponent is attacker.
        attacker = war.get("attacker", {})
        opp = f"{attacker.get('id', 'N/A')}-{attacker.get('nation_name', 'Unknown')}"
        opp = truncate(opp, 12)
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
    
    # Combine header and sections.
    output = header_info + "\n" + off_text + "\n\n" + def_text
    # Wrap in a code block for monospace display.
    output = "\n" + output + "\n"
    await interaction.response.send_message(embed=discord.Embed(description=output, color=discord.Color.purple()))



@bot.tree.command(name="help", description="Get help with the bot commands.")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Help",
        description="Here are the available commands:",
        color=discord.Color.blue(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="/audit", value="Audit alliance members based on different criteria.", inline=False)
    embed.add_field(name="/warchest", value="Calculate a nation's warchest requirements (5 days of upkeep).", inline=False)
    embed.add_field(name="/bank", value="Check the bank balance of a nation.", inline=False)
    embed.add_field(name="/wars", value="Check the active wars and military of a nation.", inline=False)
    embed.add_field(name="/suggest", value="Suggest something to the bot.", inline=False)
    embed.add_field(name="/report-a-bug", value="Report a bug to the bot.", inline=False)
    
    await interaction.response.send_message(embed=embed)
    info(f"Help command executed by {interaction.user} in {interaction.channel}", tag="HELP")


def override(user_val, computed, max_allowed):
    """Return user_val (clamped to max_allowed) if provided (>= 0); otherwise return computed."""
    if user_val >= 0:
        return min(user_val, max_allowed)
    return computed

@bot.tree.command(name="build", description="Find the best Build for a specific nation")
@app_commands.describe(
    nation_id="Nation ID to check.",
    infrastructure="Optional: Target infrastructure level",
    barracks="Optional: Desired number of Barracks (max 5)",
    factories="Optional: Desired number of Factories (max 5)",
    hangars="Optional: Desired number of Hangars (max 5)",
    drydocks="Optional: Desired number of Drydocks (max 3)",
    land="Optional: Land value to use for city",
    imp_coalpower="Optional: Desired number of Coal Power Plants",
    imp_oilpower="Optional: Desired number of Oil Power Plants",
    imp_windpower="Optional: Desired number of Wind Power Plants",
    imp_nuclearpower="Optional: Desired number of Nuclear Power Plants",
    imp_stadium="Optional: Desired number of Stadiums (max 3)",
    imp_mall="Optional: Desired number of Malls (max 4)",
    imp_bank="Optional: Desired number of Banks (max 5)",
    imp_supermarket="Optional: Desired number of Supermarkets (max 4)",
    imp_uramine="Optional: Desired number of Uranium Mines (max 5)",
    imp_oilwell="Optional: Desired number of Oil Wells (max 5)",
    imp_coalmine="Optional: Desired number of Coal Mines (max 10)",
    imp_ironmine="Optional: Desired number of Iron Mines (max 10)",
    imp_bauxitemine="Optional: Desired number of Bauxite Mines (max 10)",
    imp_leadmine="Optional: Desired number of Lead Mines (max 10)",
    imp_farm="Optional: Desired number of Farms (max 20)",
    imp_gasrefinery="Optional: Desired number of Oil Refineries (max 5)",
    imp_steelmill="Optional: Desired number of Steel Mills (max 5)",
    imp_aluminumrefinery="Optional: Desired number of Aluminum Refineries (max 5)",
    imp_munitionsfactory="Optional: Desired number of Munitions Factories (max 5)",
    imp_policestation="Optional: Desired number of Police Stations (max 5)",
    imp_hospital="Optional: Desired number of Hospitals (max 5)",
    imp_recyclingcenter="Optional: Desired number of Recycling Centers (max 3 or 4 if recycling_initiative active)",
    imp_subway="Optional: Desired number of Subways (max 1)"
)
async def build(
    interaction: discord.Interaction,
    nation_id: int,
    infrastructure: int = -1,
    barracks: int = -1,
    factories: int = -1,
    hangars: int = -1,
    drydocks: int = -1,
    land: int = -1,
    imp_coalpower: int = -1,
    imp_oilpower: int = -1,
    imp_windpower: int = -1,
    imp_nuclearpower: int = -1,
    imp_stadium: int = -1,
    imp_mall: int = -1,
    imp_bank: int = -1,
    imp_supermarket: int = -1,
    imp_uramine: int = -1,
    imp_oilwell: int = -1,
    imp_coalmine: int = -1,
    imp_ironmine: int = -1,
    imp_bauxitemine: int = -1,
    imp_leadmine: int = -1,
    imp_farm: int = -1,
    imp_gasrefinery: int = -1,
    imp_steelmill: int = -1,
    imp_aluminumrefinery: int = -1,
    imp_munitionsfactory: int = -1,
    imp_policestation: int = -1,
    imp_hospital: int = -1,
    imp_recyclingcenter: int = -1,
    imp_subway: int = -1
):
    info(f"Starting Build Calculation For: {nation_id} || By {interaction.user} In {interaction.channel}")
    
    # ---------------- Stage 0: Nation Data & Effective Infrastructure ----------------
    nation = get_data.GET_NATION_DATA(nation_id, API_KEY)
    nation_name = nation.get("nation_name", "N/A")
    # Preserve abbreviated continent (e.g., "af", "na", etc.)
    continent = nation.get("continent", "N/A").lower()
    cities = nation.get("cities", [])
    
    # Allowed raw resource improvements according to your table:
    # Africa: oil, bauxite, uranium
    # Antarctica: oil, coal, uranium
    # Asia: oil, iron, uranium
    # Australia: coal, bauxite, lead
    # Europe: coal, iron, lead
    # North America: coal, iron, uranium
    # South America: oil, bauxite, lead
    allowed = { "oil": False, "coal": False, "iron": False, "bauxite": False, "lead": False, "uranium": False }
    if continent == "af":
        allowed["oil"] = True
        allowed["bauxite"] = True
        allowed["uranium"] = True
    elif continent == "an":
        allowed["oil"] = True
        allowed["coal"] = True
        allowed["uranium"] = True
    elif continent == "as":
        allowed["oil"] = True
        allowed["iron"] = True
        allowed["uranium"] = True
    elif continent == "au":
        allowed["coal"] = True
        allowed["bauxite"] = True
        allowed["lead"] = True
    elif continent == "eu":
        allowed["coal"] = True
        allowed["iron"] = True
        allowed["lead"] = True
    elif continent == "na":
        allowed["coal"] = True
        allowed["iron"] = True
        allowed["uranium"] = True
    elif continent == "sa":
        allowed["oil"] = True
        allowed["bauxite"] = True
        allowed["lead"] = True

    # Fallbacks for land and infrastructure.
    if cities:
        city = cities[0]
        if land == -1:
            land = city.get("land", 100)
        if infrastructure == -1:
            infrastructure = city.get("infrastructure", 0)
    else:
        land = 100 if land == -1 else land
        infrastructure = 0 if infrastructure == -1 else infrastructure

    # Boost effective infrastructure if national projects reduce costs.
    effective_infra = infrastructure
    if nation.get("advanced_engineering_corps", False) and nation.get("center_for_civil_engineering", False):
        effective_infra = infrastructure * 1.05

    # Total improvement slots available (1 per 50 effective infra)
    imp_total = int(effective_infra) // 50

    # ---------------- Stage 1: MMR (Military) Improvements ----------------
    if barracks < 0 or factories < 0 or hangars < 0 or drydocks < 0:
        if len(cities) > 15:
            computed_barracks = 0
            computed_factory = 2
            computed_hangars = 5
            computed_drydock = 1
        else:
            computed_barracks = 5
            computed_factory = 5
            computed_hangars = 0
            computed_drydock = 0
    else:
        computed_barracks = barracks
        computed_factory = factories
        computed_hangars = hangars
        computed_drydock = drydocks
    stage_mmr = {
        "imp_barracks": min(computed_barracks, 5),
        "imp_factory": min(computed_factory, 5),
        "imp_hangars": min(computed_hangars, 5),
        "imp_drydock": min(computed_drydock, 3)
    }
    stage_mmr["imp_barracks"] = override(barracks, stage_mmr["imp_barracks"], 5)
    stage_mmr["imp_factory"] = override(factories, stage_mmr["imp_factory"], 5)
    stage_mmr["imp_hangars"] = override(hangars, stage_mmr["imp_hangars"], 5)
    stage_mmr["imp_drydock"] = override(drydocks, stage_mmr["imp_drydock"], 3)
    mmr_total = sum(stage_mmr.values())

    # ---------------- Stage 2: Power Improvements ----------------
    rem_infra = infrastructure
    nuclear_count = rem_infra // 2000
    rem_infra -= nuclear_count * 2000
    wind_count = math.ceil(rem_infra / 250) if rem_infra > 0 else 0
    # Compare two strategies:
    # Strategy A uses computed nuclear_count + wind_count.
    # Strategy B uses (nuclear_count + 1) and 0 wind, if that uses fewer improvement slots.
    stratA = nuclear_count + wind_count
    stratB = nuclear_count + 1
    if imp_nuclearpower < 0 and imp_windpower < 0 and stratB < stratA:
        nuclear_count = nuclear_count + 1
        wind_count = 0
    computed_power = {
        "imp_nuclearpower": nuclear_count,
        "imp_windpower": wind_count,
        "imp_coalpower": 0,
        "imp_oilpower": 0
    }
    computed_power["imp_nuclearpower"] = override(imp_nuclearpower, computed_power["imp_nuclearpower"], math.inf)
    computed_power["imp_windpower"] = override(imp_windpower, computed_power["imp_windpower"], math.inf)
    computed_power["imp_coalpower"] = override(imp_coalpower, computed_power["imp_coalpower"], math.inf)
    computed_power["imp_oilpower"] = override(imp_oilpower, computed_power["imp_oilpower"], math.inf)
    power_total = sum(computed_power.values())

    # ---------------- Stage 3: Safety & Commerce Improvements ----------------
    # Safety improvements are forced to maximum to eliminate pollution, crime, and disease.
    computed_safety = {
        "imp_policestation": 5,
        "imp_hospital": 5,
        "imp_recyclingcenter": 4 if nation.get("recycling_initiative", False) else 3,
        "imp_subway": 1
    }
    computed_safety["imp_policestation"] = override(imp_policestation, computed_safety["imp_policestation"], 5)
    computed_safety["imp_hospital"] = override(imp_hospital, computed_safety["imp_hospital"], 5)
    computed_safety["imp_recyclingcenter"] = override(imp_recyclingcenter, computed_safety["imp_recyclingcenter"], (4 if nation.get("recycling_initiative", False) else 3))
    computed_safety["imp_subway"] = override(imp_subway, computed_safety["imp_subway"], 1)
    safety_total = sum(computed_safety.values())
    
    computed_commerce = {
        "imp_stadium": 3,
        "imp_mall": 4,
        "imp_bank": 5,
        "imp_supermarket": 4
    }
    computed_commerce["imp_stadium"] = override(imp_stadium, computed_commerce["imp_stadium"], 3)
    computed_commerce["imp_mall"] = override(imp_mall, computed_commerce["imp_mall"], 4)
    computed_commerce["imp_bank"] = override(imp_bank, computed_commerce["imp_bank"], 5)
    computed_commerce["imp_supermarket"] = override(imp_supermarket, computed_commerce["imp_supermarket"], 4)
    commerce_total = sum(computed_commerce.values())
    
    used_so_far = mmr_total + power_total + safety_total + commerce_total
    remaining_slots = imp_total - used_so_far
    if remaining_slots < 0:
        if commerce_total > 0:
            scale = (commerce_total + remaining_slots) / commerce_total
            for k in computed_commerce:
                computed_commerce[k] = int(computed_commerce[k] * scale)
            commerce_total = sum(computed_commerce.values())
            used_so_far = mmr_total + power_total + safety_total + commerce_total
            remaining_slots = imp_total - used_so_far
        if remaining_slots < 0 and mmr_total > 0:
            scale = (mmr_total + remaining_slots) / mmr_total
            for k in stage_mmr:
                stage_mmr[k] = int(stage_mmr[k] * scale)
            mmr_total = sum(stage_mmr.values())
            used_so_far = mmr_total + power_total + safety_total + commerce_total
            remaining_slots = imp_total - used_so_far

    # ---------------- Stage 4: Split Remaining Slots ----------------
    if remaining_slots >= 10:
        RS_manufacturing = remaining_slots // 2
        RS_raw = remaining_slots - RS_manufacturing
    else:
        RS_manufacturing = 0
        RS_raw = remaining_slots

    # ---------------- Stage 5: Raw Resource Improvements ----------------
    RS = RS_raw
    computed_raw = {}
    # Priority order: Uranium Mine, Oil Well, Coal Mine, Iron Mine, Bauxite Mine, Lead Mine, Farm.
    if computed_power["imp_nuclearpower"] > 0 and RS > 0 and allowed["uranium"]:
        computed_raw["imp_uramine"] = override(imp_uramine, min(5, RS), 5)
        RS -= computed_raw["imp_uramine"]
    else:
        computed_raw["imp_uramine"] = override(imp_uramine, 0, 5)
    if RS > 0 and allowed["oil"]:
        computed_raw["imp_oilwell"] = override(imp_oilwell, min(5, RS), 5)
        RS -= computed_raw["imp_oilwell"]
    else:
        computed_raw["imp_oilwell"] = override(imp_oilwell, 0, 5)
    if RS > 0 and allowed["coal"]:
        computed_raw["imp_coalmine"] = override(imp_coalmine, min(10, RS), 10)
        RS -= computed_raw["imp_coalmine"]
    else:
        computed_raw["imp_coalmine"] = override(imp_coalmine, 0, 10)
    if RS > 0 and allowed["iron"]:
        computed_raw["imp_ironmine"] = override(imp_ironmine, min(10, RS), 10)
        RS -= computed_raw["imp_ironmine"]
    else:
        computed_raw["imp_ironmine"] = override(imp_ironmine, 0, 10)
    if RS > 0 and allowed["bauxite"]:
        computed_raw["imp_bauxitemine"] = override(imp_bauxitemine, min(10, RS), 10)
        RS -= computed_raw["imp_bauxitemine"]
    else:
        computed_raw["imp_bauxitemine"] = override(imp_bauxitemine, 0, 10)
    if RS > 0 and allowed["lead"]:
        computed_raw["imp_leadmine"] = override(imp_leadmine, min(10, RS), 10)
        RS -= computed_raw["imp_leadmine"]
    else:
        computed_raw["imp_leadmine"] = override(imp_leadmine, 0, 10)
    computed_raw["imp_farm"] = override(imp_farm, min(20, RS), 20)
    RS -= computed_raw["imp_farm"]
    raw_total = sum(computed_raw.values())

    # ---------------- Stage 6: Manufacturing Improvements ----------------
    RS = RS_manufacturing
    computed_manu = {}
    # For Oil Refinery: require Oil Well. Additionally, cap the number built to the number of Oil Wells computed.
    if computed_raw["imp_oilwell"] > 0 and RS > 0:
        max_possible = min(5, computed_raw["imp_oilwell"])
        computed_manu["imp_gasrefinery"] = override(imp_gasrefinery, min(max_possible, RS), 5)
        RS -= computed_manu["imp_gasrefinery"]
    else:
        computed_manu["imp_gasrefinery"] = override(imp_gasrefinery, 0, 5)
    # For Steel Mill: requires both Coal Mine and Iron Mine; cap by the lower of the two.
    if computed_raw["imp_coalmine"] > 0 and computed_raw["imp_ironmine"] > 0 and RS > 0:
        max_possible = min(5, computed_raw["imp_coalmine"], computed_raw["imp_ironmine"])
        computed_manu["imp_steelmill"] = override(imp_steelmill, min(max_possible, RS), 5)
        RS -= computed_manu["imp_steelmill"]
    else:
        computed_manu["imp_steelmill"] = override(imp_steelmill, 0, 5)
    # For Aluminum Refinery: requires Bauxite Mine; cap by that number.
    if computed_raw["imp_bauxitemine"] > 0 and RS > 0:
        max_possible = min(5, computed_raw["imp_bauxitemine"])
        computed_manu["imp_aluminumrefinery"] = override(imp_aluminumrefinery, min(max_possible, RS), 5)
        RS -= computed_manu["imp_aluminumrefinery"]
    else:
        computed_manu["imp_aluminumrefinery"] = override(imp_aluminumrefinery, 0, 5)
    # For Munitions Factory: requires Lead Mine; cap by that number.
    if computed_raw["imp_leadmine"] > 0 and RS > 0:
        max_possible = min(5, computed_raw["imp_leadmine"])
        computed_manu["imp_munitionsfactory"] = override(imp_munitionsfactory, min(max_possible, RS), 5)
        RS -= computed_manu["imp_munitionsfactory"]
    else:
        computed_manu["imp_munitionsfactory"] = override(imp_munitionsfactory, 0, 5)
    manu_total = sum(computed_manu.values())

    # ---------------- Final JSON Assembly (Schema Unchanged) ----------------
    build_json = {
        "infra_needed": infrastructure,
        "imp_total": imp_total,
        "imp_coalpower": computed_power["imp_coalpower"],
        "imp_oilpower": computed_power["imp_oilpower"],
        "imp_windpower": computed_power["imp_windpower"],
        "imp_nuclearpower": computed_power["imp_nuclearpower"],
        "imp_coalmine": computed_raw["imp_coalmine"],
        "imp_oilwell": computed_raw["imp_oilwell"],
        "imp_uramine": computed_raw["imp_uramine"],
        "imp_leadmine": computed_raw["imp_leadmine"],
        "imp_ironmine": computed_raw["imp_ironmine"],
        "imp_bauxitemine": computed_raw["imp_bauxitemine"],
        "imp_farm": computed_raw["imp_farm"],
        "imp_gasrefinery": computed_manu["imp_gasrefinery"],
        "imp_aluminumrefinery": computed_manu["imp_aluminumrefinery"],
        "imp_munitionsfactory": computed_manu["imp_munitionsfactory"],
        "imp_steelmill": computed_manu["imp_steelmill"],
        "imp_policestation": computed_safety["imp_policestation"],
        "imp_hospital": computed_safety["imp_hospital"],
        "imp_recyclingcenter": computed_safety["imp_recyclingcenter"],
        "imp_subway": computed_safety["imp_subway"],
        "imp_supermarket": computed_commerce["imp_supermarket"],
        "imp_bank": computed_commerce["imp_bank"],
        "imp_mall": computed_commerce["imp_mall"],
        "imp_stadium": computed_commerce["imp_stadium"],
        "imp_barracks": stage_mmr["imp_barracks"],
        "imp_factory": stage_mmr["imp_factory"],
        "imp_hangars": stage_mmr["imp_hangars"],
        "imp_drydock": stage_mmr["imp_drydock"],
    }

    import json
    json_output = json.dumps(build_json, indent=2)
    await interaction.response.send_message(
        f"**Build for Nation:** `{nation_name}` *(ID: {nation_id})*\n```json\n{json_output}\n```"
    )


bot.run(BOT_TOKEN)

