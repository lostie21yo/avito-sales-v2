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

def ironmac_check(df, donor_link, discount, headers, yandex_image_folder_path, annex, check_new, excel_file_name, currencies):
    
    # парсим csv донора
    donor_df = pd.read_csv(donor_link, sep=';', index_col=False)

    new_count = 0
    # добавление новых позиций
    if check_new:
        print(f'Проверка наличия новых позиций и их добавление:')
        for i in trange(len(donor_df)):
            # vendorCode
            vendorCode = f'ironmac-{donor_df["id"][i]}'
            if vendorCode not in df["Id"].values:
                # print(vendorCode)
                new_index = len(df.index)
                
                # price БЕЗ ЦЕНЫ ТОЖЕ ВЫГРУЗИТЬ
                if not pd.isna(donor_df['Цена'][i]):
                    valute = donor_df['Валюта'][i]
                    if valute != "RUB":
                        course = currencies['Valute'][valute]['Value']
                    else:
                        course = 1
                    price = round(float(donor_df['Цена'][i])*((100 - discount)/100) * float(course), 0)
                    if float(price) < 3000:
                        continue
                else:
                    price = -1
                
                # title
                title = f'{donor_df["Наименование"][i]}'

                # category
                category = f'{donor_df["Раздел"][i]}'

                # main Photo + dop
                imageUrls = []
                if  donor_df['Фото'][i] is not None:
                    # if i == 0:
                    #     origURL = "https://ironmac-kompressor.com/local/templates/ironmac/img/content/product.jpg"
                    # else:
                    origURL = donor_df['Фото'][i]
                    # origURL = origURL.replace("http://www.mkslift.ruhttp://www.mkslift.ru", "http://www.mkslift.ru")
                    filename = origURL.split('/')[-1]
                    resized_img = format_image(origURL)
                    cv2.imwrite(filename, resized_img)
                    upload_file(filename, f'{yandex_image_folder_path}/{filename}', headers, True)
                    os.remove(filename)
                    new_URL = get_new_link(filename, yandex_image_folder_path)
                    imageUrls.append(new_URL) # главная картинка в формате 4:3
                
                images = ""
                try:
                    images = donor_df['Фото доп'][i].split(',')
                    for image in images:
                        imageUrls.append(image.strip()) # дополнительные картинки
                except:
                    pass
                imageUrls = " | ".join(imageUrls)

                # description
                specifications = []
                if not pd.isna(donor_df['Анонс'][i]):
                    html_table = BS(donor_df['Анонс'][i], 'html.parser')
                    rows = html_table.find_all("tr")
                    for tr in rows:
                        cols = tr.find_all("td")
                        if len(cols) == 2:
                            line = []
                            for col in cols:
                                line.append(col.text.strip())
                            line = ': '.join(line)
                            specifications.append(line)
                    specifications = '\n'.join(specifications) + '\n\n'
                else:
                    specifications = ''

                description = f"{df.loc[i, 'Title']}\n\n{specifications}{donor_df['Описание'][i]}\n\n{annex}"

                # запись
                new_count += 1
                df.loc[new_index, 'Id'] = vendorCode
                df.loc[new_index, 'Title'] = title
                df.loc[new_index, 'Price'] = price
                df.loc[new_index, 'Category'] = category
                df.loc[new_index, 'Description'] = description
                df.loc[new_index, 'ImageUrls'] = imageUrls
                # периодический сейв
                if i!=0 and i%50 == 0:
                    df = df.drop_duplicates(subset=["Id"], keep='last')
                    df.to_excel(f'{excel_file_name}.xlsx', sheet_name='Объявления', index=False)

    old_count = 0
    # Обновление существующих позиций в выгрузке
    print('Обновление существующих позиций:')
    for i in trange(len(df)):
        vendorCode = df.loc[i, 'Id']
        # dateend = change_dateend(str(df.loc[i, 'Availability']), str(df.loc[i, 'AvitoStatus']), yesterday)
        for j in range(len(donor_df)):
            donor_id = f'ironmac-{donor_df["id"][j]}'
            if vendorCode == donor_id:
                # цена
                try:
                    valute = donor_df['Валюта'][j]
                    if valute != "RUB":
                        course = currencies['Valute'][valute]['Value']
                    else:
                        course = 1
                    price = round(float(donor_df['Цена'][j])*((100 - discount)/100) * float(course), 0)
                except:
                    continue

                # # main Photo + dop
                # imageUrls = []
                # try:
                #     if  donor_df['Фото'][j] is not None:
                #         # if i == 0:
                #         #     origURL = "https://ironmac-kompressor.com/local/templates/ironmac/img/content/product.jpg"
                #         # else:
                #         origURL = donor_df['Фото'][j]
                #         # origURL = origURL.replace("http://www.mkslift.ruhttp://www.mkslift.ru", "http://www.mkslift.ru")
                #         filename = origURL.split('/')[-1]
                #         resized_img = format_image(origURL)
                #         cv2.imwrite(filename, resized_img)
                #         upload_file(filename, f'{yandex_image_folder_path}/{filename}', headers, True)
                #         os.remove(filename)
                #         new_URL = get_new_link(filename, yandex_image_folder_path)
                #         imageUrls.append(new_URL) # главная картинка в формате 4:3
                # except:
                #     print(f'{donor_id} image broken')
                
                # images = ""
                # try:
                #     images = donor_df['Фото доп'][j].split(',')
                #     for image in images:
                #         imageUrls.append(image.strip()) # дополнительные картинки
                # except:
                #     pass
                # imageUrls = " | ".join(imageUrls)

                # df.loc[i, 'ImageUrls'] = imageUrls


                # if float(price) < 0 or float(price) > 3000: 
                #     # наличие
                #     if donor_df['Статус'][j] == "В наличии":
                #         availability = "В наличии"
                #     else:
                #         availability = "Нет в наличии"
                # else: # делаем позиции неактивными с ценой меньше 3к
                #     availability = "Нет в наличии"
                availability = "В наличии"

                # запись
                df.loc[i, 'Price'] = price
                df.loc[i, 'Availability'] = availability
                
                old_count += 1 
                break


    # обработка перед финальным сохранением и сохранение
    df = df.drop_duplicates(subset=["Id"], keep='first')
    
    return df
