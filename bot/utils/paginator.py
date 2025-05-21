from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import discord
from .helpers import create_embed
from discord import ui
from math import ceil

class ActivityPaginator(discord.ui.View):
    """A paginator for displaying activity results."""
    
    def __init__(self, results: List[str], timeout: int = 120):
        super().__init__(timeout=timeout)
        self.results = results
        self.current_page = 0
        self.items_per_page = 4
        self.pages = []
        self.create_pages()
    
    def create_pages(self) -> None:
        """Split results into pages."""
        for i in range(0, len(self.results), self.items_per_page):
            page = self.results[i:i + self.items_per_page]
            self.pages.append(page)
        
        if not self.pages:
            self.pages.append(["**All Good!** No inactive members found."])
    
    def get_embed(self) -> discord.Embed:
        """Get the current page's embed."""
        page_results = self.pages[self.current_page].copy()
        
        # Ensure grid consistency
        if len(page_results) % 2 != 0:
            page_results.append("\u200b")
        
        fields = []
        for idx, result in enumerate(page_results, start=1):
            fields.append({
                "name": "\u200b",
                "value": result,
                "inline": True
            })
        
        return create_embed(
            title="**Audit Results**",
            description="Below is a grid view of alliance members Violating the audit ran.\nUse the buttons below to navigate through pages.",
            color=discord.Color.purple(),
            fields=fields,
            footer=f"Page {self.current_page + 1}/{len(self.pages)} • Bot Maintained By Ivy Banana <3"
        )
    
    @discord.ui.button(label="Previous", style=discord.ButtonStyle.primary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle previous page button."""
        if self.current_page > 0:
            self.current_page -= 1
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle next page button."""
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        else:
            await interaction.response.defer()

class PaginatorView(ui.View):
    def __init__(self, embeds: List[discord.Embed], timeout: Optional[float] = 180):
        super().__init__(timeout=timeout)
        self.embeds = embeds
        self.current_page = 0
        self.total_pages = len(embeds)
        
        # Update button states
        self.update_buttons()
    
    def update_buttons(self):
        """Update button states based on current page."""
        self.first_page.disabled = self.current_page == 0
        self.prev_page.disabled = self.current_page == 0
        self.next_page.disabled = self.current_page == self.total_pages - 1
        self.last_page.disabled = self.current_page == self.total_pages - 1
    
    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.grey)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to first page."""
        self.current_page = 0
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
    
    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.grey)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to previous page."""
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
    
    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.grey)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to next page."""
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
    
    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.grey)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to last page."""
        self.current_page = self.total_pages - 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

class GridPaginator:
    """A utility class for creating grid-based paginated embeds."""
    
    def __init__(self, items: List[Dict[str, Any]], items_per_page: int = 9, items_per_row: int = 3):
        self.items = items
        self.items_per_page = items_per_page
        self.items_per_row = items_per_row
        self.total_pages = ceil(len(items) / items_per_page)
    
    def create_grid_embed(self, page: int, title: str, description: str = "", color: discord.Color = discord.Color.blue()) -> discord.Embed:
        """Create an embed with a grid layout for the specified page."""
        embed = discord.Embed(title=title, description=description, color=color)
        
        start_idx = page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(self.items))
        
        # Create grid layout
        for i in range(start_idx, end_idx, self.items_per_row):
            row_items = self.items[i:i + self.items_per_row]
            row_value = ""
            
            for item in row_items:
                row_value += f"{item['content']}\n"
            
            if row_value:
                embed.add_field(name="\u200b", value=row_value, inline=True)
        
        # Add page indicator
        embed.set_footer(text=f"Page {page + 1}/{self.total_pages}")
        
        return embed
    
    def get_embeds(self, title: str, description: str = "", color: discord.Color = discord.Color.blue()) -> List[discord.Embed]:
        """Get all embeds for the grid paginator."""
        return [self.create_grid_embed(i, title, description, color) for i in range(self.total_pages)] 