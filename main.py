import json
import os
import re
import time
from hashlib import md5
from multiprocessing.pool import Pool
from urllib.parse import urlencode
from config import *
import pymongo
from bs4 import BeautifulSoup
import requests

client = pymongo.MongoClient(MONGO_URL)
db = client[MONGO_DB]
headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                  " AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/76.0.3809.100 Safari/537.36",
    "cookie": "__tasessionId=4a9zluiz71566700848776; csrftoken=ce41526412c8d0d658ba9cb03c57e48d; tt_webid=6728928876406556172;"
              " s_v_web_id=1544f4b3d03b777be73047011dd502d8; sso_uid_tt=8f87c14fc7d2e144ea7fa69098777282;"
              " toutiao_sso_user=3ebff1699eda0ee2732a068df0c9d195; login_flag=7feb51516eef5293337e513db28a061f; "
              "sessionid=45c595a176fc2b896247a4edd7efd1e8; uid_tt=8250f3751cc1612dfafa190be3e6503b8d60e577a76d5c0ef833794984553fe0;"
              " sid_tt=45c595a176fc2b896247a4edd7efd1e8; sid_guard='45c595a176fc2b896247a4edd7efd1e8|1566701837|15552000|Fri\054 21-Feb-2020 02:57:17 GMT'; "
              "tt_webid=6728928876406556172; WEATHER_CITY=%E5%8C%97%E4%BA%AC"

}


def get_page_index(KEYWORD, offset):
    data = {
        "aid": 24,
        "app_name": "web_search",
        "offset": offset,
        "format": "json",
        "keyword": KEYWORD,
        "autoload": "true",
        "count": 20,
        "en_qc": 1,
        "cur_tab": 1,
        "from": "search_tab",
        "pd": "synthesis"
    }
    params = urlencode(data)
    base_url = "https://www.toutiao.com/api/search/content/"
    url = base_url + '?' + params
    print(url)
    try:
        response = requests.get(url=url, headers=headers)
        if response.status_code == 200:
            res = response.text
            return res
        return None
    except ConnectionError:
        print('请求索引页出错')
        return None


def parse_page_index(html):
    data = json.loads(html)
    if data and 'data' in data.keys():
        for item in data.get('data'):
            yield item.get('article_url')
    return None


def get_page_detail(url):
    try:
        response = requests.get(url=url, headers=headers)
        if response.status_code == 200:
            res = response.text
            return res
        return None
    except ConnectionError:
        print('请求详情页出错 ', url)
        return None


def parse_page_detail(html, url):
    soup = BeautifulSoup(html, 'lxml')
    title = soup.select('title')[0].get_text()
    images_pattern = re.compile(r'gallery: JSON.parse\("(.*)"\),', re.S)
    result = re.search(images_pattern, html)
    if result:
        result = result.group(1).replace(r"\\u002F", "")
        result = result.replace(r'\"', '"')
        result = re.sub('\\\\', '/', result)
        data = json.loads(result)
        if data and "sub_images" in data.keys():
            sub_images = data.get("sub_images")
            images = [item.get("url") for item in sub_images]
            for image in images:
                download_image(image)
            return {
                'title': title,
                'url': url,
                'images': images
            }


def download_image(url):
    print('正在下载：', url)
    try:
        response = requests.get(url=url, headers=headers)
        if response.status_code == 200:
            save_image(response.content)
        return None
    except ConnectionError:
        print('请求图片出错 ', url)
        return None


def save_image(content):
    file_path = '{0}/{1}.{2}'.format(os.getcwd(), md5(content).hexdigest(), 'jpg')
    if not os.path.exists(file_path):
        with open(file_path, 'wb') as f:
            f.write(content)


def save_to_mongo(result):
    try:
        if db[MONGO_TABLE].insert(result):
            print('存储到MongoDB成功')
            return
        print('未储存到MongoDB')
    except TypeError:
        print('None')


def main(offset):
    html = get_page_index(KEYWORD, offset)
    if html:
        for url in parse_page_index(html):
            if url:
                html = get_page_detail(url)
                if html:
                    result = parse_page_detail(html, url)
                    if result:
                        save_to_mongo(result)


if __name__ == '__main__':
    # groups = [x * 20 for x in range(GROUP_START, GROUP_END + 1)]
    # pool = Pool
    # pool.map(main,groups)
    for x in range(20):
        main(x*20)
        time.sleep(2)