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

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

    async def check_latency():
        while True:
            latency = bot.latency * 1000
            latency_check(latency, tag="LATENCY")
            await asyncio.sleep(60)

    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    bot.loop.create_task(check_latency())
    
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
    members = get_data.GET_ALLIANCE_MEMBERS(ALLIANCE_ID, API_KEY)

    audit_results = []
    current_time = time.time()
    one_day_seconds = 86400  # 1 day in seconds
    type = type.lower()

    info(f"Starting Audit For {len(members)} Members Of Alliance: https://politicsandwar.com/alliance/id={ALLIANCE_ID}")

    for member in members:
        if member.get("alliance_position", "") != "APPLICANT":
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
                    error(f"Error parsing last_active for {member['leader_name']}", tag="AUDIT")
                    audit_results.append(f"Error parsing last_active for {member['leader_name']}")
            elif type == "warchest":
                if cities >= len(member.get("cities", [])):
                    wc_result, _ = calculate.warchest(member, COSTS, MILITARY_COSTS)
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
                warning(f"Invalid audit type: '{type}'.", tag="AUDIT")
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


@bot.command(name="wc")
@app_commands.describe(nation_id="Nation ID for which to calculate the warchest.")
async def legacy_warchest(interaction, nation_id: int):
    try:
        nation_info = get_data.GET_NATION_DATA(nation_id, API_KEY)
        info(f"Starting Warchest Calculation For: {nation_info.get('nation_name', 'N/A')} || https://politicsandwar.com/nation/id={nation_id}")

        result, excess = calculate.warchest(nation_info, COSTS, MILITARY_COSTS)
        txt = ""
        if result is None:
            warning(f"Error calculating warchest for nation ID {nation_id}.", tag="WARCH")
            await interaction.send("Error calculating warchest. Please check the nation ID.")
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

        await interaction.send(embed=embed)
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
        await interaction.send(embed=error_embed, ephemeral=True)
        return


@bot.tree.command(name="warchest", description="Calculate a nation's warchest requirements (5 days of upkeep).")
@app_commands.describe(nation_id="Nation ID for which to calculate the warchest.")
async def warchest(interaction: discord.Interaction, nation_id: int):
    try:
        nation_info = get_data.GET_NATION_DATA(nation_id, API_KEY)

        info(f"Starting Warchest Calculation For: {nation_info.get('nation_name', 'N/A')} || https://politicsandwar.com/nation/id={nation_id} || By {interaction.user} In {interaction.channel}")

        result, excess = calculate.warchest(nation_info, COSTS, MILITARY_COSTS)
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
        base_url = f"https://politicsandwar.com/alliance/id={ALLIANCE_ID}&display=bank&d_note={nation_id}"

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


    

bot.run(BOT_TOKEN)
