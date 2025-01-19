import requests
import pandas as pd
import csv
from io import StringIO

# Function to get the list of VPN servers
def get_vpn_list():
    print('Getting the list of VPN servers...')
    response = requests.get('http://www.vpngate.net/api/iphone/')
    if response.status_code == 200:
        csv_data = response.text
        data = StringIO(csv_data)
        df = pd.read_csv(data, skiprows=1)
        return df
    else:
        print('Failed to retrieve data')
        return None

#Filter the VPN servers based on the country
def filter_vpn_list(vpn_list):
    print('Filtering the list of VPN servers...')
    if vpn_list is not None:
        filtered_vpn_list = vpn_list[vpn_list['Speed'] >  50000000.0]
        filtered_vpn_list = vpn_list[vpn_list['Uptime'] >  604800000.0]            
        return filtered_vpn_list
    else:
        print('No data to filter')
        return None

def main():
    vpn_list = get_vpn_list()
    #vpn_list = filter_vpn_list(vpn_list)
    if vpn_list is not None:
        print(vpn_list.columns)
        return(vpn_list)
    else:
        print('No data to display')
        return None

if __name__ == '__main__':
    vpn_list = main()
    print(vpn_list)