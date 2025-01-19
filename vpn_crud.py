import sqlite3

DATABASE = 'vpn_servers.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    return conn

def create_vpn_server(node_id: int, hostname: str, ip: str, country_long: str, country_short: str, openvpn_config_data_base64: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO vpn_servers (node_id, hostname, ip, country_long, country_short, openvpn_config_data_base64)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', (node_id, hostname, ip, country_long, country_short, openvpn_config_data_base64))
    conn.commit()
    conn.close()

def read_vpn_server(node_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM vpn_servers WHERE node_id = ?', (node_id,))
    vpn_server = cursor.fetchone()
    conn.close()
    return vpn_server

def read_vpn_servers_by_ip(ip: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM vpn_servers WHERE ip = ?', (ip,))
    vpn_servers = cursor.fetchall()
    conn.close()
    return vpn_servers

def update_vpn_server(node_id: int, hostname: str, ip: str, country_long: str, country_short: str, openvpn_config_data_base64: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    UPDATE vpn_servers
    SET hostname = ?, ip = ?, country_long = ?, country_short = ?, openvpn_config_data_base64 = ?
    WHERE node_id = ?
    ''', (hostname, ip, country_long, country_short, openvpn_config_data_base64, node_id))
    conn.commit()
    conn.close()

def delete_vpn_server(node_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM vpn_servers WHERE node_id = ?', (node_id,))
    conn.commit()
    conn.close()