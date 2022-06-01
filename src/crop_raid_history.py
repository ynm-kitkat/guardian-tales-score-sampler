#!/usr/bin/python3

import math
import cv2
import numpy as np
from oauth2client.service_account import ServiceAccountCredentials


def transform_by4(img, points):
    """ 4点を指定してトリミングする。 """
    points = sorted(points, key=lambda x: x[1])  # yが小さいもの順に並び替え。
    top = sorted(points[:2], key=lambda x: x[0])  # 前半二つは四角形の上。xで並び替えると左右も分かる。
    bottom = sorted(points[2:], key=lambda x: x[0],
                    reverse=True)  # 後半二つは四角形の下。同じくxで並び替え。
    points = np.array(top + bottom, dtype='float32')  # 分離した二つを再結合。

    width = max(np.sqrt(((points[0][0]-points[2][0])**2)*2),
                np.sqrt(((points[1][0]-points[3][0])**2)*2))
    height = max(np.sqrt(((points[0][1]-points[2][1])**2)*2),
                 np.sqrt(((points[1][1]-points[3][1])**2)*2))

    dst = np.array([
        np.array([0, 0]),
        np.array([width-1, 0]),
        np.array([width-1, height-1]),
        np.array([0, height-1]),
    ], np.float32)

    # 変換前の座標と変換後の座標の対応を渡すと、透視変換行列を作ってくれる。
    trans = cv2.getPerspectiveTransform(points, dst)
    # 透視変換行列を使って切り抜く。
    return cv2.warpPerspective(img, trans, (int(width), int(height)))


def crop_by_rect(img, rect):
    top = rect[1]
    bottom = rect[1] + rect[3]-1
    left = rect[0]
    right = rect[0] + rect[2]-1

    cropped_image = img[top: bottom, left: right]
    return cropped_image


def crop_max_box(img, contours):
    box_contours = max(contours, key=lambda x: cv2.contourArea(x))

    rect = cv2.boundingRect(box_contours)
    return crop_by_rect(img, rect)


def crop_large_box(base_img):
    # cv2.imshow('0', base_img)
    # cv2.waitKey(1000)
    # cv2.destroyAllWindows()

    image = cv2.cvtColor(
        base_img, cv2.COLOR_BGR2GRAY)  # グレースケール画像に変換

    # blurをかける
    image = cv2.GaussianBlur(image, (5, 5), 3)

    # 二値化
    ret, image = cv2.threshold(image, 50, 255, 0)

    # モルフォロジー膨張処理
    kernel = np.ones((3, 3), np.uint8)
    image = cv2.dilate(image, kernel, iterations=1)

    # エッジ画像に変換
    image = cv2.Canny(image, 1, 100, apertureSize=7)

    # 輪郭を抽出
    contours, hierarchy = cv2.findContours(
        image, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # 抽出した輪郭のうち、四角形であるものを抽出する
    curves = []
    for contour, hierarchy in zip(contours, hierarchy[0]):
        curve = cv2.approxPolyDP(
            contour, 0.01*cv2.arcLength(contour, True), True)
        if len(curve) == 4 and 100 < cv2.contourArea(curve) / 1000:
            curves.append(curve)
    curves = sorted(curves, key=lambda x: (x.ravel()[1], x.ravel()[0]))

    # print(f'四角形の数{len(curves)}')
    # for curve in curves:
    #     print(f'面積： {cv2.contourArea(curve)}')

    # 元画像をコピー
    image = base_img.copy()

    # image = cv2.cvtColor(
    #     base_img, cv2.COLOR_BGR2GRAY)  # グレースケール画像に変換

    # 抽出した四角形を画像に描画する
    # for i, curve in enumerate(curves):
    #     p1, p3 = curve[0][0], curve[2][0]
    #     x1, y1, x2, y2 = p1[0], p1[1], p3[0], p3[1]
    #     r, g, b = random.random()*255, random.random()*255, random.random()*255
    #     cv2.rectangle(image, (x1, y1), (x2, y2),
    #                   (r, g, b), thickness=4)

    image = crop_max_box(image, curves)
    # cv2.imshow('crop_large_box', image)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()

    return image


def do(base_img):
    # cv2.imshow('0', base_img)
    # cv2.waitKey(1000)
    # cv2.destroyAllWindows()

    image = cv2.cvtColor(
        base_img, cv2.COLOR_BGR2GRAY)  # グレースケール画像に変換

    # blurをかける
    image = cv2.GaussianBlur(image, (5, 5), 3)

    # 二値化
    ret, image = cv2.threshold(image, 30, 255, 0)

    # エッジ画像に変換
    image = cv2.Canny(image, 1, 100, apertureSize=7)

    # モルフォロジー膨張処理
    kernel = np.ones((3, 3), np.uint8)
    image = cv2.dilate(image, kernel, iterations=2)

    # モルフォロジー収縮処理
    image = cv2.erode(image, kernel, iterations=2)

    # dilateで膨張処理
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (6, 6))
    image = cv2.dilate(image, kernel)

    # 輪郭を抽出
    contours, hierarchy = cv2.findContours(
        image, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # 抽出した輪郭のうち、四角形であるものを抽出する
    # 面積の降順でソート
    contours = sorted(
        contours, key=lambda x: cv2.contourArea(x), reverse=False)

    curves = []
    for contour, hierarchy in zip(contours, hierarchy[0]):
        curve = cv2.approxPolyDP(
            contour, 0.01*cv2.arcLength(contour, True), True)
        area = math.floor(cv2.contourArea(curve) / 1000)
        if len(curve) == 4 and 150 < area and area < 300:
            curves.append(curve)
            if 4 <= len(curves):
                break
    curves = sorted(curves, key=lambda x: (x.ravel()[1], x.ravel()[0]))

    # 元画像をコピー
    temp_image = base_img.copy()

    results = []
    for curve in curves:
        cropped = transform_by4(temp_image, curve[:, 0, :])
        results.append(cropped)
        # cv2.imshow('cropped', cropped)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()

    # 抽出した四角形を画像に描画する
    # for i, curve in enumerate(curves):
    #     p1, p3 = curve[0][0], curve[2][0]
    #     x1, y1, x2, y2 = p1[0], p1[1], p3[0], p3[1]
    #     r, g, b = random.random()*255, random.random()*255, random.random()*255

    #     area = math.floor(cv2.contourArea(curve) / 1000)
    #     print(f'面積： {area}')
    #     cv2.rectangle(temp_image, (x1, y1), (x2, y2),
    #                   (r, g, b), thickness=2)
    #     cv2.imshow('temporary', temp_image)
    #     cv2.waitKey(0)
    #     cv2.destroyAllWindows()

    return results
