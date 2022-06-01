#!/usr/bin/python3

import cv2
import numpy as np
import PIL.Image as Image
import pyocr
import pyocr.builders
import sys


def findContoursByColor(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)  # グレースケール画像に変換
    ret, thresh = cv2.threshold(gray, 25, 30, 0)  # 127/255で二値化

    contours, hierarchy = cv2.findContours(
        thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)  # 輪郭を検出
    return contours


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


def crop_max_box(img, contours):
    box_contours = max(contours, key=lambda x: cv2.contourArea(x))

    rect = cv2.boundingRect(box_contours)

    top = rect[1]
    bottom = rect[1] + rect[3]-1
    left = rect[0]
    right = rect[0] + rect[2]-1

    cropped_image = img[top: bottom, left: right]
    return cropped_image


def outer_cropped_image(base_img):
    # 戦闘履歴外側の輪郭取得
    canny = cv2.cvtColor(base_img, cv2.COLOR_BGR2GRAY)
    canny = cv2.GaussianBlur(canny, (5, 5), 0)
    canny = cv2.Canny(canny, 97, 149)

    contours = cv2.findContours(
        canny, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]

    box_contours = max(contours, key=lambda x: cv2.contourArea(x))

    rect = cv2.boundingRect(box_contours)

    top = rect[1]
    bottom = rect[1] + rect[3]-1
    left = rect[0]
    right = rect[0] + rect[2]-1
    cropped_image = base_img[top: bottom, left: right]
    return cropped_image


def inner_cropped_image(base_img):
    # 戦闘履歴内側の輪郭取得
    inner_canny = cv2.cvtColor(base_img, cv2.COLOR_BGR2GRAY)
    inner_canny = cv2.Canny(inner_canny, 0, 100)

    contours = cv2.findContours(
        inner_canny, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]

    box_contours = max(contours, key=lambda x: cv2.contourArea(x))

    rect = cv2.boundingRect(box_contours)

    top = rect[1]
    bottom = rect[1] + rect[3]-1
    left = rect[0]
    right = rect[0] + rect[2]-1

    width = rect[0] + rect[2]-1
    height = rect[1] + rect[3]-1

    cropped_image = base_img[
        top + round(width * 0.01): bottom - round(width * 0) - 10,
        left + round(height * 0.01): right - round(height * 0.02),
    ]
    return cropped_image


def raid_history_crops(base_img):
    history_canny = cv2.cvtColor(base_img, cv2.COLOR_BGR2GRAY)  # グレースケール画像に変換
    history_canny = cv2.GaussianBlur(history_canny, (5, 5), 3)
    ret, thresh = cv2.threshold(history_canny, 25, 30, 0)  # 127/255で二値化

    contours, hierarchy = cv2.findContours(
        thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)  # 輪郭を検出

    results = []
    for i, c in enumerate(contours):
        area = cv2.contourArea(c)
        if (10000 < area):
            rect = cv2.boundingRect(c)

            top = rect[1]
            bottom = rect[1] + rect[3]-1
            left = rect[0]
            right = rect[0] + rect[2]-1

            cropped_image = base_img[top: bottom, left: right]
            results.append(cropped_image)
    return results


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


def getTexts(orig, tool):
    outer_result = outer_cropped_image(orig)
    inner_result = inner_cropped_image(outer_result)
    findContoursByColor(inner_result)

    history_crops = raid_history_crops(inner_result)

    result = []
    for i, image in enumerate(history_crops):
        print(i)
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
        bosses = ['妖精', '族長', 'ミノ', 'マリナ']
        name = next(filter(lambda boss: boss in boss_name_text, bosses), '')

        result.append([user_name, damage_text, boss_level_text, name])
    return result


if __name__ == '__main__':
    tools = pyocr.get_available_tools()
    if len(tools) == 0:
        print("No OCR tool found")
        sys.exit(1)

    tool = tools[0]

    orig = cv2.imread('./images/test.jpg')
    cv2.imshow(orig)
    cv2.waitKey(0)

    texts = getTexts(orig, tool)
    for i, text in enumerate(texts):
        [user_name, damage_text, boss_level_text, name] = text

        print(user_name + ' ' + damage_text +
              ' ダメージ lv.' + boss_level_text + ' ' + name)

    cv2.destroyAllWindows()
