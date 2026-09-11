import json, os, sqlite3, threading, time
from typing import Any
DB_PATH=os.getenv('BOT_DB_PATH','data/bot.db')
os.makedirs(os.path.dirname(DB_PATH),exist_ok=True)
_lock=threading.RLock()
def _connect():
    db=sqlite3.connect(DB_PATH,timeout=30); db.row_factory=sqlite3.Row
    db.execute('PRAGMA journal_mode=WAL'); db.execute('PRAGMA foreign_keys=ON'); return db

def init_db():
    with _lock,_connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS guild_settings(guild_id INTEGER PRIMARY KEY,prefix TEXT NOT NULL DEFAULT '!',settings_json TEXT NOT NULL DEFAULT '{}',updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS warnings(id INTEGER PRIMARY KEY AUTOINCREMENT,guild_id INTEGER,user_id INTEGER,moderator_id INTEGER,reason TEXT,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS mod_cases(id INTEGER PRIMARY KEY AUTOINCREMENT,guild_id INTEGER,user_id INTEGER,moderator_id INTEGER,action TEXT,reason TEXT,expires_at REAL,active INTEGER DEFAULT 1,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS notes(id INTEGER PRIMARY KEY AUTOINCREMENT,guild_id INTEGER,user_id INTEGER,moderator_id INTEGER,note TEXT,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS levels(guild_id INTEGER,user_id INTEGER,xp INTEGER DEFAULT 0,messages INTEGER DEFAULT 0,last_xp REAL DEFAULT 0,PRIMARY KEY(guild_id,user_id));
        CREATE TABLE IF NOT EXISTS level_roles(guild_id INTEGER,level INTEGER,role_id INTEGER,PRIMARY KEY(guild_id,level));
        CREATE TABLE IF NOT EXISTS reaction_roles(guild_id INTEGER,channel_id INTEGER,message_id INTEGER,emoji TEXT,role_id INTEGER,PRIMARY KEY(message_id,emoji));
        CREATE TABLE IF NOT EXISTS tickets(channel_id INTEGER PRIMARY KEY,guild_id INTEGER,opener_id INTEGER,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS tags(guild_id INTEGER,name TEXT,content TEXT,owner_id INTEGER,uses INTEGER DEFAULT 0,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY(guild_id,name));
        CREATE TABLE IF NOT EXISTS joinable_ranks(guild_id INTEGER,role_id INTEGER,name TEXT,PRIMARY KEY(guild_id,role_id));
        CREATE TABLE IF NOT EXISTS ignored(guild_id INTEGER,kind TEXT,target_id INTEGER,PRIMARY KEY(guild_id,kind,target_id));
        CREATE TABLE IF NOT EXISTS moderators(guild_id INTEGER,role_id INTEGER,PRIMARY KEY(guild_id,role_id));
        CREATE TABLE IF NOT EXISTS role_persist(guild_id INTEGER,user_id INTEGER,role_id INTEGER,PRIMARY KEY(guild_id,user_id,role_id));
        CREATE TABLE IF NOT EXISTS temp_roles(id INTEGER PRIMARY KEY AUTOINCREMENT,guild_id INTEGER,user_id INTEGER,role_id INTEGER,expires_at REAL,active INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS reminders(id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,guild_id INTEGER,channel_id INTEGER,message TEXT,remind_at REAL,done INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS afk(guild_id INTEGER,user_id INTEGER,reason TEXT,since REAL,PRIMARY KEY(guild_id,user_id));
        CREATE TABLE IF NOT EXISTS highlights(guild_id INTEGER,user_id INTEGER,phrase TEXT,PRIMARY KEY(guild_id,user_id,phrase));
        CREATE TABLE IF NOT EXISTS giveaways(id INTEGER PRIMARY KEY AUTOINCREMENT,guild_id INTEGER,channel_id INTEGER,message_id INTEGER,prize TEXT,winners INTEGER,end_at REAL,ended INTEGER DEFAULT 0,host_id INTEGER);
        CREATE TABLE IF NOT EXISTS command_rules(guild_id INTEGER,command TEXT,enabled INTEGER DEFAULT 1,PRIMARY KEY(guild_id,command));
        CREATE TABLE IF NOT EXISTS custom_commands(guild_id INTEGER,name TEXT,response TEXT,enabled INTEGER DEFAULT 1,owner_id INTEGER,uses INTEGER DEFAULT 0,PRIMARY KEY(guild_id,name));
        ''')

def get_guild_settings(gid:int)->dict[str,Any]:
    with _lock,_connect() as db:
        r=db.execute('SELECT prefix,settings_json FROM guild_settings WHERE guild_id=?',(gid,)).fetchone()
        if not r:
            db.execute('INSERT OR IGNORE INTO guild_settings(guild_id) VALUES(?)',(gid,)); return {'prefix':'!'}
        d=json.loads(r['settings_json'] or '{}'); d['prefix']=r['prefix'] or '!'; return d

def update_guild_settings(gid:int,**changes):
    cur=get_guild_settings(gid); prefix=str(changes.pop('prefix',cur.pop('prefix','!')))[:5] or '!'; cur.update(changes)
    with _lock,_connect() as db:
        db.execute("INSERT INTO guild_settings(guild_id,prefix,settings_json) VALUES(?,?,?) ON CONFLICT(guild_id) DO UPDATE SET prefix=excluded.prefix,settings_json=excluded.settings_json,updated_at=CURRENT_TIMESTAMP",(gid,prefix,json.dumps(cur,ensure_ascii=False)))
    cur['prefix']=prefix; return cur

def execute(sql,args=()):
    with _lock,_connect() as db:
        c=db.execute(sql,args); return c.rowcount,c.lastrowid

def query(sql,args=()):
    with _lock,_connect() as db: return db.execute(sql,args).fetchall()
def one(sql,args=()):
    with _lock,_connect() as db: return db.execute(sql,args).fetchone()

def add_warning(g,u,m,reason): return execute('INSERT INTO warnings(guild_id,user_id,moderator_id,reason) VALUES(?,?,?,?)',(g,u,m,reason))[1]
def get_warnings(g,u): return query('SELECT * FROM warnings WHERE guild_id=? AND user_id=? ORDER BY id DESC LIMIT 50',(g,u))
def clear_warnings(g,u): return execute('DELETE FROM warnings WHERE guild_id=? AND user_id=?',(g,u))[0]
def delete_warning(g,wid): return execute('DELETE FROM warnings WHERE guild_id=? AND id=?',(g,wid))[0]
def get_level_user(g,u):
    execute('INSERT OR IGNORE INTO levels(guild_id,user_id) VALUES(?,?)',(g,u)); return one('SELECT * FROM levels WHERE guild_id=? AND user_id=?',(g,u))
def set_level_user(g,u,**kw):
    r=get_level_user(g,u); vals={k:(kw[k] if kw.get(k) is not None else r[k]) for k in ('xp','messages','last_xp')}
    execute('UPDATE levels SET xp=?,messages=?,last_xp=? WHERE guild_id=? AND user_id=?',(max(0,int(vals['xp'])),max(0,int(vals['messages'])),float(vals['last_xp']),g,u)); return vals
def leaderboard(g,limit=10): return query('SELECT * FROM levels WHERE guild_id=? ORDER BY xp DESC LIMIT ?',(g,limit))
def set_level_role(g,l,r): execute('INSERT INTO level_roles(guild_id,level,role_id) VALUES(?,?,?) ON CONFLICT(guild_id,level) DO UPDATE SET role_id=excluded.role_id',(g,l,r))
def get_level_roles(g): return query('SELECT level,role_id FROM level_roles WHERE guild_id=? ORDER BY level',(g,))
def delete_level_role(g,l): execute('DELETE FROM level_roles WHERE guild_id=? AND level=?',(g,l))
