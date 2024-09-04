import pandas as pd
from tqdm import trange

# active_phrases = ("В наличии", "Под заказ", "Активно")
inactive_phrases = ("Нет в наличии", "Снято с публикации", "Истёк срок публикации", "В архиве", "Отклонено", "Заблокировано")

def change_dateend(df, date):
    df['DateEnd'] = pd.to_datetime(df.DateEnd).dt.strftime('%Y-%m-%d')
    for i in trange(len(df)):
        dateend = ""
        if str(df.loc[i, 'Availability']) in inactive_phrases or str(df.loc[i, 'AvitoStatus']) in inactive_phrases:
            dateend = date
        df.loc[i, 'DateEnd'] = dateend
    
    return df