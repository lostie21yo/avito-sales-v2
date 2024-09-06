# -*- coding: utf-8 -*-

import os
import sys
import re
import cv2
from time import sleep
import requests
import pandas as pd
from datetime import *
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup as BS
from tqdm import tqdm, trange
from transliterate import translit

# my modules
from donor_checkers.utils.image_tools import format_image, get_ascii_url, perturb_image
from donor_checkers.utils.yandex_api import get_new_link, create_folder, upload_file


# excel_name = "Promtorg"
# p_num = 34
# yandex_image_folder_path = "100kwatt Comp Main pictures"
# yandex_token = "y0_AgAAAAB2eAMkAAvtEgAAAAEHDYscAAAO0qWJlTtHEYrzMF1eVgrRvisOSQ"
# donor_link = "https://100kwatt.ru/vozdushnye-kompressory/page-"

excel_name = "Dva Domkrata"
p_num = 264
yandex_image_folder_path = "100kwatt Hydr Main pictures"
yandex_token = "y0_AgAAAAB3PjE7AAwShgAAAAEJ30hAAABEzz9MQBNKkLSRUWhuWW3Ezc9xxQ"
donor_link = "https://100kwatt.ru/gidravlicheskoe-oborudovanie-i-instrument/page-"

df = pd.read_excel(f"{excel_name}.xlsx", sheet_name='Объявления')

count = 0

headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': f'OAuth {yandex_token}'}

create_folder(yandex_image_folder_path, headers) # создание папки для изображений, если ее нет

for p in trange(p_num):
    if p > -1:
        link = f'{donor_link}{p+1}/'
        page = requests.get(link)
        html = BS(page.content, 'html.parser')
        
        for product in html.find_all("div", {"class": "ty-column4"}):
            try:
                product_url = product.find("div", {"class": "ut2-gl__image"}).a['href']
            except:
                continue
            product_page = requests.get(product_url)
            product_html = BS(product_page.content, 'html.parser')
                
            # артикул
            try:
                vendorCode = "KWT-" + re.search(r':\n([\d\w -/]+) \(', product_html.find("div", {"class": "ut2-pb__sku"}).text)[1]
            except:
                vendorCode = "no data"

            if vendorCode != "no data":
                try:
                    index = df[df['Id'] == vendorCode].index[0]
                except:
                    continue
                
                # print('check:', 'yandex_disk' in df.loc[index, 'ImageUrls2'])
                
                if 'yandex_disk' not in str(df.loc[index, 'ImageUrls']):
                    # картинки
                    try:
                        imageUrls = []
                        images = product_html.find("div", {"class": "ut2-pb__img-wrapper"}).find_all("a")
                        for a in images:
                            try:
                                if '/images/' in a["href"]:
                                    imageUrls.append(a["href"])
                            except: pass
                        for i in range(len(imageUrls)):
                            url = get_ascii_url(imageUrls[i])
                            filename = f'{translit(vendorCode, language_code='ru', reversed=True)}_{i}.jpg'
                            filename = re.sub(r'/', '-', filename, flags=re.IGNORECASE)
                            filename = re.sub(r'%', '', filename, flags=re.IGNORECASE)
                            resized_img = format_image(url)
                            cv2.imwrite(filename, resized_img)
                            perturbed_img = perturb_image(filename)
                            cv2.imwrite(filename, perturbed_img)
                            upload_file(filename, f'{yandex_image_folder_path}/{filename}', headers, True)
                            sleep(1)
                            os.remove(filename) 
                            imageUrls[i] = get_new_link(filename, yandex_image_folder_path)
                        imageUrls = " | ".join(imageUrls)
                    except Exception as e:
                        imageUrls = "no data"
                        print("image error", imageUrls, e)

                    # запись
                    print(p+1, vendorCode, '; old:', df.loc[index, 'ImageUrls'], '; new:', imageUrls)
                    df.loc[index, 'ImageUrls'] = imageUrls

                    count += 1

                    # периодический сейв
                    if (count%50 == 0):
                        df.to_excel(f'{excel_name}.xlsx', sheet_name='Объявления', index=False)
                        sleep(1)

df.to_excel(f'{excel_name}.xlsx', sheet_name='Объявления', index=False)
