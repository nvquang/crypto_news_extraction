import requests
from bs4 import BeautifulSoup
import sentiment_news
from dateutil.parser import parse
import json
from pymongo import MongoClient
import re

import sys
import os
from inspect import getsourcefile
current_path = os.path.abspath(getsourcefile(lambda: 0))
current_dir = os.path.dirname(current_path)
parent_dir = current_dir[:current_dir.rfind(os.path.sep)]
sys.path.insert(0, parent_dir)

import config
config = config.get_config(sys.argv[1])


client = MongoClient(config['db_uri'])
db = client[config['database_name']]

header = {
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6)" +
                  " AppleWebKit/537.36 (KHTML, like Gecko) " +
                  "Chrome/65.0.3325.181 Safari/537.36",
}


def get_ajax_nonce():
    rr = requests.get("https://altcointoday.com/", headers=header)
    soup = BeautifulSoup(rr.content.decode("utf-8"), 'html.parser')
    for e in soup.find_all('script', type='text/javascript'):
        if 'var dtLocal' in e.text:
            text = e.text.replace("var dtLocal = ", '')
            text = text.replace('/* <![CDATA[ */', '')
            text = text.replace('/* ]]> */', '')
            text = text.replace('}};', '}}')
            json_object = json.loads(text)
            return json_object['ajaxNonce']

    return None


def extract_data():
    current_page = 1

    ajaxNonce = get_ajax_nonce()

    if ajaxNonce is None:
        print("Cannot get ajax Nonce, exit altcoin today cralwer")
        return None

    while True:
        print("Current page: ", current_page)
        data = {
            "action": "presscore_template_ajax",
            "postID": 18697,
            "postsCount": 0,
            "paged": current_page,
            "targetPage": current_page,
            "nonce": ajaxNonce,
            "contentType": "blog",
            "pageData": {
                "type": "page",
                "template": 'blog',
                "layout": "masonry"
            },
            "sender": "paginator"
        }

        r = requests.post(
            "https://altcointoday.com/wp-admin/admin-ajax.php",
            data=data,
            headers=header)

        json_object = json.loads(r.content.decode("utf-8"))
        soup = BeautifulSoup(json_object['html'], 'html.parser')
        news_tags = soup.find_all(class_="wf-cell")

        print("Nb of news in current page: ", len(news_tags))
        if len(news_tags) == 0:
            print("Cannot found any news")
            return None

        for news_tag in news_tags:
            entry_tag = news_tag.select_one(
                "article > div.blog-content.wf-td > h2 > a")
            title = entry_tag.text
            post_url = entry_tag['href']

            img_url = ''
            img_tag = news_tag.find(name="img",
                                    attrs={"class":
                                           "preload-me"})

            if img_tag:
                img_url = re.search("(?P<url>https?://[^\s]+)",
                                    img_tag['srcset']).group("url")

            time_str = news_tag['data-date']
            # time string: 2018-04-10T18:00:29+00:00
            datetime_object = parse(time_str.strip())

            name = "AltcoinToday.com"

            des_t = news_tag.select_one("article > div.blog-content.wf-td > p")
            description = des_t.text

            sentiment = sentiment_news.sentiment_text(des_t)

            news_object = {"title": title,
                           "post_url": post_url,
                           "image_url": img_url,
                           "publish_time": datetime_object,
                           "author_name": name,
                           "description": description,
                           "sentiment": sentiment,
                           "source": "altcointoday"}
            db['news'].insert(news_object)
        current_page += 1


if __name__ == '__main__':
    extract_data()
