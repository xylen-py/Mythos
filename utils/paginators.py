"""
Mythos - A Feature-Rich Discord Music Bot
Copyright (C) 2026 xylen-py

This file is part of Mythos.
Mythos is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Mythos is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Mythos. If not, see <https://www.gnu.org/licenses/>.

Author: xylen-py
GitHub: https://github.com/xylen-py
"""

import discord
from discord.ext import commands
from dataclasses import dataclass
from config import default_color
from typing import Union, List, Callable, Dict, Any, Optional, Sequence, Set

PageContent = Union[discord.Embed, str, discord.File, Dict[str, Any]]
ContentSource = Union[List[PageContent], Callable[[int], PageContent]]

@dataclass(slots=True)
class PaginatorStyle:
    first: str = "<:arrow1:1556658161232904282>"
    previous: str = "<:arrow2:1556658398987157636>"
    delete: str = "<:delete:1556658174176665720>"
    next: str = "<:arrow3:1556658502926205033>"
    last: str = "<:arrow4:1556658621717286932>"
    jump: str = "<:jump:1556658650225844295>"
    button_style: discord.ButtonStyle = discord.ButtonStyle.secondary

PAGINATOR_STYLE = PaginatorStyle()

class _JumpModal(discord.ui.Modal, title="Jump to Page"):
    page_input = discord.ui.TextInput(
        label="Page Number",
        placeholder="Enter a page number.",
        min_length=1,
        max_length=5,
        required=True
    )

    def __init__(self, paginator: "Paginator"):
        super().__init__()
        self.paginator = paginator
        self.page_input.placeholder = f"e.g ( 1 , {paginator.total_pages + 1} )"

    async def on_submit(self, interaction: discord.Interaction):
        try:
            page = int(self.page_input.value) - 1
            page = max(0, min(page, self.paginator.total_pages))
            await self.paginator.show_page(interaction, page)
        except ValueError:
            await interaction.response.send_message("Invalid page number.", ephemeral=True)

class Paginator(discord.ui.LayoutView):
    def __init__(
        self,
        ctx: Union[commands.Context, discord.Interaction],
        content: ContentSource,
        *,
        total_pages: Optional[int] = None,
        timeout: float = 180.0,
        footer_format: str = "Page {page}/{total_pages} | Requested by {user.display_name}",
        extra_items: Optional[Sequence[discord.ui.Item]] = None,
        allowed_mentions: Optional[discord.AllowedMentions] = None,
        reply: bool = False,
        silent: bool = False,
        ephemeral: bool = False,
        page_counter: bool = False,
        jump_button: bool = False,
        author_ids: Optional[Set[int]] = None,
        on_page_change: Optional[Callable[[int, "Paginator"], Any]] = None,
        loop: bool = False
    ):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.content = content
        self.footer_format = footer_format
        self.allowed_mentions = allowed_mentions
        self.reply = reply
        self.silent = silent
        self.ephemeral = ephemeral
        self.page_counter = page_counter
        self.jump_button = jump_button
        self.on_page_change = on_page_change
        self.loop = loop
        self.extra_items = extra_items
        self.message: Optional[discord.Message] = None
        self.current_page = 0

        if isinstance(ctx, discord.Interaction):
            self._author_id = ctx.user.id
            self._author = ctx.user
        else:
            self._author_id = ctx.author.id
            self._author = ctx.author

        self._allowed_users: Set[int] = author_ids or {self._author_id}

        if callable(content):
            if total_pages is None:
                raise ValueError("total_pages must be provided for a dynamic content generator.")
            self.total_pages = total_pages - 1
        else:
            self.total_pages = len(content) - 1

        s = PAGINATOR_STYLE

        if jump_button:
            self.nav_buttons = [
                discord.ui.Button(emoji=s.previous, style=s.button_style, custom_id="pg_prev"),
                discord.ui.Button(emoji=s.delete, style=s.button_style, custom_id="pg_delete"),
                discord.ui.Button(emoji=s.next, style=s.button_style, custom_id="pg_next"),
                discord.ui.Button(emoji=s.jump, style=s.button_style, custom_id="pg_jump"),
            ]

            self.nav_buttons[0].callback = self.previous_page
            self.nav_buttons[1].callback = self.delete_page
            self.nav_buttons[2].callback = self.next_page
            self.nav_buttons[3].callback = self.jump_page
        else:
            self.nav_buttons = [
                discord.ui.Button(emoji=s.first, style=s.button_style, custom_id="pg_first"),
                discord.ui.Button(emoji=s.previous, style=s.button_style, custom_id="pg_prev"),
                discord.ui.Button(emoji=s.delete, style=s.button_style, custom_id="pg_delete"),
                discord.ui.Button(emoji=s.next, style=s.button_style, custom_id="pg_next"),
                discord.ui.Button(emoji=s.last, style=s.button_style, custom_id="pg_last"),
            ]

            self.nav_buttons[0].callback = self.first_page
            self.nav_buttons[1].callback = self.previous_page
            self.nav_buttons[2].callback = self.delete_page
            self.nav_buttons[3].callback = self.next_page
            self.nav_buttons[4].callback = self.last_page

        if page_counter:
            self.counter_btn = discord.ui.Button(label=f"1/{self.total_pages + 1}", style=s.button_style, disabled=True, custom_id="pg_counter")

    def embed_to_container(self, raw: PageContent, page_num: int) -> discord.ui.Container:
        items = []

        if isinstance(raw, discord.Embed):
            if raw.title:
                items.append(discord.ui.TextDisplay(content=f"### {raw.title}"))

            if raw.description:
                items.append(discord.ui.TextDisplay(content=raw.description))

            for field in raw.fields:
                header = f"**{field.name}**" if field.name else ""
                val = field.value if field.value else " "
                items.append(discord.ui.TextDisplay(content=f"{header}\n{val}"))

            footer_text = None
            if raw.footer and raw.footer.text:
                footer_text = raw.footer.text
            elif self.footer_format:
                footer_text = self.footer_format.format(
                    page=page_num + 1, total_pages=self.total_pages + 1, user=self._author
                )

            if footer_text:
                items.append(discord.ui.Separator(visible=False))
                items.append(discord.ui.TextDisplay(content=f"-# {footer_text}"))

            color = raw.color if raw.color else default_color
            return discord.ui.Container(*items, accent_colour=color)

        elif isinstance(raw, str):
            items.append(discord.ui.TextDisplay(content=raw))

            if self.footer_format:
                footer_text = self.footer_format.format(
                    page=page_num + 1, total_pages=self.total_pages + 1, user=self._author
                )
                items.append(discord.ui.Separator(visible=False))
                items.append(discord.ui.TextDisplay(content=f"-# {footer_text}"))

            return discord.ui.Container(*items)

        elif isinstance(raw, dict):
            embed = raw.get("embed")
            content_text = raw.get("content")

            if embed:
                return self.embed_to_container(embed, page_num)

            if content_text:
                items.append(discord.ui.TextDisplay(content=content_text))

            if self.footer_format:
                footer_text = self.footer_format.format(
                    page=page_num + 1, total_pages=self.total_pages + 1, user=self._author
                )
                items.append(discord.ui.Separator(visible=False))
                items.append(discord.ui.TextDisplay(content=f"-# {footer_text}"))

            return discord.ui.Container(*items)

        return discord.ui.Container(discord.ui.TextDisplay(content="No content available."))

    async def resolve_page(self, page_num: int) -> PageContent:
        if callable(self.content):
            return await discord.utils.maybe_coroutine(self.content, page_num)
        return self.content[page_num]

    def sync_buttons(self):
        if not self.loop:
            if self.jump_button:
                self.nav_buttons[0].disabled = self.current_page == 0
                self.nav_buttons[2].disabled = self.current_page == self.total_pages
            else:
                self.nav_buttons[0].disabled = self.current_page == 0
                self.nav_buttons[1].disabled = self.current_page == 0
                self.nav_buttons[3].disabled = self.current_page == self.total_pages
                self.nav_buttons[4].disabled = self.current_page == self.total_pages

        if self.page_counter:
            self.counter_btn.label = f"{self.current_page + 1}/{self.total_pages + 1}"

    async def build_view(self, page_num: int, disabled: bool = False):
        self.clear_items()

        raw = await self.resolve_page(page_num)
        container = self.embed_to_container(raw, page_num)
        self.add_item(container)

        if disabled:
            for btn in self.nav_buttons:
                btn.disabled = True
            
            if self.extra_items:
                def disable_ui_item(obj: Any):
                    if hasattr(obj, "disabled"):
                        try:
                            obj.disabled = True
                        except Exception:
                            pass
                    for attr in ("children", "components", "items", "_items"):
                        if hasattr(obj, attr):
                            val = getattr(obj, attr)
                            if isinstance(val, (list, tuple)):
                                for child in val:
                                    disable_ui_item(child)
                
                for item in self.extra_items:
                    disable_ui_item(item)

        nav_row_items = list(self.nav_buttons)

        if self.page_counter:
            nav_row_items.append(self.counter_btn)

        for i in range(0, len(nav_row_items), 5):
            self.add_item(discord.ui.ActionRow(*nav_row_items[i:i+5]))

        if self.extra_items:
            for item in self.extra_items:
                if isinstance(item, discord.ui.ActionRow) or isinstance(item, discord.ui.Container):
                    self.add_item(item)
                else:
                    self.add_item(discord.ui.ActionRow(item))

    async def show_page(self, interaction: discord.Interaction, page: int):
        self.current_page = page
        self.sync_buttons()

        if self.on_page_change:
            await discord.utils.maybe_coroutine(self.on_page_change, self.current_page, self)

        await self.build_view(self.current_page)
        await interaction.response.edit_message(view=self, content=None, embed=None, allowed_mentions=discord.AllowedMentions.none())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in self._allowed_users:
            await interaction.response.send_message("You cannot control this.", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        try:
            if self.message:
                await self.build_view(self.current_page, disabled=True)
                await self.message.edit(view=self, content=None, embed=None, allowed_mentions=discord.AllowedMentions.none())

        except discord.HTTPException:
            pass

    async def first_page(self, interaction: discord.Interaction):
        await self.show_page(interaction, 0)

    async def previous_page(self, interaction: discord.Interaction):
        page = self.total_pages if (self.loop and self.current_page == 0) else max(0, self.current_page - 1)
        await self.show_page(interaction, page)

    async def next_page(self, interaction: discord.Interaction):
        page = 0 if (self.loop and self.current_page == self.total_pages) else min(self.total_pages, self.current_page + 1)
        await self.show_page(interaction, page)

    async def last_page(self, interaction: discord.Interaction):
        await self.show_page(interaction, self.total_pages)

    async def jump_page(self, interaction: discord.Interaction):
        await interaction.response.send_modal(_JumpModal(self))

    async def delete_page(self, interaction: discord.Interaction):
        try:
            await interaction.message.delete()

        except discord.HTTPException:
            pass
        
        self.stop()

    async def start(self):
        if self.total_pages < 0:
            if isinstance(self.ctx, discord.Interaction):
                return await self.ctx.response.send_message("Nothing to paginate.", ephemeral=True)
            return await self.ctx.send("Nothing to paginate.")

        self.sync_buttons()
        await self.build_view(0)

        if isinstance(self.ctx, discord.Interaction):
            send_kwargs = {"view": self, "ephemeral": self.ephemeral, "content": None, "embed": None}
            send_kwargs["allowed_mentions"] = discord.AllowedMentions.none()

            if self.ctx.response.is_done():
                self.message = await self.ctx.followup.send(**send_kwargs, wait=True)
            else:
                await self.ctx.response.send_message(**send_kwargs)
                self.message = await self.ctx.original_response()
        else:
            send = self.ctx.reply if self.reply else self.ctx.send
            send_kwargs = {"view": self, "content": None, "embed": None}
            send_kwargs["allowed_mentions"] = discord.AllowedMentions.none()

            if self.silent:
                send_kwargs["silent"] = True

            self.message = await send(**send_kwargs)

"""
Mythos Discord Bot
Copyright (C) 2026 xylen-py
GitHub: https://github.com/xylen-py
"""
