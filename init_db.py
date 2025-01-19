import sqlite3

DATABASE = 'vpn_servers.db'

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS vpn_servers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        node_id INTEGER,
        hostname TEXT,
        ip TEXT,
        country_long TEXT,
        country_short TEXT,
        openvpn_config_data_base64 TEXT
    )
    ''')
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")