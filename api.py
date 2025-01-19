from fastapi import FastAPI
import uvicorn
import requests
import pandas as pd
from io import StringIO
from vpn_crud import *

app = FastAPI(
    title="OpenVPN Configuration API",
    description="This is a simple API to get OpenVPN configuration file",
    version="0.1",
)

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/get_vpncfg/{node_id}")
def get_vpncfg(node_id: int):
    response = requests.get('http://www.vpngate.net/api/iphone/')
    if response.status_code == 200:
        csv_data = response.text
        data = StringIO(csv_data)
        vpn_list = pd.read_csv(data, skiprows=1)
        vpn_list = vpn_list[vpn_list['Speed'] >  50000000.0]
        vpn_list = vpn_list[vpn_list['Uptime'] >  604800000.0]
        for index, row in vpn_list.iterrows():
            node_id = node_id
            vpn_ip = row['IP']
            hostname = row['#HostName']
            country_long = row['CountryLong']
            country_short = row['CountryShort']
            openvpn_config_data_base64 = row['OpenVPN_ConfigData_Base64']
            vpn_server = read_vpn_servers_by_ip(vpn_ip)
            if not vpn_server:
                create_vpn_server(node_id, hostname, vpn_ip, country_long, country_short, openvpn_config_data_base64)
                return {
                    "node_id": node_id,
                    "hostname": hostname,
                    "vpn_ip": vpn_ip,
                    "country_long": country_long,
                    "country_short": country_short,
                    "openvpn_config_data_base64": openvpn_config_data_base64
                }
            else:
                print(f"VPN {row['IP']} already assigned to another node")
                continue
        return {"error": "No VPN server available"}
    else:
        return {"error": "Failed to fetch VPN servers"}

@app.get("/vpn/{node_id}")
def read_vpn(node_id: int):
    vpn_server = read_vpn_server(node_id)
    if vpn_server:
        return {
            "node_id": vpn_server[1],
            "hostname": vpn_server[2],
            "vpn_ip": vpn_server[3],
            "country_long": vpn_server[4],
            "country_short": vpn_server[5],
            "openvpn_config_data_base64": vpn_server[6]
        }
    else:
        return {"error": "VPN server not found"}

@app.put("/vpn/{node_id}")
def update_vpn(node_id: int, hostname: str, vpn_ip: str, country_long: str, country_short: str, openvpn_config_data_base64: str):
    update_vpn_server(node_id, hostname, vpn_ip, country_long, country_short, openvpn_config_data_base64)
    return {"message": "VPN server updated successfully"}

@app.delete("/vpn/{node_id}")
def delete_vpn(node_id: int):
    delete_vpn_server(node_id)
    return {"message": "VPN server deleted successfully"}

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
