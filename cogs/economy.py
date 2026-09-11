import discord,json,os,random
from discord.ext import commands
from datetime import datetime,timedelta,timezone
DATA_FILE='data/economy.json'; CURRENCY='💵'
def load_data():
    try:
        with open(DATA_FILE,encoding='utf-8') as f:return json.load(f)
    except:return {}
def save_data(data):
    os.makedirs('data',exist_ok=True)
    with open(DATA_FILE,'w',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2)
def account(data,g,u):
    return data.setdefault(str(g),{}).setdefault(str(u),{'wallet':500,'bank':0,'last_daily':None,'last_work':None})
def now():return datetime.now(timezone.utc)
def parse_dt(v):
    if not v:return None
    d=datetime.fromisoformat(v); return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d
SUITS=['♠️','♥️','♦️','♣️']; RANKS=['2','3','4','5','6','7','8','9','10','J','Q','K','A']
def deck():
    d=[(r,s) for r in RANKS for s in SUITS]; random.shuffle(d); return d
def value(hand):
    v=sum(11 if r=='A' else 10 if r in 'JQK' else int(r) for r,_ in hand); a=sum(r=='A' for r,_ in hand)
    while v>21 and a:v-=10;a-=1
    return v
def fmt(hand):return ' '.join(f'`{r}{s}`' for r,s in hand)

class Economy(commands.Cog):
    def __init__(self,bot):self.bot=bot;self.games={}
    def acc(self,ctx,member=None):
        d=load_data();m=member or ctx.author;a=account(d,ctx.guild.id,m.id);save_data(d);return d,m,a
    @commands.hybrid_command(name='balance')
    async def balance(self,ctx,member:discord.Member|None=None):
        _,m,a=self.acc(ctx,member);e=discord.Embed(title=f'💰 Konto von {m.display_name}',color=discord.Color.green());e.add_field(name='Wallet',value=f"{a['wallet']:,} {CURRENCY}");e.add_field(name='Bank',value=f"{a['bank']:,} {CURRENCY}");e.add_field(name='Gesamt',value=f"{a['wallet']+a['bank']:,} {CURRENCY}");await ctx.send(embed=e)
    @commands.hybrid_command(name='daily')
    async def daily(self,ctx):
        d,_,a=self.acc(ctx);n=now();last=parse_dt(a['last_daily'])
        if last and n-last<timedelta(hours=24):
            rem=timedelta(hours=24)-(n-last);return await ctx.send(f'❌ Nächste Daily in **{int(rem.total_seconds()//3600)}h {int(rem.total_seconds()%3600//60)}m**.')
        amt=random.randint(200,500);a['wallet']+=amt;a['last_daily']=n.isoformat();save_data(d);await ctx.send(f'📅 +**{amt:,} {CURRENCY}** • Wallet: **{a["wallet"]:,}**')
    @commands.hybrid_command(name='work')
    async def work(self,ctx):
        d,_,a=self.acc(ctx);n=now();last=parse_dt(a['last_work'])
        if last and n-last<timedelta(minutes=30):return await ctx.send(f'❌ Du kannst in **{max(1,int((timedelta(minutes=30)-(n-last)).total_seconds()//60))} Min.** wieder arbeiten.')
        amt=random.randint(50,200);a['wallet']+=amt;a['last_work']=n.isoformat();save_data(d);await ctx.send(f'💼 Arbeit erledigt: +**{amt:,} {CURRENCY}**')
    @commands.hybrid_command(name='deposit')
    async def deposit(self,ctx,amount:str):
        d,_,a=self.acc(ctx);amt=a['wallet'] if amount.lower()=='all' else int(amount) if amount.isdigit() else 0
        if amt<=0 or amt>a['wallet']:return await ctx.send('❌ Ungültiger Betrag.')
        a['wallet']-=amt;a['bank']+=amt;save_data(d);await ctx.send(f'🏦 {amt:,} eingezahlt.')
    @commands.hybrid_command(name='withdraw')
    async def withdraw(self,ctx,amount:str):
        d,_,a=self.acc(ctx);amt=a['bank'] if amount.lower()=='all' else int(amount) if amount.isdigit() else 0
        if amt<=0 or amt>a['bank']:return await ctx.send('❌ Ungültiger Betrag.')
        a['bank']-=amt;a['wallet']+=amt;save_data(d);await ctx.send(f'💸 {amt:,} abgehoben.')
    @commands.hybrid_command(name='pay')
    async def pay(self,ctx,member:discord.Member,amount:int):
        if member.bot or member==ctx.author or amount<=0:return await ctx.send('❌ Ungültig.')
        d=load_data();a=account(d,ctx.guild.id,ctx.author.id);b=account(d,ctx.guild.id,member.id)
        if a['wallet']<amount:return await ctx.send('❌ Nicht genug Wallet-Guthaben.')
        a['wallet']-=amount;b['wallet']+=amount;save_data(d);await ctx.send(f'💸 {amount:,} {CURRENCY} an {member.mention}.')
    @commands.hybrid_command(name='rob')
    async def rob(self,ctx,member:discord.Member):
        if member.bot or member==ctx.author:return await ctx.send('❌ Ungültiges Ziel.')
        d=load_data();a=account(d,ctx.guild.id,ctx.author.id);b=account(d,ctx.guild.id,member.id)
        if b['wallet']<50:return await ctx.send('❌ Ziel hat zu wenig Spielgeld.')
        if random.random()<.4:
            amt=random.randint(50,min(500,b['wallet']));a['wallet']+=amt;b['wallet']-=amt;text=f'🦹 Im Spiel erfolgreich: +{amt:,} {CURRENCY}'
        else:
            amt=random.randint(100,300);a['wallet']=max(0,a['wallet']-amt);text=f'🚔 Im Spiel gescheitert: -{amt:,} {CURRENCY}'
        save_data(d);await ctx.send(text)
    @commands.hybrid_command(name='richlist')
    async def richlist(self,ctx):
        d=load_data().get(str(ctx.guild.id),{});rows=[]
        for uid,a in d.items():
            m=ctx.guild.get_member(int(uid));
            if m:rows.append((m.display_name,a['wallet']+a['bank']))
        rows.sort(key=lambda x:x[1],reverse=True);await ctx.send(embed=discord.Embed(title='💰 Richlist',description='\n'.join(f'`{i}.` **{n}** — {v:,} {CURRENCY}' for i,(n,v) in enumerate(rows[:10],1)) or 'Keine Daten.'))
    @commands.hybrid_command(name='blackjack')
    async def blackjack(self,ctx,einsatz:int):
        if einsatz<=0:return await ctx.send('❌ Einsatz muss positiv sein.')
        d=load_data();a=account(d,ctx.guild.id,ctx.author.id);key=f'{ctx.guild.id}_{ctx.author.id}'
        if a['wallet']<einsatz:return await ctx.send('❌ Nicht genug Spielgeld.')
        if key in self.games:return await ctx.send('❌ Du hast bereits ein Spiel.')
        dk=deck();p=[dk.pop(),dk.pop()];dealer=[dk.pop(),dk.pop()];a['wallet']-=einsatz;save_data(d);self.games[key]={'deck':dk,'player':p,'dealer':dealer,'stake':einsatz,'data':d,'acc':a}
        if value(p)==21:
            a['wallet']+=int(einsatz*2.5);save_data(d);self.games.pop(key,None);return await ctx.send(f'🃏 Blackjack! +{int(einsatz*1.5):,} {CURRENCY}')
        await ctx.send(embed=self.embed(p,dealer,einsatz,True),view=BlackjackView(self,key,ctx.author.id))
    def embed(self,p,d,s,hidden=False,result=None):
        e=discord.Embed(title='🃏 Blackjack',color=discord.Color.blurple());e.add_field(name=f'Deine Hand ({value(p)})',value=fmt(p),inline=False);e.add_field(name='Dealer (?)' if hidden else f'Dealer ({value(d)})',value=f'{fmt([d[0]])} `??`' if hidden else fmt(d),inline=False);e.add_field(name='Einsatz',value=f'{s:,} {CURRENCY}');
        if result:e.add_field(name='Ergebnis',value=result,inline=False)
        return e
    async def finish(self,interaction,key):
        g=self.games.pop(key,None)
        if not g:return
        while value(g['dealer'])<17:g['dealer'].append(g['deck'].pop())
        p,d=value(g['player']),value(g['dealer']);stake=g['stake']
        if p>21:r=f'Bust: -{stake:,}'
        elif d>21 or p>d:g['acc']['wallet']+=stake*2;r=f'Gewonnen: +{stake:,}'
        elif p==d:g['acc']['wallet']+=stake;r='Unentschieden'
        else:r=f'Verloren: -{stake:,}'
        save_data(g['data']);await interaction.response.edit_message(embed=self.embed(g['player'],g['dealer'],stake,False,r),view=None)

class BlackjackView(discord.ui.View):
    def __init__(self,cog,key,user_id):super().__init__(timeout=60);self.cog=cog;self.key=key;self.user_id=user_id
    async def interaction_check(self,i):
        if i.user.id!=self.user_id:await i.response.send_message('❌ Nicht dein Spiel.',ephemeral=True);return False
        return True
    @discord.ui.button(label='Hit 🃏',style=discord.ButtonStyle.green)
    async def hit(self,i,b):
        g=self.cog.games.get(self.key)
        if not g:return await i.response.send_message('Spiel beendet.',ephemeral=True)
        g['player'].append(g['deck'].pop())
        if value(g['player'])>=21:return await self.cog.finish(i,self.key)
        await i.response.edit_message(embed=self.cog.embed(g['player'],g['dealer'],g['stake'],True),view=self)
    @discord.ui.button(label='Stand 🛑',style=discord.ButtonStyle.red)
    async def stand(self,i,b):await self.cog.finish(i,self.key)
    async def on_timeout(self):
        g=self.cog.games.pop(self.key,None)
        if g:g['acc']['wallet']+=g['stake'];save_data(g['data'])
async def setup(bot):await bot.add_cog(Economy(bot))
