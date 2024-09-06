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

# my modules
from donor_checkers.utils.image_tools import format_image
from donor_checkers.utils.yandex_api import get_new_link, create_folder, upload_file

def garopt_check(df, donor_link, discount, lower_price_limit, headers, yandex_image_folder_path, annex, check_new, excel_file_name, currencies):

    annex = annex.split("\nТЕЛО ОПИСАНИЯ\n")

    for l in range(len(donor_link)):
        # парсим xml донора
        print(f'Категория ({l+1}/{len(donor_link)}): {donor_link[l]}')
        xml_response = requests.get(donor_link[l])
        root = ET.fromstring(xml_response.text)
        offer_list = root.find('shop').find('offers').findall('offer')

        new_count = 0
        # добавление новых позиций
        if check_new:
            # загрузка категорий
            categoryDict = {}
            for category in root.find('shop').find('categories').findall('category'):
                categoryID = category.attrib['id']
                categoryDict[categoryID] = category.text
                
            print(f'Проверка наличия новых позиций и их добавление:')
            for offer in tqdm(offer_list[:]):
                # vendorCode
                vendorCode = offer.find('vendorCode').text
                if vendorCode not in df["Id"].values:
                    new_index = len(df.index)
                    
                    # price
                    try:
                        valute = offer.find('currencyId').text
                        if valute != "RUB":
                            course = currencies['Valute'][valute]['Value']
                        else:
                            course = 1
                        price = round(float(offer.find('price').text)*((100 - discount)/100) * float(course), 0) 

                    except:
                        price = -1

                    # фильтр по цене
                    if pd.isna(price) or price < lower_price_limit:
                        continue
                    
                    # title
                    title = offer.find('name').text

                    # category
                    categoryID = offer.find('categoryId').text
                    try:
                        category = categoryDict[categoryID]
                    except:
                        category = ""

                    # main Photo + dop
                    imageUrls = []
                    pictures = offer.findall('picture')
                    try:
                        for p in range(len(pictures)):
                            if p == 0:
                                origURL = pictures[p].text
                                print(origURL)
                                filename = origURL.split('/')[-1]
                                resized_img = format_image(origURL)
                                cv2.imwrite(filename, resized_img)
                                upload_file(filename, f'{yandex_image_folder_path}/{filename}', headers, True)
                                os.remove(filename)
                                new_URL = get_new_link(filename, yandex_image_folder_path)
                                imageUrls.append(new_URL) # главная картинка в формате 4:3
                            else:
                                imageUrls.append(pictures[p].text)
                    except:
                        imageUrls.append("no data") 
                    finally:
                        imageUrls = " | ".join(imageUrls)

                    title = offer.find('name').text
                    if offer.find('description') is not None:
                        description = f"{title}\n{annex[0]}{offer.find('description').text}\n{annex[1]}"
                    else:
                        description = f"{title}\n{annex[0]}\n{annex[1]}"

                    # запись
                    new_count += 1
                    df.loc[new_index, 'Id'] = vendorCode
                    df.loc[new_index, 'Title'] = title
                    df.loc[new_index, 'Price'] = price
                    df.loc[new_index, 'Category'] = category
                    df.loc[new_index, 'Description'] = description
                    df.loc[new_index, 'ImageUrls'] = imageUrls
                    df.loc[new_index, 'Availability'] = "В наличии"
                    # периодический сейв
                    if (new_count%25 == 0 or new_count == len(offer_list)):
                        df.to_excel(f'{excel_file_name}.xlsx', sheet_name='Объявления', index=False)

        # Обновление существующих позиций в выгрузке
        print("Обновление существующих позиций:")
        for i in trange(len(df)):
            vendorCode = df.loc[i, 'Id']
            for offer in offer_list[:]:
                donor_id = f'{offer.find("vendorCode").text}'
                if vendorCode == donor_id:
                    # цена
                    try:
                        valute = offer.find('currencyId').text
                        if valute != "RUB":
                            course = currencies['Valute'][valute]['Value']
                        else:
                            course = 1
                        price = round(float(offer.find('price').text)*((100 - discount)/100) * float(course), 0)
                    except:
                        continue

                    # запись
                    df.loc[i, 'Price'] = price
                    break

    return df
