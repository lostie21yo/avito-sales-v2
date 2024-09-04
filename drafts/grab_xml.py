import os
import sys
import re
import cv2
import time
import requests
import pandas as pd
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup as BS
from tqdm import tqdm
from PIL import Image
from urllib.request import urlopen

# my modules
from format_image import format_image
from yandex_api import get_new_link, create_folder

link = "https://www.mkslift.ru/export_xml.php?key=176ec86554e7edcec3dd5ef05dd58d9d"
file_name = "Выгрузка Промторг.xlsx"
xml_response = requests.get(link)
root = ET.fromstring(xml_response.text)

# открываем xlsx файл 
df = pd.read_excel(f"output/{file_name}", sheet_name='Объявления')

# загрузка категорий
categoryDict = {}
for category in root.find('shop').find('categories').findall('category'):
    categoryID = category.attrib['id']
    categoryDict[categoryID] = category.text

# приставка снизу
annex = "<p><br/></p> <p><strong>✅✅✅✅✅ Гарантия 12 месяцев! 💫💫💫💫💫</strong></p> <p><strong>🚕🚕🚕🚕🚕 Оперативная Доставка по России Транспортными компаниями 🚛🚛🚛 Доставляем по СПб за 1 час! 🚁🚁🚁🚁🚁</strong></p> <p><strong>🔥🔥🔥🔥🔥 Добавляйте объявление в избранное что бы не потерять  🔥🔥🔥🔥🔥</strong></p> <p><strong>🔫🔨🔧 Оперативный гарантийный сервис! 🔫🔨🔧</strong></p> <p><strong>📲📲📲 Обращайтесь за помощью в сообщениях или по телефону, всегда на связи! 📞📞📞</strong></p>"


# для работы с Yandex.Диском
URL = 'https://cloud-api.yandex.net/v1/disk/resources'
TOKEN = 'y0_AgAAAAB2eAMkAAvtEgAAAAEHDYscAAAO0qWJlTtHEYrzMF1eVgrRvisOSQ'
headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': f'OAuth {TOKEN}'}
yandex_image_folder_path = 'Main pictures'
create_folder(yandex_image_folder_path)
# res = requests.get(f'{URL}/public', headers=headers).json()
# print(res)

count = 0
offer_list = root.find('shop').find('offers').findall('offer')

for elem in tqdm(offer_list[:]):
    # if elem.attrib["id"] != "14208":
    #     continue

    new_index = len(df.index)

    # url
    page_url = elem.find('url').text

    # артикул
    vendorCode = elem.find('vendorCode').text

    # категории ID
    categoryID = elem.find('categoryId').text
    try:
        categoryIDtext = categoryDict[categoryID]
    except:
        categoryIDtext = ""

    # получаем и формируем title
    vendor = elem.find('vendor').text  
    title = f"{elem.find('name').text.split(vendor)[-1].split(vendorCode)[-1].strip()} {vendorCode} {vendor}"
    
    # цена
    try:
        price = round(float(elem.find('price').text)*0.95, 0)
    except:
        price = -1

    # наличие
    isAvailable = ""
    if elem.attrib['available'] == "true":
        isAvailable = "В наличии"
    if elem.attrib['available'] == "false":
        isAvailable = "Нет в наличии"

    # описание и категория
    category = ""
    params = []
    for param in elem.findall('param'):
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

        # обновление param категории
        if name == "Категория":
            category = param.text

    params = '\n'.join(params)
    if elem.find('description_long').text is not None:
        description_long = []
        for sentence in elem.find('description_long').text.split('.'):
            sentence = re.sub(" +", " ", sentence)
            sentence = re.sub("\n+", "\n", sentence)
            sentence = re.sub("\n ", "\n", sentence)
            description_long.append(sentence.strip())
        description_long = '\n'.join(description_long)
        description = f"{description_long}\n{params}\n\n{annex}"
    else:
        description = f"{params}\n{annex}"
    # print(description)
    
    # images urls
    imageUrls = []
    if elem.find('picture') is not None:
        origURL = elem.find('picture').text
        origURL = origURL.replace("http://www.mkslift.ruhttp://www.mkslift.ru", "http://www.mkslift.ru")
        filename = origURL.split('/')[-1]
        # resized_img = format_image(origURL)
        # cv2.imwrite(filename, resized_img)
        # upload_file(filename, f'{y_folder}/{filename}')
        # os.remove(filename)
        new_URL = get_new_link(filename, yandex_image_folder_path)
        imageUrls.append(new_URL) # главная картинка в формате 4:3

    if elem.find('images') is not None:
        for image in elem.find('images').findall('image'):
            imageUrls.append(image.text) # дополнительные картинки
    imageUrls = " | ".join(imageUrls)

    # video url
    page_url_response = requests.get(page_url)
    html = BS(page_url_response.content, 'html.parser')
    try:
        frame = html.find_all('iframe')[0]
        videoUrl = frame.get('src').split('embed/')
        videoUrl = videoUrl[0] + 'watch?v=' + videoUrl[1].split("?")[0]
    except:
        videoUrl = ""

    # добавление с фильтрацией
    if float(price) < 0 or float(price) > 3000:
        df.loc[new_index, 'paramCategory'] = category
        df.loc[new_index, 'categoryIDtext'] = categoryIDtext
        df.loc[new_index, 'Id'] = vendorCode
        df.loc[new_index, 'Title'] = title
        df.loc[new_index, 'Price'] = price
        df.loc[new_index, 'Availability'] = isAvailable
        df.loc[new_index, 'Description'] = description
        df.loc[new_index, 'ImageUrls'] = imageUrls
        df.loc[new_index, 'VideoUrl'] = videoUrl
        # категории
        # df.loc[new_index, 'categoryIDtext'] = categoryIDtext

        count += 1

    df.to_excel(f'output/{file_name}', sheet_name='Объявления', index=False)

print(f"Добавлено строк: {count}/{len(offer_list)}")
before_drop_count = len(df)
df = df.drop_duplicates(subset=["Id"], keep='last')
print(f"Из них {before_drop_count - len(df)} дупликаты (удалены)")
df.to_excel(f'output/{file_name}', sheet_name='Объявления', index=False)
