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

def change_pictures():
    
    yesterday = (datetime.now() - timedelta(days=1)).date().strftime("%Y-%m-%d")

    # для работы с Yandex.Диском
    # headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': f'OAuth {yandex_token}'}
    
    # открываем xlsx файл выгрузки
    df = pd.read_excel(f"Stoshka.xlsx", sheet_name='Объявления')

    # Обновление существующих позиций в выгрузке
    for i in trange(len(df)):
        desc = str(df.loc[i, 'Description'])

        if "🚗 🚕 🚙 🚌 🚎 🚓 🚑 🚒 🚐 🚚 🚛 🚜 🚔 🚍 🚘 🚖" in desc:
            if "RF-0100-3D" in df.loc[i, 'Title']:
                print(df.loc[i, 'Id'])

            # картинки
            imageUrls = df.loc[i, 'ImageUrls'].split(' | ')
            if len(imageUrls) > 1:
                imageUrls = ' | '.join(imageUrls[:-1])
            
                # запись
                df.loc[i, 'ImageUrls'] = imageUrls
                    
    # обработка перед финальным сохранением и сохранение
    df.to_excel(f'Stoshka.xlsx', sheet_name='Объявления', index=False)
    # upload_file(f'{excel_file_name}.xlsx', f'/{excel_file_name}.xlsx', headers, replace=True)

    """
    http://avito.ru/autoload/1/items-to-feed/images?imageSlug=/image/1/1.erO9DLaw1lqLu1RXxQ1KnMeu1FoNpd5QCw._DeVzu6C8Y3M6F6ISsT-eYK_ZM0a-ej7tN8ED85oOaw | http://avito.ru/autoload/1/items-to-feed/images?imageSlug=/image/1/1.s7Ya4bawH18sVp1ScL-_vHJDHV-qSBdVrA.kv9C2SXEzYiWwFZccin1wGtp3zaneIsbBKTCVqeP0CU
    """

change_pictures()