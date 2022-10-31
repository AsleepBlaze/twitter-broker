# -*- encoding: utf-8 -*-

from functools import reduce
import json
from time import sleep
import tornado.autoreload
from settings import bearer_token, requests_proxies, tweets_search_timedelta, tweets_search_initial_start_timedelta, tweets_search_query, timberland_gateway
import requests
import datetime_tz
import logging

logging.getLogger().setLevel(level=logging.INFO)

def push(pair):
    response = requests.request("POST", "{}".format(timberland_gateway), json=dict(following=pair[0], follower=pair[1]))
    if not response.status_code in [200, 201, 204]:
        raise Exception(
            "Request returned an error: {} {}".format(
                response.status_code, response.text
            )
        )

def bearer_oauth(r):
    r.headers["Authorization"] = f"Bearer {bearer_token}"
    r.headers["User-Agent"] = "v2RetweetedByPython"
    return r

def connect_to_endpoint(url, user_fields):
    logging.info(url)
    logging.info(user_fields)
    response = requests.request("GET", url, auth=bearer_oauth, params=user_fields, proxies=requests_proxies)
    if response.status_code != 200:
        raise Exception(
            "Request returned an error: {} {}".format(
                response.status_code, response.text
            )
        )
    return response.json()

def tweets_search(start_time, end_time, next_token=None, size=100):
    try:
        data = connect_to_endpoint(
            'https://api.twitter.com/2/tweets/search/recent',
            dict(
                query=tweets_search_query,
                start_time=start_time.isoformat(), 
                end_time=end_time.isoformat(), 
                expansions='author_id,referenced_tweets.id.author_id',
                max_results=size,
                **{'user.fields': 'profile_image_url'},
                **(dict() if next_token is None else dict(next_token=next_token))
            )
        )

        if not data.get('errors') is None:
            raise Exception(
                "Response error: {} {} {}".format(
                    data.get('title', ''), data.get('detail', ''), json.dumps(data['errors'])
                )
            )
        
        if data['meta']['result_count'] == 0:
            return [], None
        
        tweets = reduce(lambda p, t: dict(p, **{ t['id']: t['author_id'] }), data.get('includes', dict()).get('tweets', []), dict())
        users = reduce(lambda p, u: dict(p, **{ u['id']: dict(username=u['username'], **(dict() if u.get('profile_image_url') is None else dict(profile_image_url=u['profile_image_url']))) }), data.get('includes', dict()).get('users', []), dict())
        
        return list(map(lambda i: (dict(id=i[0], **users[i[0]]), dict(id=i[1], **users[i[1]])), filter(lambda i: not (i[0] is None or users.get(i[0]) is None or i[1] is None or users.get(i[1]) is None), map(lambda t: (tweets.get(reduce(lambda p, r: r['id'] if p is None and r['type'] == 'retweeted' else p, t.get('referenced_tweets', []), None) or '-1'), t['author_id']), data['data'])))), data['meta'].get('next_token')
    except Exception as e:
        logging.error(e.args)
        return None, None

def tweets_search_recent():
    return datetime_tz.datetime_tz.now('UTC') - datetime_tz.timedelta(minutes=1)

def load_parameters():
    try:
        with open('.parameters', 'r') as fo:
            p = json.loads(fo.read())
            start_time = datetime_tz.datetime_tz.utcfromtimestamp(p['start_time'])
            end_time = start_time + tweets_search_timedelta
            return dict(p, **dict(start_time=start_time, end_time=end_time))
    except:
        start_time = datetime_tz.datetime_tz.now('UTC') - tweets_search_initial_start_timedelta
        end_time = start_time + tweets_search_timedelta
        return dict(start_time=start_time, end_time=end_time, next_token=None)

def save_parameters(p):
    with open('.parameters', 'wb') as fo:
        fo.write(json.dumps(dict(p, **dict(start_time=p['start_time'].timestamp(), end_time=None))).encode())

def main():
    parameters = load_parameters()
    recent = tweets_search_recent()
    if parameters['end_time'] > recent:
        delta = int(parameters['end_time'].timestamp() - recent.timestamp() + 1)
        logging.warning("In advance, will sleep {} seconds".format(delta))

        loop = tornado.ioloop.IOLoop.instance()
        loop.add_timeout(deadline=(loop.time() + delta), callback=main)
    else:
        while True:
            pairs, next_token = tweets_search(parameters['start_time'], parameters['end_time'], next_token=parameters.get('next_token'))
            if pairs is None:
                delta = 5 * 60
                logging.warning("Reach errors, will sleep {} seconds".format(delta))

                loop = tornado.ioloop.IOLoop.instance()
                loop.add_timeout(deadline=(loop.time() + delta), callback=main)
                break
            else:
                for pair in pairs:
                    max_times = 300
                    current_times = 1
                    while current_times <= max_times:
                        try:
                            logging.info("[{}/{}]Push: {}, {}".format(current_times, max_times, json.dumps(pair[0]), json.dumps(pair[1])))
                            push(pair)
                            break
                        except Exception as e:
                            logging.error(e.args)
                            
                            if current_times % 10 == 0:
                                logging.warning("Push error, will sleep {} seconds".format(20))
                                sleep(20)
                            else:
                                logging.warning("Push error, will sleep {} seconds".format(1))
                                sleep(1)
                            
                            current_times = current_times + 1
                    
                    if current_times > max_times:
                        delta = 1 * 60
                        logging.warning("Reach errors, will sleep {} seconds".format(delta))

                        loop = tornado.ioloop.IOLoop.instance()
                        loop.add_timeout(deadline=(loop.time() + delta), callback=main)
                        return
                
                if next_token is None:
                    save_parameters(dict(parameters, **dict(start_time=parameters['end_time'], end_time=parameters['end_time'] + tweets_search_timedelta, next_token=None)))
                    loop = tornado.ioloop.IOLoop.instance()
                    loop.add_timeout(deadline=(loop.time() + 1), callback=main)
                    break
                else:
                    parameters['next_token'] = next_token
                    save_parameters(parameters)

if __name__ == '__main__':
    loop = tornado.ioloop.IOLoop.instance()
    loop.add_timeout(deadline=(loop.time() + 1), callback=main)
    tornado.autoreload.start()
    loop.start()

