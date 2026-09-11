import discord
from discord.ext import commands
from core.storage import get_guild_settings

class TicketButton(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label='Ticket öffnen',style=discord.ButtonStyle.green,emoji='🎫',custom_id='ticket:open')
    async def open_ticket(self,interaction:discord.Interaction,button):
        guild=interaction.guild; s=get_guild_settings(guild.id)
        existing=discord.utils.get(guild.text_channels,name=f"ticket-{interaction.user.id}")
        if existing: return await interaction.response.send_message(f"Du hast bereits {existing.mention}.",ephemeral=True)
        category=guild.get_channel(int(s.get('ticket_category',0))) if s.get('ticket_category') else None
        overwrites={guild.default_role:discord.PermissionOverwrite(view_channel=False),interaction.user:discord.PermissionOverwrite(view_channel=True,send_messages=True,read_message_history=True),guild.me:discord.PermissionOverwrite(view_channel=True,send_messages=True,manage_channels=True)}
        ch=await guild.create_text_channel(f"ticket-{interaction.user.id}",category=category,overwrites=overwrites,reason='Support-Ticket')
        await ch.send(f"🎫 {interaction.user.mention}, beschreibe dein Anliegen. Ein Teammitglied meldet sich.")
        await interaction.response.send_message(f"✅ Ticket erstellt: {ch.mention}",ephemeral=True)

class Tickets(commands.Cog):
    def __init__(self,bot): self.bot=bot; bot.add_view(TicketButton())
    @commands.hybrid_command(name='ticketpanel',description='Erstellt ein Ticket-Panel.')
    @commands.has_permissions(administrator=True)
    async def ticketpanel(self,ctx):
        e=discord.Embed(title='🎫 Support',description='Klicke auf den Button, um ein privates Support-Ticket zu öffnen.',color=discord.Color.blurple())
        await ctx.send(embed=e,view=TicketButton())
    @commands.hybrid_command(name='ticketclose',description='Schließt das aktuelle Ticket.')
    async def ticketclose(self,ctx):
        if not ctx.channel.name.startswith('ticket-'): return await ctx.send('❌ Das ist kein Ticket-Channel.')
        owner=ctx.channel.name.removeprefix('ticket-')
        if str(ctx.author.id)!=owner and not ctx.author.guild_permissions.manage_channels: return await ctx.send('❌ Keine Berechtigung.')
        await ctx.send('🔒 Ticket wird geschlossen.'); await ctx.channel.delete(reason=f'Ticket geschlossen von {ctx.author}')
async def setup(bot): await bot.add_cog(Tickets(bot))
