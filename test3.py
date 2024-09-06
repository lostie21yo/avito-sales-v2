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

donor_link = "https://100kwatt.ru/gidravlicheskoe-oborudovanie-i-instrument/page-1/"
html = BS(requests.get(donor_link).content, 'html.parser')
for product in html.find_all("div", {"class": "ty-column4"}):
    # выявление артикула и цены не переходя на страницу продукта
    vendorCode = "KWT-" + re.search(r'([\d\w -/]+) \(', product.find("span", {"class": "ty-control-group__item"}).text)[1]
    price = int(int(''.join(re.findall(r'\d+', product.find("span", {"class": "ty-price-num"}).text)))*((100 - 3)/100))
    # price = round(int(''.join(re.findall(r'\d+', product.find("span", {"class": "ty-price-num"})*((100 - 3)/100).text))), 0)

    print(vendorCode, price)
