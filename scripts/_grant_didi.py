import psycopg2

conn = psycopg2.connect(
    host="127.0.0.1",
    port=5432,
    user="postgres",
    password="postgres",
    dbname="vision-fr",
)
conn.autocommit = True
cur = conn.cursor()
cur.execute("GRANT ALL ON SCHEMA public TO didi")
cur.execute("GRANT ALL ON ALL TABLES IN SCHEMA public TO didi")
cur.execute("GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO didi")
cur.execute("ALTER DATABASE \"vision-fr\" OWNER TO didi")
cur.execute(
    """
    SELECT n.nspname, c.relname
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relkind = 'r'
    """
)
for schema, name in cur.fetchall():
    cur.execute(f'ALTER TABLE "{name}" OWNER TO didi')
cur.close()
conn.close()

app = psycopg2.connect(
    host="127.0.0.1",
    port=5432,
    user="didi",
    password="didi123",
    dbname="vision-fr",
)
cur = app.cursor()
cur.execute("SELECT count(*) FROM departments")
print("departments", cur.fetchone()[0])
cur.execute("SELECT count(*) FROM cameras")
print("cameras", cur.fetchone()[0])
cur.execute("SELECT count(*) FROM roi_timer_daily")
print("roi_timer_daily", cur.fetchone()[0])
cur.execute("SELECT id, name FROM departments")
print("dept rows", cur.fetchall())
cur.execute("SELECT id, name, department_id FROM cameras")
print("cam rows", cur.fetchall())
cur.close()
app.close()
