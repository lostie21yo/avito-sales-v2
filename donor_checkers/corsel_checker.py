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
from transliterate import translit

# my modules
from donor_checkers.utils.image_tools import format_image, perturb_image
from donor_checkers.utils.yandex_api import get_new_link, upload_file

def corsel_check(df, donor_link, discount, lower_price_limit, headers, yandex_image_folder_path, annex, check_new, excel_file_name, currencies):

    domain = "https://www.corsel.ru"

    for l in range(len(donor_link)):
        category_html = BS(requests.get(donor_link[l]).content, 'html.parser')
        try:
            page_number = int(category_html.find("div", {"class": "nums"}).find_all('a')[-1].text)
        except:
            page_number = 1
        print(f'Категория ({l+1}/{len(donor_link)}): {donor_link[l]}')
        new_count = 0
        for p in trange(page_number):
            page_html = BS(requests.get(f"{donor_link[l]}/?PAGEN_1={p+1}").content, 'html.parser')
            for item in page_html.find("div", {"class": "catalog_block_template"}).find_all("div", {"class": "catalog-block-view__item"}):
                
                # выявление артикула и цены не переходя на страницу продукта
                vendorCode = f"Corsel-{item.find("div", {"class": "article_block"}).text.replace("Арт.:", '').strip()}"
                try:
                    pagePrice = float(''.join(re.findall(r'\d+', item.find("span", {"class": "price_value"}).text)))
                    price = int(round(pagePrice * ((100 - discount)/100), 0))
                except:
                    price = float('nan')
                
                # фильтр по цене
                if pd.isna(price) or price < lower_price_limit or price > 2000000:
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
                        product_link = f'{domain}{item.find("div", {"class": "image_wrapper_block"}).a["href"]}'
                        product_html = BS(requests.get(product_link).content, 'html.parser')

                        # title
                        try:
                            title = product_html.find("div", {"class": "topic__heading"}).text.strip()
                        except:
                            title = 'no data'
                        
                         # categories
                        category = []
                        breadcrumbs = product_html.find("div", {"id": "navigation"}).find_all("div", {"class": "breadcrumbs__item"})
                        for bc in breadcrumbs:
                            category.append(bc.find("span", {"class": "breadcrumbs__item-name"}).text)
                        category = category[2:]
                        while len(category) < 3:
                            category.append('')

                        # brand
                        try:
                            brand = product_html.find("div", {"class": "product-info-headnote__brand"}).find("meta", {"itemprop": "name"})["content"]
                        except:
                            brand = ""
                            
                        # игнорируем бренд ironmac
                        if brand.lower() == "ironmac":
                            continue

                        # description & 
                        description = []
                        try:
                            for string in product_html.find("div", {"id": "desc"}).stripped_strings:
                                description.append(string)
                        except: pass
                        try:
                            for string in product_html.find("div", {"class": "char-side"}).stripped_strings:
                                description.append(string)
                        except: pass
                        description = '\n'.join(description)
                        description = description.replace('\n—\n', ' — ')
                        description = description.replace('\nХарактеристики\n', '\nХарактеристики:\n')
                        
                        # images
                        try:
                            imageUrls = []
                            images = product_html.find_all("div", {"class": "swiper-wrapper"})[-1].find_all("a")
                            for a in images:
                                if ('.jpg' in a["href"]) or ('.jpeg' in a["href"]) or ('.png' in a["href"]) or ('.webp' in a["href"]):
                                    imageUrls.append(f'{domain}{a["href"]}')
                                else:
                                    print(a["href"])
                                    raise 
                            imageUrls = imageUrls[0:10] # ограничение в 10 изображений
                            for i in range(len(imageUrls)):
                                url = imageUrls[i]
                                filename = f'{translit(vendorCode, language_code='ru', reversed=True)}_{i}.jpg'
                                filename = re.sub(r'/', '-', filename, flags=re.IGNORECASE)
                                filename = re.sub(r'"', '', filename, flags=re.IGNORECASE)
                                filename = re.sub(r'%', '', filename, flags=re.IGNORECASE)
                                resized_img = format_image(url)
                                cv2.imwrite(filename, resized_img)
                                perturbed_img = perturb_image(filename)
                                cv2.imwrite(filename, perturbed_img)
                                upload_file(filename, f'{yandex_image_folder_path}/{filename}', headers, True)
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
                        df.loc[new_index, 'ServiceType'] = category[2]
                        df.loc[new_index, 'Brand'] = brand
                        df.loc[new_index, 'Description'] = description
                        df.loc[new_index, 'ImageUrls'] = imageUrls
                        df.loc[new_index, 'Availability'] = "В наличии"
                        new_count += 1

                    # сохранение после каждой страницы   
                    if (new_count%25 == 0):             
                        df.to_excel(f'{excel_file_name}.xlsx', sheet_name='Объявления', index=False)
                        sleep(1)
    
    return df