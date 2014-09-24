#-*- coding: utf-8 -*-
from tweepy import OAuthHandler
from tweepy import API
from tweepy import Cursor
import re
import sqlite3
import requests
import shutil
from settings import CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET, log_file
import logging
import sys


def fetch_url(tweetid, url):
    response = requests.get(url, stream=True)
    logging.info('[=] Fetched paste from {}'.format(response.url))
    if 'pastebin' in response.url:
        source = 'pastebin'
    elif 'pastie' in response.url:
        source = 'pastie'
        url = response.url.replace("view", "download")
    elif 'slexy' in response.url:
        source = 'slexy'
    else:
        source = 'other'
        logging.info('[=] URL is: %s', url)
    with open('cache/{}_{}.gz'.format(tweetid, source), 'wb') as out_file:
        shutil.copyfileobj(response.raw, out_file)
        logging.info("[+] Stored paste from tweet: {} - Size: {}".format(tweetid, len(response.text)))
    del response


def process_status(tweet):
    conn.execute('INSERT OR IGNORE INTO tweets VALUES (?,?, ?,?)', (tweet.id, tweet.user.id, tweet.created_at, tweet.text))
    conn.commit()
    urls = map(lambda x: x['expanded_url'], tweet.entities['urls'])
    for url in urls:
        fetch_url(tweet.id, url)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v", "--verbose", help="more verbose", action="store_true")
    parser.add_argument(
        "-l", "--latest", help="list ten latest tweets", action="store_true")
    args = parser.parse_args()
    level = logging.INFO
    if args.verbose:
        level = logging.DEBUG
    conn = sqlite3.connect('tweetnom.db')
    logging.basicConfig(
        format='%(asctime)s [%(levelname)s] %(message)s', filename=log_file, level=level)
    conn.execute('CREATE TABLE IF NOT EXISTS tweets (id integer primary key, author_id integer, timestamp text, body text)')
    logging.debug("[=] Existing tweets: %s", conn.execute('SELECT COUNT(*) FROM tweets').fetchone())

    if args.latest:
        tweet_list = conn.execute("SELECT * FROM tweets ORDER BY id desc LIMIT 30").fetchall()
        print "Latest 30 tweets:"
        for t in tweet_list:
            print("{} - {}".format(t[2], t[3]))
        print "--------------------"
        conn.close()
        sys.exit(0)
    logging.debug('[+] Connecting to Twitter...')
    auth = OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    api = API(auth)
    tweets = None

    latest_tweet = conn.execute('SELECT id FROM tweets ORDER BY id desc').fetchone()
    if latest_tweet:
        logging.debug("[=] Latest TweetID: %s", latest_tweet)
        tweets = api.user_timeline('dumpmon', since_id=latest_tweet[0])
        logging.debug("[=] Tweets since last fetch: %s", len(tweets))
        for tweet in tweets:
            process_status(tweet)
    conn.close()
