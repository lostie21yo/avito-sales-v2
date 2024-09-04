import os
import sys
import re
import cv2
import time
import requests
import pandas as pd
from datetime import *
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup as BS
from tqdm import tqdm, trange
from PIL import Image
from urllib.request import urlopen
from collections import Counter
from donor_checkers.utils.yandex_api import get_new_link, create_folder, upload_file

def update_WDKOPT_price(yandex_token):

    headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': f'OAuth {yandex_token}'}

    # парсинг прайса вдк
    donor_file = pd.ExcelFile(f"sources/Прайс WDK Июль.xlsb")

    wdk_price_df = pd.read_excel(f"sources/Wiederkraft price.xlsx", sheet_name="WDK price")
    wdk_unique_Ids = wdk_price_df["Id"]

    opt_price_df = pd.read_excel(f"sources/Optimus price.xlsx", sheet_name="OPT price")
    opt_unique_Ids = opt_price_df["Id"]

    new_count = 0
    old_count = 0

    for sheet_name in donor_file.sheet_names[1:]:
        print(sheet_name)
        if sheet_name == "Лист7":
            print(sheet_name, "skipped")
            continue
        donor_price_df = pd.read_excel(donor_file, sheet_name=sheet_name)
        if sheet_name == "Optimus":
            for i in trange(len(donor_price_df)):
                try:
                    vendorCode = re.match(r"[ A-Za-z\d-/]+", str(donor_price_df.loc[i, donor_price_df.columns[1]]))[0].strip()
                    price = round(float(donor_price_df.loc[i, donor_price_df.columns[4]]), 2)
                    if pd.isna(vendorCode) or vendorCode == "nan":
                        continue
                    if vendorCode not in opt_unique_Ids.values:
                        new_index = len(opt_price_df.index)
                        opt_price_df.loc[new_index, 'Id'] = vendorCode
                        opt_price_df.loc[new_index, 'Price'] = price
                        new_count += 1
                    else:
                        index = opt_price_df[opt_price_df['Id'] == vendorCode].index[0]
                        # print(index, vendorCode, price)
                        opt_price_df.loc[index, 'Price'] = price
                        old_count += 1
                except:
                    pass
        else:
            for i in trange(len(donor_price_df)):
                try:
                    vendorCode = re.match(r"[ A-Za-z\d-/]+", str(donor_price_df.loc[i, donor_price_df.columns[1]]))[0].strip()
                    price = round(float(donor_price_df.loc[i, donor_price_df.columns[4]]), 2)
                    if pd.isna(vendorCode) or vendorCode == "nan":
                        continue
                    if vendorCode not in wdk_unique_Ids.values:
                        new_index = len(wdk_price_df.index)
                        wdk_price_df.loc[new_index, 'Id'] = vendorCode
                        wdk_price_df.loc[new_index, 'Price'] = price
                        new_count += 1
                    else:
                        index = wdk_price_df[wdk_price_df['Id'] == vendorCode].index[0]
                        # print(index, vendorCode, price)
                        wdk_price_df.loc[index, 'Price'] = price
                        old_count += 1
                except:
                    pass
        
    print('Saving to YandexDisk')
    wdk_price_df = wdk_price_df.drop_duplicates(subset=["Id", "Price"], keep='first')
    wdk_price_df.to_excel(f"sources/Wiederkraft price.xlsx", sheet_name="WDK price", index=False)
    upload_file(f"sources/Wiederkraft price.xlsx", f'/Wiederkraft price.xlsx', headers, replace=True)
    opt_price_df = opt_price_df.drop_duplicates(subset=["Id", "Price"], keep='first')
    opt_price_df.to_excel(f"sources/Optimus price.xlsx", sheet_name="OPT price", index=False)
    upload_file(f"sources/Optimus price.xlsx", f'/Optimus price.xlsx', headers, replace=True)

    return {'new': new_count, 'old': old_count}
        


yandex_token = "y0_AgAAAAB3PjE7AAwShgAAAAEJ30hAAABEzz9MQBNKkLSRUWhuWW3Ezc9xxQ"
print(update_WDKOPT_price(yandex_token))
