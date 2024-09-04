import pandas as pd
from tqdm import trange

file_name1 = "new_Выгрузка Промторг.xlsx"
file_name2 = "Соответствие категорий Авито-Мкслифт.xlsx"

vigruzka_df = pd.read_excel(f"output/{file_name1}", sheet_name='Объявления')
category_df = pd.read_excel(f"{file_name2}", sheet_name='Объявления')

column_list = vigruzka_df.columns.intersection(category_df.columns).tolist()[1:]

for i in trange(len(vigruzka_df)): #len(vigruzka_df)
    if type(vigruzka_df.loc[i, 'categoryIDtext']) != float:
        mks_category = vigruzka_df.loc[i, 'categoryIDtext']
        if type(mks_category) != str:
            mks_category = vigruzka_df.loc[i, 'paramCategory']
        mks_category = mks_category.strip()
        for j in range(len(category_df)): #len(category_df)
            for cat in category_df.loc[j][:11]:
                if type(cat) == str and cat.strip() == mks_category:
                    # print(j, cat)
                    for column_name in column_list:
                        # print(column_name, vigruzka_df.loc[i, column_name], category_df.loc[j, column_name])
                        vigruzka_df.loc[i, column_name] = category_df.loc[j, column_name]
                    break
            continue

vigruzka_df.to_excel(f'output/{file_name1}', sheet_name='Объявления', index=False)
