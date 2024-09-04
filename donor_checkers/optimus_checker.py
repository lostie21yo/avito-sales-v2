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

# my modules
from donor_checkers.utils.image_tools import format_image
from donor_checkers.utils.yandex_api import get_new_link, create_folder, upload_file

def optimus_check(df, donor_link, discount, headers, yandex_image_folder_path, annex, check_new, excel_file_name, currencies):

    # парсинг прайса wdk/opt
    price_df = pd.read_excel(f"sources/Optimus price.xlsx", sheet_name='OPT price')

    domain = "https://optimus.su"

    # добавление новых позиций
    if check_new:
        print(f'Проверка наличия новых позиций и их добавление:')
        page = requests.get(f"{donor_link}/")
        html = BS(page.content, 'html.parser')
        for category_div in tqdm(html.find("div", {"class": "catalog_section_list row items flexbox"}).children):
            if category_div != '\n':
                links = category_div.find_all("li", {"class": "sect"})
                for link in links:
                    link = domain + link.a['href']
                    category_page = requests.get(link)
                    category_html = BS(category_page.content, 'html.parser')
                    for product_div in category_html.find("div", {"class": "catalog_block"}).children:
                        if product_div != '\n':

                            new_index = len(df.index)

                            # страница продукта
                            product_link = domain + product_div.a['href']
                            product_page = requests.get(product_link)
                            product_html = BS(product_page.content, 'html.parser')

                            # цена
                            # price = float(''.join(re.findall(r'\d+', product_html.find("bdi").text)))

                            # артикул
                            try:
                                vendorCodeDiv = product_html.find("div", {"class": "article iblock"})
                                vendorCode = vendorCodeDiv.find("span", {"class": "value"}).text
                            except:
                                vendorCode = "no data"
                            if vendorCode not in df["Id"].values:
                                # title
                                title = product_html.find("h1", {"id": "pagetitle"}).text
                                
                                # получаем категории
                                category = []
                                for cat in product_html.find("div", {"class": "breadcrumbs"}).strings:
                                    if cat != '-':
                                        category.append(cat)
                                category = category[2:-1]
                                while len(category) < 3:
                                    category.append('')
                                # category = ' | '.join(category[1:-1])

                                # описание 
                                description = []
                                try:
                                    for string in product_html.find("div", {"class": "detail_text"}).stripped_strings:
                                        description.append(string)
                                except:
                                    pass
                                try:
                                    additional_info = product_html.find("table", {"class": "props_list nbg"}).children
                                    for line in additional_info:
                                        string = line.get_text().strip().replace("\t", "").replace("\n", " ")
                                        description.append(string)
                                except:
                                    pass
                                description = '\n'.join(description).replace("\n\n", "\n")
                                description = f"{title}\n{description}\n{annex}"

                                # картинки
                                imageUrls = []
                                try:
                                    imagesDiv = product_html.find("div", {"class": "slides"})
                                    links = imagesDiv.find_all("a", {"data-fancybox-group": "item_slider"})
                                    for a in links:
                                        imageUrls.append(domain + a["href"])
                                    
                                    origURL = imageUrls[0]
                                    filename = origURL.split('/')[-1]
                                    resized_img = format_image(origURL)
                                    cv2.imwrite(filename, resized_img)
                                    upload_file(filename, f'{yandex_image_folder_path}/{filename}', headers, True)
                                    os.remove(filename)
                                    new_URL = get_new_link(filename, yandex_image_folder_path)
                                    imageUrls[0] = new_URL # главная картинка в формате 4:3
                                    imageUrls = " | ".join(imageUrls)
                                except:
                                    imageUrls = 'no data'

                                # запись
                                new_count += 1
                                df.loc[new_index, 'Id'] = vendorCode
                                df.loc[new_index, 'Title'] = title
                                # df.loc[new_index, 'Price'] = price
                                df.loc[new_index, 'Category'] = category[0]
                                df.loc[new_index, 'GoodsType'] = category[1]
                                df.loc[new_index, 'ProductType'] = category[2]
                                df.loc[new_index, 'Description'] = description
                                df.loc[new_index, 'ImageUrls'] = imageUrls
                                # периодический сейв
                                if (new_count%50 == 0):
                                    df.to_excel(f'{excel_file_name}.xlsx', sheet_name='Объявления', index=False)
                                    sleep(1)
    
    old_count = 0
    # Обновление существующих позиций в выгрузке
    print("Обновление существующих позиций:")
    for i in trange(len(df)):
        vendorCode = df.loc[i, 'Id'].split('/')[0]
        for j in range(len(price_df)):
            if vendorCode == price_df.loc[j, 'Id']:
                price = price_df.loc[j, 'Price']
                valute = price_df.loc[j, 'Unit']
                
                # цена
                if valute != "RUB":
                    course = currencies['Valute'][valute]['Value']
                else:
                    course = 1
                price = round(price * ((100 - discount)/100) * float(course), 0)

                # Наличие
                if float(df.loc[i, 'Price']) > 8000:
                    availability = "В наличии"
                else:
                    availability = "Нет в наличии"

                # description = f"{df.loc[i, 'Title']}\n{df.loc[i, 'Description']}\n{annex}"

                # title = (f'{df.loc[i, 'Title'].split(vendorCode)[1]} {vendorCode}').strip()
                # title = df.loc[i, 'Title'].strip()

                # запись
                old_count += 1
                # df.loc[i, 'Description'] = description
                # df.loc[i, 'Title'] = title
                df.loc[i, 'Availability'] = availability
                df.loc[i, 'Price'] = price
                price_df.loc[j, 'Status'] = "OK"
                break

        
    # обработка перед финальным сохранением и сохранение
    df = df.drop_duplicates(subset=["Id"], keep='first')
    price_df.to_excel(f'sources/Optimus price.xlsx', sheet_name='OPT price', index=False)

    return df
    