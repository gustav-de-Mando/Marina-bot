import random,discord
from discord.ext import commands
class Dice(commands.Cog):
    def __init__(self,bot):self.bot=bot
    @commands.hybrid_command(name='dice',aliases=['würfel'],description='Wirft Würfel, z. B. 2d6.')
    async def dice(self,ctx,notation:str='1d6'):
        try:n,s=map(int,notation.lower().split('d'))
        except:return await ctx.send('❌ Format: `2d6`.')
        if not 1<=n<=20 or not 2<=s<=100000:return await ctx.send('❌ Erlaubt: 1–20 Würfel, 2–100000 Seiten.')
        rolls=[random.randint(1,s) for _ in range(n)];await ctx.send(f'🎲 {", ".join(map(str,rolls))} → **{sum(rolls)}**')
    @commands.hybrid_command(name='coin',aliases=['münze'])
    async def coin(self,ctx):await ctx.send('🪙 '+random.choice(['Kopf','Zahl']))
    @commands.hybrid_command(name='randommember')
    async def randommember(self,ctx):
        ms=[m for m in ctx.guild.members if not m.bot];await ctx.send(f'🎯 {random.choice(ms).mention}' if ms else 'Keine Mitglieder.')
async def setup(bot):await bot.add_cog(Dice(bot))
