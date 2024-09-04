import json
from datetime import *
import requests
import sys
import pandas as pd

# my modules
from donor_checkers.mkslift_checker import mkslift_check
from donor_checkers.ironmac_checker import ironmac_check
from donor_checkers.garopt_checker import garopt_check
from donor_checkers.wiederkraft_checker import wiederkraft_check
from donor_checkers.optimus_checker import optimus_check
from donor_checkers.kwatt_checker import kwatt_check
from donor_checkers.corsel_checker import corsel_check
from donor_checkers.utils.yandex_api import upload_file, download_file, get_new_link, create_folder
from donor_checkers.utils.change_dateend import change_dateend
from donor_checkers.utils.donor_launcher import launch

# инициализация
launch_date = datetime.now().date()
bot_token = "7227476930:AAHz9Aldcx4G2cTiyyZsEfkpyUirNeSffqY"
chat_ids = ["904798847"] 
# chat_ids.append("546496045") # - иван
message = f"Произведена инициализация проверки доноров {launch_date}."
print(f'{message}')
yesterday = (datetime.now() - timedelta(days=1)).date().strftime("%Y-%m-%d")
report = {}
donors = {
    # 'mkslift': mkslift_check,
    # 'ironmac': ironmac_check,
    # 'garopt1': garopt_check,
    # 'garopt2': garopt_check,
    # 'garopt3': garopt_check,
    # 'wiederkraft': wiederkraft_check,
    # 'optimus': optimus_check,
    # '100kwatt_comp': kwatt_check,
    # '100kwatt_hydr': kwatt_check,
    'corsel_promtorg': corsel_check,
    'corsel_dvadomkrata': corsel_check,
}

try:
    for id in chat_ids:
        requests.get(f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={id}&text={message}").json()

    # получение информации о валютах
    currencies = requests.get('https://www.cbr-xml-daily.ru/daily_json.js').json()

except Exception as e:
    print(f'Ошибка: проверьте интернет-соединение.')

# подгрузка настроек из json-файла
try:
    with open('env.json', encoding='utf-8') as settings_file:
        settings = json.load(settings_file)
except Exception as e:
    print(f'Проверьте наличие файла с настройками, {e}')
    input("Чтобы завершить программу, нажмите Enter...")
    sys.exit()

try:
    for account in settings['accounts']:
        data = account['data']
        yandex_token = data['yandex_token']
        excel_file_name = data['excel_file_name']
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': f'OAuth {yandex_token}'}

        # temporary settings
        if excel_file_name == "Promtorg":
            excel_file_name = "corsel_promtorg"
        if excel_file_name == "Dva Domkrata":
            excel_file_name = "corsel_dvadomkrata"


        # открываем xlsx файл выгрузки
        df = pd.read_excel(f"{excel_file_name}.xlsx", sheet_name='Объявления')
        print(f"\n      Avito аккаунт — {account['name']}")

        # Загрузка последних версий обратных выгрузок на яндекс диск с почты
        # imap_download(contact_number, excel_file_name, settings['imap_pass'], headers)

        # перебор доноров и их проверка    
        for donor in data['donors']:

            check_new = True if donor["check_new"].lower() == "true" else False
            update = True if donor["update"].lower() == "true" else False
            yandex_img_path = donor['yandex_image_folder_path']
            create_folder(donor['yandex_image_folder_path'], headers) # создание папки для изображений, если ее нет

            args = [update, df, donor['link'], donor['discount'], headers, yandex_img_path, donor["annex"], check_new, excel_file_name, currencies]
            
            # запуск проверки конкретного донора, магия тут
            if donor['name'] in donors.keys():
                print(f"    Донор — {donor['name']}, Скидка — {donor['discount']}% ===-")
                report[donor['name']] = launch(donors[donor['name']], args)[0]
        
        print(f'Запись в файл — {excel_file_name}.xlsx. Обновление поля DateEnd...')
        # df = change_dateend(df, yesterday)
        # df.to_excel(f'{excel_file_name}.xlsx', sheet_name='Объявления', index=False)

    # Создание отчета
    message = ['Обновление завершено. Отчет о проверке:\n']
    for key in report:
        report_raw = f'{key}:\n{report[key]}\n'
        message.append(report_raw)
    message = '\n'.join(message)
    print(message)
    for id in chat_ids:
        requests.get(f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={id}&text={message}").json()

except Exception as e:
    print(f'Ошибка: при работе с файлами, {e}')



# удаление локальных файлов
# for account in settings['accounts']:
#     yandex_token = account['data']['yandex_token']
#     excel_file_name = account['data']['excel_file_name']
#     headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': f'OAuth {yandex_token}'}
#     upload_file(f'{excel_file_name}.xlsx', f'/{excel_file_name}.xlsx', headers, replace=True)
#     os.remove(f'{excel_file_name}.xlsx')



input("Чтобы завершить программу, нажмите Enter...")
# pyinstaller -F -i 'avito-icon.png' app.py