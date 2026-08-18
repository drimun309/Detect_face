"""Enable pgvector and grant local app user."""
import psycopg2

admin = psycopg2.connect(
    host="127.0.0.1",
    port=5432,
    user="postgres",
    password="postgres",
    dbname="vision-fr",
)
admin.autocommit = True
cur = admin.cursor()
cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
cur.execute("GRANT ALL ON SCHEMA public TO didi")
cur.execute("GRANT ALL PRIVILEGES ON DATABASE \"vision-fr\" TO didi")
cur.execute("ALTER DATABASE \"vision-fr\" OWNER TO didi")
cur.execute("SELECT extname, extversion FROM pg_extension WHERE extname='vector'")
print("vector:", cur.fetchall())
cur.close()
admin.close()

app = psycopg2.connect(
    host="127.0.0.1",
    port=5432,
    user="didi",
    password="didi123",
    dbname="vision-fr",
)
app.autocommit = True
acur = app.cursor()
acur.execute("SELECT 1")
print("didi connection OK")
acur.close()
app.close()
