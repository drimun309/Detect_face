"""ponytail: one-shot local postgres bootstrap for UI smoke runs."""
import psycopg2

conn = psycopg2.connect(
    host="127.0.0.1",
    port=5432,
    user="postgres",
    password="postgres",
    dbname="postgres",
)
conn.autocommit = True
cur = conn.cursor()
cur.execute("SELECT datname FROM pg_database")
print("dbs:", [r[0] for r in cur.fetchall()])
cur.execute("SELECT rolname FROM pg_roles WHERE rolcanlogin")
print("roles:", [r[0] for r in cur.fetchall()])
cur.execute("SELECT name, default_version FROM pg_available_extensions WHERE name='vector'")
print("vector avail:", cur.fetchall())

cur.execute("SELECT 1 FROM pg_roles WHERE rolname='didi'")
if not cur.fetchone():
    cur.execute("CREATE USER didi WITH PASSWORD 'didi123'")
    print("created user didi")
else:
    print("user didi exists")

cur.execute("SELECT 1 FROM pg_database WHERE datname='vision-fr'")
if not cur.fetchone():
    cur.execute('CREATE DATABASE "vision-fr" OWNER didi')
    print("created db vision-fr")
else:
    print("db vision-fr exists")

cur.close()
conn.close()

db = psycopg2.connect(
    host="127.0.0.1",
    port=5432,
    user="postgres",
    password="postgres",
    dbname="vision-fr",
)
db.autocommit = True
dcur = db.cursor()
try:
    dcur.execute("CREATE EXTENSION IF NOT EXISTS vector")
    print("vector extension ok")
except Exception as exc:
    print("vector extension FAILED:", exc)
dcur.execute("SELECT extname FROM pg_extension")
print("extensions:", [r[0] for r in dcur.fetchall()])
dcur.close()
db.close()
