import os,secrets,requests
from flask import Flask,redirect,request,session,render_template,url_for,abort,flash
from core.storage import get_guild_settings,update_guild_settings,query,one,execute
DISCORD_API='https://discord.com/api/v10'

def create_dashboard(bot):
    app=Flask(__name__,template_folder='templates');app.secret_key=os.environ.get('DASHBOARD_SECRET') or secrets.token_hex(32)
    app.config.update(SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Lax',SESSION_COOKIE_SECURE=os.environ.get('DASHBOARD_URL','').startswith('https://'))
    client_id=os.environ.get('DISCORD_CLIENT_ID');client_secret=os.environ.get('DISCORD_CLIENT_SECRET');base=os.environ.get('DASHBOARD_URL','http://localhost:8080').rstrip('/');redirect_uri=base+'/callback'
    def csrf():
        if 'csrf' not in session:session['csrf']=secrets.token_urlsafe(24)
        return session['csrf']
    def verify_csrf():
        if request.form.get('csrf')!=session.get('csrf'):abort(403)
    app.jinja_env.globals['csrf_token']=csrf
    @app.get('/')
    def home():return render_template('index.html',user=session.get('user'),bot=bot)
    @app.get('/login')
    def login():
        if not client_id or not client_secret:return 'DISCORD_CLIENT_ID/SECRET fehlt',500
        state=secrets.token_urlsafe(24);session['oauth_state']=state
        u='https://discord.com/oauth2/authorize?response_type=code&client_id='+client_id+'&scope=identify%20guilds&redirect_uri='+requests.utils.quote(redirect_uri,safe='')+'&state='+state
        return redirect(u)
    @app.get('/callback')
    def callback():
        if request.args.get('state')!=session.pop('oauth_state',None):abort(403)
        data={'client_id':client_id,'client_secret':client_secret,'grant_type':'authorization_code','code':request.args.get('code'),'redirect_uri':redirect_uri}
        token=requests.post(DISCORD_API+'/oauth2/token',data=data,headers={'Content-Type':'application/x-www-form-urlencoded'},timeout=10).json();access=token.get('access_token')
        if not access:return f'OAuth fehlgeschlagen: {token}',400
        h={'Authorization':f'Bearer {access}'};session['user']=requests.get(DISCORD_API+'/users/@me',headers=h,timeout=10).json();session['guilds']=requests.get(DISCORD_API+'/users/@me/guilds',headers=h,timeout=10).json();csrf();return redirect(url_for('guilds'))
    @app.get('/logout')
    def logout():session.clear();return redirect('/')
    def manageable():
        out=[]
        for g in session.get('guilds',[]):
            perms=int(g.get('permissions','0'))
            if (g.get('owner') or perms&0x8 or perms&0x20) and bot.get_guild(int(g['id'])):out.append(g)
        return out
    def require_guild(gid):
        if not session.get('user'):return None,redirect('/login')
        if gid not in {int(g['id']) for g in manageable()}:abort(403)
        g=bot.get_guild(gid)
        if not g:abort(404)
        return g,None
    @app.get('/guilds')
    def guilds():
        if not session.get('user'):return redirect('/login')
        return render_template('guilds.html',guilds=manageable())
    @app.route('/guild/<int:guild_id>',methods=['GET','POST'])
    def guild_settings(guild_id):
        guild,r=require_guild(guild_id)
        if r:return r
        if request.method=='POST':
            verify_csrf();mods=['automod','levels','welcome','goodbye','logs','tickets','suggestions','starboard','economy','music'];changes={'prefix':request.form.get('prefix','!')[:5] or '!','language':request.form.get('language','de')}
            for m in mods:changes[m+'_enabled']=m+'_enabled' in request.form
            for k in ('anti_spam','anti_caps','block_invites','anti_links','anti_mass_mentions'):changes[k]=k in request.form
            changes['blocked_words']=[x.strip() for x in request.form.get('blocked_words','').split(',') if x.strip()]
            changes['welcome_message']=request.form.get('welcome_message','')[:1800];changes['goodbye_message']=request.form.get('goodbye_message','')[:1800]
            for key in ('modlog','welcome','goodbye','levelup','suggestions','tickets','starboard','bump'):
                raw=request.form.get(key+'_channel','').strip();changes[key+'_channel']=int(raw) if raw.isdigit() else None
            for key in ('autorole','bump_role'):
                raw=request.form.get(key+'_id','').strip();changes[key+'_id']=int(raw) if raw.isdigit() else None
            for key,default,lo,hi in [('xp_min',15,1,1000),('xp_max',25,1,1000),('xp_cooldown',45,5,3600),('starboard_threshold',3,1,50)]:
                try:v=int(request.form.get(key,default));changes[key]=max(lo,min(hi,v))
                except:changes[key]=default
            if changes['xp_min']>changes['xp_max']:changes['xp_min'],changes['xp_max']=changes['xp_max'],changes['xp_min']
            update_guild_settings(guild_id,**changes);flash('Einstellungen gespeichert.','ok')
        s=get_guild_settings(guild_id);return render_template('settings.html',guild=guild,s=s,channels=guild.text_channels,roles=[x for x in guild.roles if x!=guild.default_role])
    @app.route('/guild/<int:guild_id>/commands',methods=['GET','POST'])
    def commands_page(guild_id):
        guild,r=require_guild(guild_id)
        if r:return r
        if request.method=='POST':
            verify_csrf();all_names={c.name for c in bot.commands};enabled=set(request.form.getlist('enabled'))
            for name in all_names:execute('INSERT INTO command_rules(guild_id,command,enabled) VALUES(?,?,?) ON CONFLICT(guild_id,command) DO UPDATE SET enabled=excluded.enabled',(guild_id,name,int(name in enabled)))
            flash('Command-Regeln gespeichert.','ok')
        rules={r['command']:bool(r['enabled']) for r in query('SELECT command,enabled FROM command_rules WHERE guild_id=?',(guild_id,))};cmds=sorted(bot.commands,key=lambda c:(c.cog_name or '',c.name));return render_template('commands.html',guild=guild,commands=cmds,rules=rules)
    @app.route('/guild/<int:guild_id>/customs',methods=['GET','POST'])
    def customs_page(guild_id):
        guild,r=require_guild(guild_id)
        if r:return r
        if request.method=='POST':
            verify_csrf();action=request.form.get('action');name=request.form.get('name','').lower().strip().lstrip('!/')[:40]
            if action=='save' and name:
                response=request.form.get('response','')[:2000];enabled='enabled' in request.form;execute('INSERT INTO custom_commands(guild_id,name,response,enabled,owner_id) VALUES(?,?,?,?,?) ON CONFLICT(guild_id,name) DO UPDATE SET response=excluded.response,enabled=excluded.enabled',(guild_id,name,response,int(enabled),int(session['user']['id'])));flash('Custom Command gespeichert.','ok')
            elif action=='delete' and name:execute('DELETE FROM custom_commands WHERE guild_id=? AND name=?',(guild_id,name));flash('Custom Command gelöscht.','ok')
        rows=query('SELECT * FROM custom_commands WHERE guild_id=? ORDER BY name',(guild_id,));return render_template('customs.html',guild=guild,rows=rows)
    return app
