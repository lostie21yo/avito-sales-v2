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
from PIL import Image
from urllib.request import urlopen
from transliterate import translit

# my modules
from donor_checkers.utils.image_tools import format_image, get_ascii_url, perturb_image
from donor_checkers.utils.yandex_api import get_new_link, create_folder, upload_file

link = "https://100kwatt.ru/stanok-shos-120p/"

page = requests.get(link)
product_html = BS(page.content, 'html.parser')

# yandex_token = "y0_AgAAAAB2eAMkAAvtEgAAAAEHDYscAAAO0qWJlTtHEYrzMF1eVgrRvisOSQ"
# yandex_image_folder_path = "100kwatt Comp Main pictures"

excel_name = "Dva Domkrata"
yandex_image_folder_path = "100kwatt Hydr Main pictures"
yandex_token = "y0_AgAAAAB3PjE7AAwShgAAAAEJ30hAAABEzz9MQBNKkLSRUWhuWW3Ezc9xxQ"
donor_link = "https://100kwatt.ru/gidravlicheskoe-oborudovanie-i-instrument/page-"

headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': f'OAuth {yandex_token}'}

vendorCode = "РОСТ 6112017"

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
print(imageUrls)