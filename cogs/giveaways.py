import discord,time,random
from discord.ext import commands,tasks
from core.storage import execute,query,one
from core.timeparse import parse_duration,human

class Giveaways(commands.Cog):
    def __init__(self,bot): self.bot=bot; self.worker.start()
    def cog_unload(self): self.worker.cancel()

    @commands.hybrid_command(name='giveaway',description='Erstellt ein Giveaway.')
    @commands.has_permissions(manage_guild=True)
    async def giveaway(self,ctx,duration:str,winners:commands.Range[int,1,20]=1,*,prize:str):
        try:s=parse_duration(duration,2592000)
        except ValueError as e:return await ctx.send(f'❌ {e}')
        end=time.time()+s; e=discord.Embed(title='🎉 GIVEAWAY',description=f'**{prize}**\n\nReagiere mit 🎉 zum Teilnehmen.\nGewinner: **{winners}**\nEndet <t:{int(end)}:R>',color=discord.Color.gold()); e.set_footer(text=f'Host: {ctx.author}')
        msg=await ctx.send(embed=e); await msg.add_reaction('🎉'); _,gid=execute('INSERT INTO giveaways(guild_id,channel_id,message_id,prize,winners,end_at,host_id) VALUES(?,?,?,?,?,?,?)',(ctx.guild.id,ctx.channel.id,msg.id,prize,winners,end,ctx.author.id));
        if ctx.interaction: await ctx.interaction.followup.send(f'Giveaway #{gid} erstellt.',ephemeral=True)

    @commands.hybrid_command(name='giveaway_end')
    @commands.has_permissions(manage_guild=True)
    async def giveaway_end(self,ctx,giveaway_id:int):
        r=one('SELECT * FROM giveaways WHERE guild_id=? AND id=?',(ctx.guild.id,giveaway_id));
        if not r:return await ctx.send('❌ Nicht gefunden.')
        execute('UPDATE giveaways SET end_at=? WHERE id=?',(time.time(),giveaway_id)); await ctx.send('✅ Wird beendet.')

    async def finish(self,r):
        g=self.bot.get_guild(r['guild_id']); ch=g.get_channel(r['channel_id']) if g else None
        if not ch:return execute('UPDATE giveaways SET ended=1 WHERE id=?',(r['id'],))
        try:m=await ch.fetch_message(r['message_id'])
        except:return execute('UPDATE giveaways SET ended=1 WHERE id=?',(r['id'],))
        reaction=discord.utils.get(m.reactions,emoji='🎉'); users=[]
        if reaction:
            async for u in reaction.users():
                if not u.bot:users.append(u)
        winners=random.sample(users,min(r['winners'],len(users))) if users else []
        execute('UPDATE giveaways SET ended=1 WHERE id=?',(r['id'],)); await ch.send(f"🎉 Giveaway **{r['prize']}** beendet! Gewinner: "+(', '.join(u.mention for u in winners) if winners else 'Keine gültigen Teilnehmer.'))

    @tasks.loop(seconds=15)
    async def worker(self):
        for r in query('SELECT * FROM giveaways WHERE ended=0 AND end_at<=?',(time.time(),)): await self.finish(r)
        for r in query('SELECT * FROM reminders WHERE done=0 AND remind_at<=?',(time.time(),)):
            ch=self.bot.get_channel(r['channel_id']);
            if ch:
                try: await ch.send(f"⏰ <@{r['user_id']}> Erinnerung: {r['message']}")
                except: pass
            execute('UPDATE reminders SET done=1 WHERE id=?',(r['id'],))
        for r in query('SELECT * FROM temp_roles WHERE active=1 AND expires_at<=?',(time.time(),)):
            g=self.bot.get_guild(r['guild_id']); m=g.get_member(r['user_id']) if g else None; role=g.get_role(r['role_id']) if g else None
            if m and role:
                try: await m.remove_roles(role,reason='Temp role expired')
                except: pass
            execute('UPDATE temp_roles SET active=0 WHERE id=?',(r['id'],))
    @worker.before_loop
    async def before(self): await self.bot.wait_until_ready()

async def setup(bot): await bot.add_cog(Giveaways(bot))
