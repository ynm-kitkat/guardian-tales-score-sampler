#!/usr/bin/python3

import cv2
import PIL.Image as Image
import pyocr
import pyocr.builders
import sys
import glob
import gspread

import crop_raid_history
from oauth2client.service_account import ServiceAccountCredentials


def crop_top_area(img):
    height, width, _ = img.shape

    top_area_image = img[0: round(height / 3), 0: width]

    user_area_image = top_area_image[0: height, 0: round(width / 2)]
    boss_name_area_image = top_area_image[0: height, round(width / 2): width]
    return [user_area_image, boss_name_area_image]


def crop_bottom_area(img):
    height, width, _ = img.shape

    bottom_area_image = img[round(height / 3): height, 0: width]

    height, width, _ = bottom_area_image.shape

    charactors_area_image = bottom_area_image[0: height, 0: round(
        width * 0.28)]
    damage_area_image = bottom_area_image[0: height, round(
        width * 0.28): round(width * 0.7)]
    boss_area_image = bottom_area_image[0: height, round(width * 0.7): width]

    return [charactors_area_image, damage_area_image, boss_area_image]


def cv2pil(image):
    '''
     [Pillow ↔ OpenCV 変換](https://qiita.com/derodero24/items/f22c22b22451609908ee)
     OpenCV型 -> PIL型 
     '''
    new_image = image.copy()
    if new_image.ndim == 2:  # モノクロ
        pass
    elif new_image.shape[2] == 3:  # カラー
        new_image = cv2.cvtColor(new_image, cv2.COLOR_BGR2RGB)
    elif new_image.shape[2] == 4:  # 透過
        new_image = cv2.cvtColor(new_image, cv2.COLOR_BGRA2RGBA)
    new_image = Image.fromarray(new_image)
    return new_image


def ocr_japanese(pilImage, tool):
    text = tool.image_to_string(
        pilImage,
        lang="jpn",
        builder=pyocr.builders.TextBuilder(tesseract_layout=6)
    )
    return text.replace('  ', '___').replace(' ', '').replace('①', '1').replace('②', '2').replace('③', '3').replace('④', '4').replace('⑤', '5').replace('6', '⑥').replace('⑦', '7').replace('⑧', '8').replace('⑨', '9').replace('⑩', '10').replace('___', ' ')


def ocr_digits(pilImage, tool):
    text = tool.image_to_string(
        pilImage,
        lang='eng', builder=pyocr.builders.DigitBuilder(tesseract_layout=6)
    )
    return text.replace(',', '').replace(' ', '').replace('.', '').replace('-', '')


def ocr_eng(pilImage, tool):
    text = tool.image_to_string(
        pilImage,
        lang='eng', builder=pyocr.builders.TextBuilder(tesseract_layout=6)
    )
    return text


def getTexts(orig, tool):
    history_crops = crop_raid_history.do(orig)

    result = []
    for i, image in enumerate(history_crops):
        [user_name_image, boss_name_image] = crop_top_area(image)
        [charactors_area, damage_area, boss_area] = crop_bottom_area(image)

        # ユーザ名
        gray = cv2.cvtColor(
            user_name_image,
            cv2.COLOR_BGR2GRAY
        )
        ret, thresh = cv2.threshold(gray, 200, 255, 0)  # 2値化
        reverse = cv2.bitwise_not(thresh)  # 色反転
        user_name = ocr_japanese(cv2pil(reverse), tool)

        # ダメージテキスト取得
        gray = cv2.cvtColor(damage_area, cv2.COLOR_BGR2GRAY)  # グレースケール画像に変換
        ret, thresh = cv2.threshold(gray, 200, 255, 0)  # 2値化
        reverse = cv2.bitwise_not(thresh)  # 色反転
        damage_text = ocr_digits(cv2pil(reverse), tool)

        # ボスレベル取得
        gray = cv2.cvtColor(
            boss_name_image, cv2.COLOR_BGR2GRAY
        )  # グレースケール画像に変換
        ret, thresh = cv2.threshold(gray, 200, 255, 0)  # 2値化
        reverse = cv2.bitwise_not(thresh)  # 色反転
        boss_level_text = ocr_digits(cv2pil(reverse), tool)

        # ボス名取得
        gray = cv2.cvtColor(
            boss_name_image, cv2.COLOR_BGR2GRAY
        )  # グレースケール画像に変換
        ret, thresh = cv2.threshold(gray, 100, 200, 3)  # 2値化
        reverse = cv2.bitwise_not(thresh)  # 色反転
        boss_name_text = ocr_japanese(cv2pil(reverse), tool)
        bosses = ['妖精', '族長', 'ミノ', 'マリナ', '司令官', 'ガラム',
                  'ワーム', '首魁', 'エリナ', 'スライム', 'ガスト', 'マッド', '魔獣', '悪魔', 'ハーベスター']
        boss_name = next(
            filter(lambda boss: boss in boss_name_text, bosses), '')

        # とどめ取得
        gray = cv2.cvtColor(
            boss_area, cv2.COLOR_BGR2GRAY
        )  # グレースケール画像に変換
        blur = cv2.GaussianBlur(gray, (5, 5), 3)
        blur = cv2.GaussianBlur(blur, (5, 5), 3)
        ret, thresh = cv2.threshold(blur, 180, 255, 0)  # 2値化
        reverse = cv2.bitwise_not(thresh)  # 色反転
        ocr_data = ocr_eng(cv2pil(reverse), tool)
        is_finish_blow = 'TRUE' if 'x' in ocr_data else 'FALSE'
        result.append([user_name, damage_text, boss_level_text,
                      boss_name, is_finish_blow])
    return result


def getBossId(name):
    if name == 'ハーベスター':
        return '29'
    if name == '魔獣':
        return '30'
    if name == 'マッド':
        return '31'
    if name == '族長':
        return '32'
    if name == '司令官':
        return '25'
    if name == 'ガスト':
        return '26'
    if name == 'ガラム':
        return '27'
    if name == 'スライム':
        return '28'
    if name == 'ワーム':
        return '21'
    if name == 'ミノ':
        return '22'
    if name == 'マリナ':
        return '23'
    if name == '首魁':
        return '24'
    if name == '魔獣':
        return '17'
    if name == '悪魔':
        return '18'
    if name == '族長':
        return '19'
    if name == '妖精':
        return '20'
    # if name == 'マリナ':
    #     return '5'
    # if name == 'ミノ':
    #     return '6'
    # if name == '妖精':
    #     return '7'
    # if name == '族長':
    #     return '8'
    # if name == '司令官':
    #     return '9'
    # if name == 'ガラム':
    #     return '10'
    # if name == 'ワーム':
    #     return '11'
    # if name == '首魁':
    #     return '12'
    if name == 'エリナ':
        return '13'
    # if name == 'スライム':
    #     return '14'
    # if name == 'ガスト':
    #     return '15'
    if name == 'マッド':
        return '16'
    return name


def getMemberId(name):
    if name == 'KitKat':
        return "1"
    if name == 'hira':
        return "2"
    if name == 'ラム':
        return "3"
    if name == 'Ryokun':
        return "4"
    if name == 'JOJA':
        return "5"
    if name == '101':
        return "6"
    if name == 'ゆずぽん':
        return "7"
    if name == '倉井':
        return "8"
    if name == '鶏井':
        return "8"
    if name == 'Mikan':
        return "9"
    if name == 'セツナ':
        return "10"
    if name == 'セッナ':
        return "10"
    if name == 'セツッナ':
        return "10"
    if name == 'セッツナ':
        return "10"
    if name == 'hinmel777':
        return "11"
    if name == 'ナイル':
        return "12"
    if name == 'まあ':
        return "13"
    if name == 'まめ':
        return "14"
    if name == 'Latiss':
        return "15"
    if name == 'カシ':
        return "16"
    if name == 'カシジシ':
        return '16'
    if name == 'むん':
        return "17"
    if name == 'むじゅ':
        return "18"
    if name == 'ハイスター':
        return "19"
    if name == 'NaRaKa':
        return "20"
    if name == 'NaRakKa':
        return "20"
    if name == '叶エル':
        return "21"
    if name == 'あぴどら':
        return "22"
    if name == 'あびぴどら':
        return "22"
    if name == 'エイルン':
        return "23"
    if name == 'Ram':
        return "24"
    if name == '連敗戦士':
        return "25"
    if name == 'カイ':
        return "26"
    if name == 'ささ':
        return "27"
    if name == 'trunk':
        return "28"
    if name == 'いる':
        return "29"
    if name == 'ヒデノリ':
        return "30"
    if name == 'たっちゃん':
        return "31"
    if name == '翼あっと狂音':
        return "32"
    if name == '巽あっと狂音':
        return "32"
    if name == '複あっと狂音':
        return "32"
    if name == 'ねぎ':
        return "33"
    if name == 'シュウ':
        return "34"
    if name == 'れみ':
        return "35"
    if name == 'ラム':
        return "36"
    if name == 'へぴ':
        return "37"
    if name == 'へび':
        return "37"
    if name == 'へびぴ':
        return "37"
    if name == '駄菓子屋':
        return "38"
    if name == 'エマ':
        return "39"
    if name == 'はばぎり':
        return "40"
    if name == 'Hamustar':
        return "41"
    if name == 'ぎゅーどん':
        return "46"
    if name == 'あかご':
        return "47"
    if name == 'まいん':
        return "48"
    if name == '夜桜':
        return "49"
    if name == 'エク':
        return "50"
    if name == 'りん':
        return "51"
    if name == 'リン':
        return "51"
    if name == 'ふくまる':
        return "52"
    if name == 'シリュウ':
        return "53"
    if name == 'へにゃむる':
        return "54"
    if name == 'ふれいはるど':
        return "55"
    if name == 'トトメル':
        return "56"
    if name == 'なたたな':
        return "57"
    if name == 'ふぇるめぇる':
        return "58"
    if name == 'ふえぇえるめえぇる':
        return "58"
    if name == 'ふえるめえぇる':
        return "58"
    if name == 'ふえるめえぇえる':
        return "58"
    if name == 'ふぇえるめぇる':
        return '58'
    if name == 'ふぇえるめえぇる':
        return '58'
    if name == 'ふえぇるめぇる':
        return '58'
    if name == 'ふえぇるめぇえる':
        return '58'
    if name == 'ふぇえるめぇえる':
        return '58'
    if name == 'ふえぇえるめぇる':
        return '58'
    if name == 'フレア':
        return "59"
    if name == 'ふざ':
        return "60"
    if name == 'ふずざ':
        return "60"
    if name == 'てんてん':
        return "61"
    if name == 'オーベル':
        return "62"
    if name == 'オーペベル':
        return "62"
    if name == 'ろん':
        return "63"
    if name == 'salmon':
        return '64'
    if name == 'Salmon':
        return '64'
    if name == 'シルヴィア':
        return '65'
    if name == 'ユア':
        return '66'
    if name == '夜の星':
        return '67'
    return name


def connect_gspread():
    # (1) Google Spread Sheetsにアクセス
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']
    jsonf = "service-account-key.json"
    spread_sheet_key = "18JepKrGcO-bBOKgd3MKWVI7DWAv0QaBbDtDdMJ-SciM"
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        jsonf, scope)
    gc = gspread.authorize(credentials)
    worksheet = gc.open_by_key(spread_sheet_key).get_worksheet_by_id(0)
    return worksheet


def cellsTo2dArray(cells, col):  # colは列の数
    cells2d = []
    for i in range(len(cells) // col):
        cells2d.append(cells[i * col:(i + 1) * col])
    return cells2d


def cellsTo1dArray(cells2d):
    cells1d = []
    for cells in cells2d:
        cells1d.extend(cells)
    return cells1d


if __name__ == '__main__':
    ##############################################################################
    season = '9'
    date = '2022-04-14'
    # season = 'test'
    # date = '1'
    isWriteMode = True
    ##############################################################################

    tools = pyocr.get_available_tools()
    if len(tools) == 0:
        print("No OCR tool found")
        sys.exit(1)
    tool = tools[0]

    results = []
    for image_path in glob.glob(f"./images/{season}/{date}/*"):
        print('')
        print(image_path)
        original_image = (cv2.imread(image_path))
        texts = getTexts(original_image, tool)
        for i, text in enumerate(texts):
            [user_name, damage_text, boss_level_text, name, is_finish_blow] = text
            if damage_text != '' and name != '':
                results.append(text)
                print(user_name + ' ' + damage_text +
                      ' ダメージ lv.' + boss_level_text + ' ' + name + ' ' + is_finish_blow)

    if isWriteMode:
        # ws書き込み処理
        ws = connect_gspread()
        spreadsheetData = ws.get_all_values()

        registeredDataList = []
        notRegisteredDataList = []

        maxId = 0
        maxRow = 0
        for (index, spreadSheetRow) in enumerate(spreadsheetData):
            [_id, _member_id, _boss_id, _boss_level,
                _season_id, _damage, _, _date, _deleted_at, _hero_0, _hero_1, _hero_2, _hero_3, _tool_info] = spreadSheetRow
            if _id == 'id':
                continue
            i = int(_id, 10)
            if maxId < i:
                maxId = i
            maxRow = index + 1

        for row in results:
            [user_name, damage_text, boss_level_text,
                boss_name, is_finish_blow] = row
            member_id = getMemberId(user_name)
            boss_id = getBossId(boss_name)

            findFlag = 0
            for spreadSheetRow in spreadsheetData:
                [_id, _member_id, _boss_id, _boss_level,
                    _season_id, _damage, _, _date, _deleted_at, _hero_0, _hero_1, _hero_2, _hero_3, _tool_info] = spreadSheetRow

                if member_id == _member_id and date == _date and _damage == damage_text and boss_id == _boss_id:
                    registeredDataList.append(row)
                    findFlag = 1
                    break

            if findFlag == 0:
                notRegisteredDataList.append(row)
        print()
        print()

        print(f'シーズン{season}, {date} のデータを画像から取得します')
        print('画像の枚数:', len(glob.glob(f"./images/{season}/{date}/*.jpg")), '枚')
        print('画像から検出した凸履歴:', len(results), '件')
        print('登録済み凸履歴: ', len(registeredDataList), '件')
        print('未登録凸履歴: ', len(notRegisteredDataList), '件')
        print(f'シーズン{season}, {date} の未登録凸履歴', len(
            notRegisteredDataList), '件を書き込みます')

        firstRowNum = maxRow + 1
        newDataCount = len(notRegisteredDataList)

        range_target = f'A{str(firstRowNum)}:N{str(firstRowNum + newDataCount - 1)}'
        for e in notRegisteredDataList:
            print(e)

        print(range_target, 'に書き込みます')
        cell_list = ws.range(range_target)

        for (index, r) in enumerate(notRegisteredDataList):
            [user_name, damage_text, boss_level_text,
                boss_name, is_finish_blow] = r
            member_id = getMemberId(user_name)

            boss_id = getBossId(boss_name)
            i = i + 1
            newData = [
                i,
                member_id,
                boss_id,
                boss_level_text,
                season,
                damage_text,
                is_finish_blow,
                date,
                '',
                '',
                '',
                '',
                '',
                '自動入力されました:' + user_name
            ]
            for (jndex, c) in enumerate(newData):
                cell_list[index * len(newData) + jndex].value = c
        # アップデート
        ws.update_cells(cell_list)
        print('書き込み処理完了！')
        cv2.destroyAllWindows()
