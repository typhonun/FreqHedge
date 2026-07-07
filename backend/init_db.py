from app.db import get_conn

conn = get_conn()

conn.execute("""
CREATE TABLE IF NOT EXISTS strategy_config(
    side TEXT PRIMARY KEY,
    config_json TEXT NOT NULL,
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()
conn.close()

print("db initialized")