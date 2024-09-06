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
from transliterate import translit

# my modules
from donor_checkers.utils.image_tools import format_image, get_ascii_url, perturb_image
from donor_checkers.utils.yandex_api import get_new_link, create_folder, upload_file

def kwatt_check(df, donor_link, discount, lower_price_limit, headers, yandex_image_folder_path, annex, check_new, excel_file_name, currencies):
    
    # выявление последней страницы
    page_number = re.search(r'page-(\d+)', donor_link).group(1)
    donor_link = donor_link.split(page_number)[0]

    new_count = 0
    for p in trange(int(page_number)):
        html = BS(requests.get(f'{donor_link}{p+1}/').content, 'html.parser')
        for product in html.find_all("div", {"class": "ty-column4"}):
       
            # выявление артикула и цены не переходя на страницу продукта
            try:
                vendorCode = "KWT-" + re.search(r'([\d\w -/]+) \(', product.find("span", {"class": "ty-control-group__item"}).text)[1]
            except:
                print('vendorcode not found')
                continue
            try:
                price = int(int(''.join(re.findall(r'\d+', product.find("span", {"class": "ty-price-num"}).text)))*((100 - 3)/100))
            except:
                price = float('nan')
                
            # фильтр по цене
            if pd.isna(price) or price < lower_price_limit:
                continue

            # обновление цены в excel-файле, если такой артикул есть
            if vendorCode in df["Id"].values:
                index = df[df['Id'] == vendorCode].index[0]
                df.loc[index, 'Price'] = price
                df.loc[index, 'Availability'] = "В наличии"
            
            # добавление новых позиций
            else:
                if check_new and (vendorCode not in df["Id"].values):
                    new_index = len(df.index)
                    try:
                        product_url = product.find("div", {"class": "ut2-gl__image"}).a['href']
                    except:
                        print('product url is shit')
                        continue
                    product_html = BS(requests.get(product_url).content, 'html.parser')

                    # title
                    try:
                        title = product_html.find("div", {"class": "ut2-pb__title"}).h1.text.strip()
                    except:
                        title = 'no data'
                    
                    # получаем категории
                    category = []
                    breadcrumb = product_html.find("div", {"class": "ty-breadcrumbs clearfix"})
                    for cat in breadcrumb.find_all("a"):
                        category.append(cat.string)
                    category = category[2:4]

                    # описание
                    description = []
                    page_description = product_html.find("div", {"id": "content_description"}).div
                    if page_description is not None:
                        for child in page_description.children:
                            if child.name == 'ul':
                                for li in child.children:
                                    if li.text != ' ':
                                        if li.text.startswith('-'):
                                            description.append('   ' + li.text)
                                        else:
                                            description.append(' - ' + li.text)
                            elif child.name == 'ol':
                                counter = 0
                                for li in child.children:
                                    if li.text != ' ':
                                        counter += 1
                                        description.append(f' {counter}. ' + li.text)
                            elif child.name == 'table':
                                try:
                                    for col in range(len(child.tbody.tr.contents)):
                                        description.append(f' - {child.tbody.contents[0].contents[col].text}: {child.tbody.contents[1].contents[col].text}')
                                except:
                                    try:
                                        for tr in child.tbody.contents:
                                            if tr != " ":
                                                description.append(f' - {tr.text.strip()}')
                                    except:
                                        for tr in child.contents:
                                            if tr != " ":
                                                description.append(f' - {tr.text.strip()}')
                            else:
                                description.append(child.text)
                
                    description = '\n\n'.join([x for x in description if x not in ('', ' ')])
                    # description.replace(r';\d+)', ';\n - ')
                    description = re.sub(r';\d+\)', ';\n - ', description)
                    description = re.sub(r':\n\n\d+\)', ':\n - ', description)
                    description = re.sub(r'\n\n ', '\n ', description)
                    description = re.sub(r';\s*  ', '\n ', description)
                    description = re.sub(r'  ', ' ', description)
                    description = re.sub(r'\n-', ' -', description)
                    description = re.sub(r'\n \n', '\n', description)
                    description = re.sub(r'\n \n', '\n', description)
                    description = re.sub(r'\n\n\n', '\n\n', description)
                    description = description.strip()   

                    # основные характеристики
                    try:
                        page_feature = product_html.find("div", {"class": "ut2-pb__first"}).find_all("span", {"class": "ty-control-group"})
                        description += '\n'
                        for feature in page_feature:
                            description = description + f'\n{feature.contents[0].text}: {feature.contents[1].text}'
                            if feature.contents[0].text == "БРЕНД":
                                brand = feature.contents[1].text
                    except: pass
                    
                    # картинки
                    try:
                        imageUrls = []
                        images = product_html.find("div", {"class": "ut2-pb__img-wrapper"}).find_all("a")
                        for a in images:
                            try:
                                if '/images/' in a["href"]:
                                    imageUrls.append(a["href"])
                            except: pass
                        imageUrls = imageUrls[0:10] # ограничение в 10 изображений
                        for i in range(len(imageUrls)):
                            url = get_ascii_url(imageUrls[i])
                            filename = f'{translit(vendorCode, language_code='ru', reversed=True)}_{i}.jpg'
                            filename = re.sub(r'/', '-', filename, flags=re.IGNORECASE)
                            filename = re.sub(r'%', '', filename, flags=re.IGNORECASE)
                            resized_img = format_image(url)
                            cv2.imwrite(filename, resized_img)
                            perturbed_img = perturb_image(filename)
                            cv2.imwrite(filename, perturbed_img)
                            upload_file(filename, f'{yandex_image_folder_path}/{filename}', headers, True)
                            sleep(1)
                            os.remove(filename) 
                            imageUrls[i] = get_new_link(filename, yandex_image_folder_path)
                        imageUrls = " | ".join(imageUrls)
                    except Exception as e:
                        imageUrls = "no data"

                    # writing
                    df.loc[new_index, 'Id'] = vendorCode
                    df.loc[new_index, 'Price'] = price
                    df.loc[new_index, 'Title'] = title
                    df.loc[new_index, 'Category'] = category[0]
                    df.loc[new_index, 'GoodsType'] = category[1]
                    df.loc[new_index, 'Brand'] = brand
                    df.loc[new_index, 'Description'] = description
                    df.loc[new_index, 'ImageUrls'] = imageUrls
                    df.loc[new_index, 'Availability'] = "В наличии"
                    new_count += 1

                # периодический сейв
                if (new_count%25 == 0):
                    df.to_excel(f'{excel_file_name}.xlsx', sheet_name='Объявления', index=False)
                    sleep(1)
        
    return df
    