import os
import sys
import re
import cv2
import time
import json
import requests
import pandas as pd
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup as BS
from tqdm import tqdm
from PIL import Image
from urllib.request import urlopen

# my modules
from utils.format_image import format_image
from utils.yandex_api import get_new_link, create_folder, upload_file
from utils.change_dateend import change_dateend

link = "https://www.mkslift.ru/export_xml.php?key=176ec86554e7edcec3dd5ef05dd58d9d"
file_name = "Выгрузка Промторг"

# С инета
xml_response = requests.get(link)
root = ET.fromstring(xml_response.text)

# с файла
# tree = ET.parse('export_xml.xml')
# root = tree.getroot()
# root = ET.fromstring(root.text)


# root_key_list = ['ED807', 'BICDirectoryEntry'] 
# with open('export_xml.xml', encoding='cp1251') as fd:
#     df = pdx.read_xml(fd.read(), root_key_list)
# root = pd.read_xml('export_xml.xml', parser="etree")

# открываем xlsx файл 
df = pd.read_excel(f"{file_name}.xlsx", sheet_name='Объявления')

with open('D:/my/Programming/avito-sales/env.json', encoding='utf-8') as settings_file:
    settings = json.load(settings_file)

yandex_token = settings['accounts'][0]['data']['yandex_token']

yandex_image_folder_path = 'MKSLIFT Main pictures'
headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': f'OAuth {yandex_token}'}
offer_list = root.find('shop').find('offers').findall('offer')

for elem in tqdm(offer_list[:]):
    vendorCode = elem.find('vendorCode').text
    # res = df.set_index('Id').loc[vendorCode]
    # res = df.loc[:, ['Id']].index(vendorCode)
    try:
        index = df[df['Id'] == vendorCode].index[0]
    except:
        continue
    
    # images urls
    imageUrls = []
    if elem.find('picture') is not None:
        origURL = elem.find('picture').text
        origURL = origURL.replace("http://www.mkslift.ruhttp://www.mkslift.ru", "http://www.mkslift.ru")
        filename = origURL.split('/')[-1]
        resized_img = format_image(origURL)
        cv2.imwrite(filename, resized_img)
        upload_file(filename, f'{yandex_image_folder_path}/{filename}', headers, True)
        os.remove(filename)
        new_URL = get_new_link(filename, yandex_image_folder_path)
        imageUrls.append(new_URL) # главная картинка в формате 4:3

    if elem.find('images') is not None:
        for image in elem.find('images').findall('image'):
            imageUrls.append(image.text) # дополнительные картинки
    imageUrls = " | ".join(imageUrls)

    df.loc[index, 'ImageUrls'] = imageUrls

df.to_excel(f'{file_name}_2.xlsx', sheet_name='Объявления', index=False)

