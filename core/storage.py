import json, os, sqlite3, threading
from typing import Any

DATABASE_URL=os.getenv('DATABASE_URL','').strip()
DB_PATH=os.getenv('BOT_DB_PATH','data/bot.db')
DEFAULT_PREFIX=os.getenv('DEFAULT_PREFIX','-')[:5] or '-'
USE_POSTGRES=bool(DATABASE_URL)
if not USE_POSTGRES:
    os.makedirs(os.path.dirname(DB_PATH) or '.',exist_ok=True)
_lock=threading.RLock()

if USE_POSTGRES:
    import psycopg
    from psycopg.rows import dict_row

def _connect():
    if USE_POSTGRES:
        return psycopg.connect(DATABASE_URL, autocommit=False, row_factory=dict_row)
    db=sqlite3.connect(DB_PATH,timeout=30); db.row_factory=sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL'); db.execute('PRAGMA foreign_keys=ON'); return db

def _sql(sql):
    if not USE_POSTGRES:return sql
    s=sql.replace('?','%s')
    s=s.replace('INSERT OR IGNORE INTO','INSERT INTO')
    if 'INSERT INTO' in s and 'ON CONFLICT' not in s and ('guild_settings(guild_id,prefix)' in s or 'levels(guild_id,user_id)' in s):
        s += ' ON CONFLICT DO NOTHING'
    return s

def init_db():
    schema_pg=f'''CREATE TABLE IF NOT EXISTS guild_settings(guild_id BIGINT PRIMARY KEY,prefix TEXT NOT NULL DEFAULT '{DEFAULT_PREFIX}',settings_json TEXT NOT NULL DEFAULT '{{}}',updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS warnings(id BIGSERIAL PRIMARY KEY,guild_id BIGINT,user_id BIGINT,moderator_id BIGINT,reason TEXT,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS mod_cases(id BIGSERIAL PRIMARY KEY,guild_id BIGINT,user_id BIGINT,moderator_id BIGINT,action TEXT,reason TEXT,expires_at DOUBLE PRECISION,active INTEGER DEFAULT 1,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS notes(id BIGSERIAL PRIMARY KEY,guild_id BIGINT,user_id BIGINT,moderator_id BIGINT,note TEXT,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS levels(guild_id BIGINT,user_id BIGINT,xp INTEGER DEFAULT 0,messages INTEGER DEFAULT 0,last_xp DOUBLE PRECISION DEFAULT 0,PRIMARY KEY(guild_id,user_id));
CREATE TABLE IF NOT EXISTS level_roles(guild_id BIGINT,level INTEGER,role_id BIGINT,PRIMARY KEY(guild_id,level));
CREATE TABLE IF NOT EXISTS reaction_roles(guild_id BIGINT,channel_id BIGINT,message_id BIGINT,emoji TEXT,role_id BIGINT,PRIMARY KEY(message_id,emoji));
CREATE TABLE IF NOT EXISTS tickets(channel_id BIGINT PRIMARY KEY,guild_id BIGINT,opener_id BIGINT,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS tags(guild_id BIGINT,name TEXT,content TEXT,owner_id BIGINT,uses INTEGER DEFAULT 0,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY(guild_id,name));
CREATE TABLE IF NOT EXISTS joinable_ranks(guild_id BIGINT,role_id BIGINT,name TEXT,PRIMARY KEY(guild_id,role_id));
CREATE TABLE IF NOT EXISTS ignored(guild_id BIGINT,kind TEXT,target_id BIGINT,PRIMARY KEY(guild_id,kind,target_id));
CREATE TABLE IF NOT EXISTS moderators(guild_id BIGINT,role_id BIGINT,PRIMARY KEY(guild_id,role_id));
CREATE TABLE IF NOT EXISTS role_persist(guild_id BIGINT,user_id BIGINT,role_id BIGINT,PRIMARY KEY(guild_id,user_id,role_id));
CREATE TABLE IF NOT EXISTS temp_roles(id BIGSERIAL PRIMARY KEY,guild_id BIGINT,user_id BIGINT,role_id BIGINT,expires_at DOUBLE PRECISION,active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS reminders(id BIGSERIAL PRIMARY KEY,user_id BIGINT,guild_id BIGINT,channel_id BIGINT,message TEXT,remind_at DOUBLE PRECISION,done INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS afk(guild_id BIGINT,user_id BIGINT,reason TEXT,since DOUBLE PRECISION,PRIMARY KEY(guild_id,user_id));
CREATE TABLE IF NOT EXISTS highlights(guild_id BIGINT,user_id BIGINT,phrase TEXT,PRIMARY KEY(guild_id,user_id,phrase));
CREATE TABLE IF NOT EXISTS giveaways(id BIGSERIAL PRIMARY KEY,guild_id BIGINT,channel_id BIGINT,message_id BIGINT,prize TEXT,winners INTEGER,end_at DOUBLE PRECISION,ended INTEGER DEFAULT 0,host_id BIGINT);
CREATE TABLE IF NOT EXISTS command_rules(guild_id BIGINT,command TEXT,enabled INTEGER DEFAULT 1,PRIMARY KEY(guild_id,command));
CREATE TABLE IF NOT EXISTS custom_commands(guild_id BIGINT,name TEXT,response TEXT,enabled INTEGER DEFAULT 1,owner_id BIGINT,uses INTEGER DEFAULT 0,PRIMARY KEY(guild_id,name));'''
    schema_sqlite=schema_pg.replace('BIGSERIAL PRIMARY KEY','INTEGER PRIMARY KEY AUTOINCREMENT').replace('BIGINT','INTEGER').replace('DOUBLE PRECISION','REAL')
    with _lock,_connect() as db:
        if USE_POSTGRES:
            for stmt in schema_pg.split(';'):
                if stmt.strip(): db.execute(stmt)
        else: db.executescript(schema_sqlite)
        db.commit()
    print('[storage] backend:', 'PostgreSQL' if USE_POSTGRES else 'SQLite fallback')

def execute(sql,args=()):
    with _lock,_connect() as db:
        c=db.execute(_sql(sql),args); rc=c.rowcount; lid=getattr(c,'lastrowid',None); db.commit(); return rc,lid

def query(sql,args=()):
    with _lock,_connect() as db:return db.execute(_sql(sql),args).fetchall()
def one(sql,args=()):
    with _lock,_connect() as db:return db.execute(_sql(sql),args).fetchone()

def get_guild_settings(gid:int)->dict[str,Any]:
    r=one('SELECT prefix,settings_json FROM guild_settings WHERE guild_id=?',(gid,))
    if not r:
        execute('INSERT OR IGNORE INTO guild_settings(guild_id,prefix) VALUES(?,?)',(gid,DEFAULT_PREFIX)); return {'prefix':DEFAULT_PREFIX}
    d=json.loads(r['settings_json'] or '{}'); d['prefix']=r['prefix'] or DEFAULT_PREFIX; return d

def update_guild_settings(gid:int,**changes):
    cur=get_guild_settings(gid); prefix=str(changes.pop('prefix',cur.pop('prefix',DEFAULT_PREFIX)))[:5] or DEFAULT_PREFIX; cur.update(changes)
    execute("INSERT INTO guild_settings(guild_id,prefix,settings_json) VALUES(?,?,?) ON CONFLICT(guild_id) DO UPDATE SET prefix=excluded.prefix,settings_json=excluded.settings_json,updated_at=CURRENT_TIMESTAMP",(gid,prefix,json.dumps(cur,ensure_ascii=False)))
    cur['prefix']=prefix; return cur

def add_warning(g,u,m,reason):
    if USE_POSTGRES:
        with _lock,_connect() as db:
            r=db.execute('INSERT INTO warnings(guild_id,user_id,moderator_id,reason) VALUES(%s,%s,%s,%s) RETURNING id',(g,u,m,reason)).fetchone(); db.commit(); return r['id']
    return execute('INSERT INTO warnings(guild_id,user_id,moderator_id,reason) VALUES(?,?,?,?)',(g,u,m,reason))[1]
def get_warnings(g,u):return query('SELECT * FROM warnings WHERE guild_id=? AND user_id=? ORDER BY id DESC LIMIT 50',(g,u))
def clear_warnings(g,u):return execute('DELETE FROM warnings WHERE guild_id=? AND user_id=?',(g,u))[0]
def delete_warning(g,wid):return execute('DELETE FROM warnings WHERE guild_id=? AND id=?',(g,wid))[0]
def get_level_user(g,u):
    execute('INSERT OR IGNORE INTO levels(guild_id,user_id) VALUES(?,?)',(g,u)); return one('SELECT * FROM levels WHERE guild_id=? AND user_id=?',(g,u))
def set_level_user(g,u,**kw):
    r=get_level_user(g,u); vals={k:(kw[k] if kw.get(k) is not None else r[k]) for k in ('xp','messages','last_xp')}
    execute('UPDATE levels SET xp=?,messages=?,last_xp=? WHERE guild_id=? AND user_id=?',(max(0,int(vals['xp'])),max(0,int(vals['messages'])),float(vals['last_xp']),g,u)); return vals
def leaderboard(g,limit=10):return query('SELECT * FROM levels WHERE guild_id=? ORDER BY xp DESC LIMIT ?',(g,limit))
def set_level_role(g,l,r):execute('INSERT INTO level_roles(guild_id,level,role_id) VALUES(?,?,?) ON CONFLICT(guild_id,level) DO UPDATE SET role_id=excluded.role_id',(g,l,r))
def get_level_roles(g):return query('SELECT level,role_id FROM level_roles WHERE guild_id=? ORDER BY level',(g,))
def delete_level_role(g,l):execute('DELETE FROM level_roles WHERE guild_id=? AND level=?',(g,l))
