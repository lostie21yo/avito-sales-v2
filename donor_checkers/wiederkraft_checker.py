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

def wiederkraft_check(df, donor_link, discount, lower_price_limit, headers, yandex_image_folder_path, annex, check_new, excel_file_name, currencies):
    
    # парсинг прайса wdk/opt
    price_df = pd.read_excel(f"sources/Wiederkraft price.xlsx", sheet_name='WDK price')

    # выявление последней страницы
    first_page = requests.get(f"{donor_link}/{1}/")
    html = BS(first_page.content, 'html.parser')
    max_page_number = 0
    for product in html.find_all("a", {"class": "page-numbers"}):
        if product.text.isdigit() and int(product.text) > max_page_number:
            max_page_number = int(product.text)

    new_count = 0

    # добавление новых позиций
    if check_new:
        print(f'Проверка наличия новых позиций и их добавление:')
        for i in trange(max_page_number):
            page = requests.get(f"{donor_link}/{i+1}/")
            html = BS(page.content, 'html.parser')
            try:
                for product in html.find("ul", {"class": "products"}).children:
                    if product != '\n':
                        new_index = len(df.index)

                        # страница продукта
                        product_page = requests.get(product.a['href'])
                        product_html = BS(product_page.content, 'html.parser')
                        
                        # цена
                        price = float(''.join(re.findall(r'\d+', product_html.find("bdi").text)))
                       
                        # фильтр по цене
                        if pd.isna(price) or price < lower_price_limit:
                            continue

                        # артикул
                        try:
                            vendorCode = product_html.find("span", {"class": "sku"}).text
                        except:
                            vendorCode = "no data"
                        if vendorCode not in df["Id"].values:

                            # title
                            title = product_html.find("h1", {"class": "product_title entry-title"}).text
                            
                            # получаем категории
                            category = []
                            for cat in product_html.find("nav", {"class": "woocommerce-breadcrumb"}).children:
                                category.append(cat.string)
                            category = category[1:-1]
                            while len(category) < 3:
                                category.append('')
                            # category = ' | '.join(category[1:-1])

                            # описание 
                            description = []
                            page_description = product_html.find("div", {"id": "tab-description"}).stripped_strings
                            for string in page_description:
                                description.append(string)
                            try:
                                additional_info = product_html.find("div", {"id": "tab-additional_information"}).table.children
                                for line in additional_info:
                                    string = line.get_text().strip().replace("\n", " ")
                                    description.append(string)
                            except:
                                pass
                            description = '\n'.join(description).replace("\n\n", "\n")
                            description = f"{title}\n{description}\n{annex}"

                            # картинки
                            imageUrls = []
                            try:
                                images = product_html.find("figure", {"class": "woocommerce-product-gallery__wrapper swiper-wrapper"}).find_all("div")
                                for div in images:
                                    imageUrls.append(div.a["href"])
                                
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
                            df.loc[new_index, 'Price'] = price
                            df.loc[new_index, 'Category'] = category[0]
                            df.loc[new_index, 'GoodsType'] = category[1]
                            df.loc[new_index, 'ProductType'] = category[2]
                            df.loc[new_index, 'Description'] = description
                            df.loc[new_index, 'ImageUrls'] = imageUrls

                            # периодический сейв
                            if (new_count%50 == 0):
                                df.to_excel(f'{excel_file_name}.xlsx', sheet_name='Объявления', index=False)
                                sleep(1)
                            
            except Exception as e:
                print(e)
                break

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

                # запись
                old_count += 1
                # df.loc[i, 'Description'] = description
                df.loc[i, 'Availability'] = availability
                df.loc[i, 'Price'] = price
                price_df.loc[j, 'Status'] = "OK"
                
                break

    # обработка перед финальным сохранением и сохранение
    price_df.to_excel(f'sources/Wiederkraft price.xlsx', sheet_name='WDK price', index=False)

    return df
    