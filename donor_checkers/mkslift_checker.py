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

def mkslift_check(df, donor_link, discount, headers, yandex_image_folder_path, annex, check_new, excel_file_name, currencies):

    # парсим xml донора
    xml_response = requests.get(donor_link)
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
                    if valute != "RUR":
                        course = currencies['Valute'][valute]['Value']
                    else:
                        course = 1
                    price = round(float(offer.find('price').text)*((100 - discount)/100) * float(course), 0) 
                    if float(price) < 3000:
                        continue
                except:
                    price = -1
                
                # title
                vendor = offer.find('vendor').text  
                title = f"{offer.find('name').text.split(vendor)[-1].split(vendorCode)[-1].strip()} {vendorCode} {vendor}"

                # category
                try:
                    categoryID = offer.find('categoryId').text
                    category = categoryDict[categoryID]
                except:
                    category = ""

                # описание и категория
                params = []
                for param in offer.findall('param'):
                    # if param.attrib['name'] != 'articul':
                    pattern = "(?<=&gt;)(.*)(?=&lt;)|(?<=;'>)(.*)(?=</span>)"
                    name = param.attrib['name']
                    # извлечение значения 
                    if "span" in param.text:
                        value = re.search(pattern, param.text)[0]
                    elif param.text == "":
                        value = ""
                    else:
                        value = param.text
                    # извлечение unit'а
                    unit = ""
                    if 'unit' in param.attrib:
                        if "span" in param.attrib['unit']:
                            unit = re.search(pattern, param.attrib['unit'])[0]
                        elif param.text == "":
                            unit = ""
                        else:
                            unit = param.attrib['unit']
                    params.append(f'{name}   {value} {unit}')
                
                params = '\n'.join(params)
                if offer.find('description_long').text is not None:
                    description_long = []
                    for sentence in offer.find('description_long').text.split('.'):
                        sentence = re.sub(" +", " ", sentence)
                        sentence = re.sub("\n+", "\n", sentence)
                        sentence = re.sub("\n ", "\n", sentence)
                        description_long.append(sentence.strip())
                    description_long = '\n'.join(description_long)
                    description = f"{title}\n{description_long}\n{params}\n\n{annex}"
                else:
                    description = f"{title}\n{params}\n{annex}"

                # main Photo + dop
                imageUrls = []
                if offer.find('picture') is not None:
                    origURL = offer.find('picture').text
                    origURL = origURL.replace("http://www.mkslift.ruhttp://www.mkslift.ru", "http://www.mkslift.ru")
                    filename = origURL.split('/')[-1]
                    resized_img = format_image(origURL)
                    cv2.imwrite(filename, resized_img)
                    upload_file(filename, f'{yandex_image_folder_path}/{filename}', headers, True)
                    os.remove(filename)
                    new_URL = get_new_link(filename, yandex_image_folder_path)
                    imageUrls.append(new_URL) # главная картинка в формате 4:3

                if offer.find('images') is not None:
                    for image in offer.find('images').findall('image'):
                        imageUrls.append(image.text) # дополнительные картинки
                imageUrls = " | ".join(imageUrls)

                # video url
                page_url = offer.find('url').text
                page_url_response = requests.get(page_url)
                html = BS(page_url_response.content, 'html.parser')
                try:
                    frame = html.find_all('iframe')[0]
                    videoUrl = frame.get('src').split('embed/')
                    videoUrl = videoUrl[0] + 'watch?v=' + videoUrl[1].split("?")[0]
                except:
                    videoUrl = ""

                # запись
                df.loc[new_index, 'Id'] = vendorCode
                df.loc[new_index, 'Title'] = title
                df.loc[new_index, 'Price'] = price
                df.loc[new_index, 'Category'] = category
                df.loc[new_index, 'Description'] = description
                df.loc[new_index, 'ImageUrls'] = imageUrls
                df.loc[new_index, 'VideoUrl'] = videoUrl
                new_count += 1
                # периодический сейв
                if (new_count%50 == 0 or new_count == len(offer_list)):
                    # df['DateEnd'] = pd.to_datetime(df['DateEnd']).dt.date
                    df = df.drop_duplicates(subset=["Id"], keep='last')
                    df.to_excel(f'{excel_file_name}.xlsx', sheet_name='Объявления', index=False)

    # обновление существующих позиций
    old_count = 0
    print("Обновление существующих позиций:")
    for i in trange(len(df)):
        vendorCode = df.loc[i, 'Id']
        # dateend = change_dateend(str(df.loc[i, 'Availability']), str(df.loc[i, 'AvitoStatus']), yesterday)
        for offer in offer_list[:]:
            if vendorCode == offer.find('vendorCode').text: 
                # index = df[df['Id'] == offerVendorCode].index[0]
                # vendorCode = df.loc[index, 'Id']
                # цена
                try:
                    price = round(float(offer.find('price').text)*((100 - discount)/100), 0)
                except:
                    continue

                if float(price) > 8000: 
                    # наличие
                    if offer.attrib['available'] == "true":
                        availability = "В наличии"
                    if offer.attrib['available'] == "false":
                        availability = "Нет в наличии"
                else: # делаем позиции неактивными с ценой меньше 3к
                    availability = "Нет в наличии"

                # запись
                df.loc[i, 'Price'] = price
                df.loc[i, 'Availability'] = availability
                old_count += 1
                break

    # обработка перед финальным сохранением и сохранение
    df = df.drop_duplicates(subset=["Id"], keep='first')
    
    return df