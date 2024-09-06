

def launch(checker, args):
    update, df, link, discount, lower_price_limit, headers, img_path, annex, check_new, excel_file_name, currencies = args
    if update:
        try:
            df_row_count_before = len(df)
            df = checker(df, link, discount, lower_price_limit, headers, img_path, annex, check_new, excel_file_name, currencies)
            df_row_count_after = len(df)
            new_row_count = df_row_count_after - df_row_count_before
            check = 'ВКЛ.' if check_new else 'ВЫКЛ.'
            result = f' - новые позиции: {new_row_count} (проверка {check})\n - скидка: {discount}%'
        except Exception as e:
            result = f'ошибка при работе с донором'
            print(f'{result}: {e}\n')
    else: result = f'обновление донора отключено'

    return result, df