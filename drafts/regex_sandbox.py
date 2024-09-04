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


excel_file_name = "kwatt_hydr"

df = pd.read_excel(f"{excel_file_name}.xlsx", sheet_name='Объявления')

words = [
            "насосная гидравлическая станции с электромагнитным распределителем",
            "Станция",
            "насосная станция",
            "Гайковерт",
            "Гидравлическая",
            "Электрическая", "Электрический",
            "Многофункциональный",
            "Бензогидростанция",
            "Механический",
            "Помпа",
            "Ножницы",
            "Двухступенчатый",
            "Трехпоточная",
            "гайковерт гидравлический",
            "Предохранительный",
            "Гидрозамок",
            "Арматурогиб",
            "Электроопрессовщик",
            "Опрессовщик",
            "ДОМКРАТ",
            "НАСОС",
            "съёмник гидравлический,"
            "Пневмогидравлический",
            "Инструмент",
            "Резчик",
            "Цилиндр",
            "насос гидравлический ручной односторонний",
            "Cтанция насосная",
            "Насос",
            "Съемник"
            ]

# for word in words:
# regex = r'.*(?= ' + word + r')'  # r'.*(?= Опрессовщик)',
# regex = r' \d+\s?л/мин '
# regex = r' \d{1,2}\s?т '12 т
# regex = r' \d*Нм'
# regex = r' \d{4,6} ДГ'
# regex = r' \d{5,7}\s?ДУ'
# regex = r' Д.+ HHYG-'
regex = r' Инстан ГК.*'



for i in trange(len(df)):
    # Изменение тайтла
    title = df.loc[i, 'Title'].replace('!', '').replace('  ', ' ').strip()
    if len(title) > 50:
        # try:
        #     if "ГГМК" in title:
        #         part = re.search(regex, title)[0] 
        #         # title = f'{title.replace(part, '').strip()} {part}'
        #         title = title.replace(part, ' Инстан')
        #         title = title.replace('  ', ' ').strip()
        #         print(i, part)
        # except: pass 

        if len(title) > 50:
            # фильтрация по символам
            title = '!' + title

    df.loc[i, 'Title'] = title.strip()

df.to_excel(f'{excel_file_name}.xlsx', sheet_name='Объявления', index=False)


"""
part = re.search(' \d+\s?л/мин ', title)[0]

"""