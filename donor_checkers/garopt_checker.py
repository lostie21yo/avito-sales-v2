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

def garopt_check(df, donor_link, discount, headers, yandex_image_folder_path, annex, check_new, excel_file_name, currencies):

    # парсим xml донора
    xml_response = requests.get(donor_link)
    root = ET.fromstring(xml_response.text)
    offer_list = root.find('shop').find('offers').findall('offer')

    annex = annex.split("\nТЕЛО ОПИСАНИЯ\n")

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
                    if float(price) < 3000:
                        continue
                except:
                    price = -1
                
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
                    imageUrls.append('invalid link') 
                finally:
                    imageUrls = " | ".join(imageUrls)

                # description
                # if not pd.isna(donor_df['Описание'][i]):
                #     description_long = []
                #     for sentence in elem.find('description_long').text.split('.'):
                #         sentence = re.sub(" +", " ", sentence)
                #         sentence = re.sub("\n+", "\n", sentence)
                #         sentence = re.sub("\n ", "\n", sentence)
                #         description_long.append(sentence.strip())
                #     description_long = '\n'.join(description_long)
                #     description = f"{description_long}\n{params}\n\n{annex}"
                # else:
                title = offer.find('name').text
                if offer.find('description') is not None:
                    description = f"{title}\n{annex[0]}{offer.find('description').text}\n{annex[1]}"
                else:
                    description = f"{title}\n{annex[0]}\n{annex[1]}"

                # наличие
                availability = "В наличии"

                # запись
                new_count += 1
                df.loc[new_index, 'Id'] = vendorCode
                df.loc[new_index, 'Title'] = title
                df.loc[new_index, 'Price'] = price
                df.loc[new_index, 'Category'] = category
                df.loc[new_index, 'Description'] = description
                df.loc[new_index, 'ImageUrls'] = imageUrls
                df.loc[new_index, 'Availability'] = availability
                # периодический сейв
                if (new_count%50 == 0 or new_count == len(offer_list)):
                    # df['DateEnd'] = pd.to_datetime(df['DateEnd']).dt.date
                    df = df.drop_duplicates(subset=["Id"], keep='last')
                    df.to_excel(f'{excel_file_name}.xlsx', sheet_name='Объявления', index=False)

    old_count = 0
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
                    
                # # desc temporary
                # title = offer.find('name').text
                # if offer.find('description') is not None:
                #     description = f"{title}\n{annex[0]}\n{offer.find('description').text}\n{annex[1]}"
                # else:
                #     description = f"{title}\n{annex[0]}\n{annex[1]}"

                # наличие
                # if float(price) < 0 or float(price) > 3000: 
                #     if offer.attrib['available'] == "true":
                #         availability = "В наличии"
                #     if offer.attrib['available'] == "false":
                #         availability = "Нет в наличии"
                # else: # делаем позиции неактивными с ценой меньше 3к
                #     availability = "Нет в наличии"

                # запись
                df.loc[i, 'Price'] = price
                # df.loc[i, 'Description'] = description
                # df.loc[i, 'Availability'] = availability
                old_count += 1
                break
            
    # обработка перед финальным сохранением и сохранение
    df = df.drop_duplicates(subset=["Id"], keep='first')

    return df
