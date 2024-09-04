import cv2
from urllib.parse import quote, urlsplit, urlunsplit
from urllib.request import urlopen
import numpy as np
import os
from skimage.util import random_noise

def get_ascii_url(url: str) -> str:
    url = list(urlsplit(url))
    url[2] = quote(url[2])
    return urlunsplit(url)

def perturb_image(filename):
    img = cv2.imread(filename)
    #  Gaussian noise adding
    noised_img = random_noise(img, mode="gaussian")
    noised_img = np.array(255*noised_img)
    return noised_img

def format_image(link, target_size = (1280, 960)):
    # link = get_ascii_url(link)
    req = urlopen(link)
    arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
    img = cv2.imdecode(arr, -1) # 'Load it as it is'
    h, w = img.shape[:2]

    coef1 = target_size[0]/w
    coef2 = target_size[1]/h

    if coef1 < coef2:
        new_w, new_h = target_size[0], round(h*coef1)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
        line_height = round((target_size[1] - new_h)/2)
        nul = np.full((line_height, new_w, 3), 255)
        img = np.vstack((nul, img))
        img = np.vstack((img, nul))
    else:
        new_w, new_h = round(w*coef2), target_size[1]
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
        line_width = round((target_size[0] - new_w)/2)
        nul = np.full((new_h, line_width, 3), 255)
        img = np.hstack((nul, img))
        img = np.hstack((img, nul))

    return img 



# origURL = "https://www.corsel.ru/upload/iblock/1bc/fpc5z76mvos3mw3sh67dib5nzh314yj7.jpg"
# # origURL = get_ascii_url(origURL)
# filename = origURL.split('/')[-1].split('.')[0] + '.jpg'
# resized_img = format_image(origURL)
# cv2.imwrite(filename, resized_img)

# perturbed_img = perturb_image(filename)
# cv2.imwrite('noised ' + filename, perturbed_img)