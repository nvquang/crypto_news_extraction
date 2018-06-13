import requests
from bs4 import BeautifulSoup
import sentiment_news
from dateutil.parser import parse
from pymongo import MongoClient
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
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36",
}


def extract_data():
    current_page = 1
    while True:
        print("Current page number: ", current_page)
        r = requests.get("https://www.ethnews.com/news?page=" +
                         str(current_page), headers=header)
        soup = BeautifulSoup(r.content, 'html.parser')
        news_tags = soup.find_all(class_="article-thumbnail")
        print("Nb of news in current page: ", len(news_tags))
        if len(news_tags) == 0:
            print("Cannot found any news")
            break
        for news_tag in news_tags:
            title_tag = news_tag.select_one(
                "div.article-thumbnail__info > h2 > a")
            title = title_tag.text
            post_url = title_tag['href']
            post_url = "https://www.ethnews.com" + post_url

            img_tag = news_tag.find(name="img",
                                    attrs={"class":
                                           "lazy__img"})
            img_url = img_tag['data-src']

            time_str = news_tag.select_one(
                "div.article-thumbnail__info__etc > div.article-thumbnail__info__etc__date > h6")['data-created-short']
            # time string: Apr 6, 2018 %Y-%m-%d
            datetime_object = parse(time_str.strip())

            name = news_tag.select_one(
                "div.article-thumbnail__info__etc > div.article-thumbnail__info__etc__author > h6 > a").text

            des_t = news_tag.find(name="div",
                                  attrs={"class":
                                         "article-thumbnail__info__summary"})
            description = des_t.text

            sentiment = sentiment_news.sentiment_text(
                title + ". " + description)

            news_object = {"title": title,
                           "post_url": post_url,
                           "image_url": img_url,
                           "publish_time": datetime_object,
                           "author_name": name,
                           "description": description,
                           "sentiment": sentiment,
                           "source": "ethnews"}
            db['news'].insert(news_object)
        current_page += 1


if __name__ == '__main__':
    extract_data()
