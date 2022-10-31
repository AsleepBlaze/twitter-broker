# -*- encoding: utf-8 -*-

import os.path
import datetime_tz

bearer_token=None
requests_proxies=None
tweets_search_timedelta=datetime_tz.timedelta(minutes=1)
tweets_search_initial_start_timedelta=datetime_tz.timedelta(hours=1)
tweets_search_query='#ETHW is:retweet'
timberland_gateway='http://127.0.0.1:4000'

if os.path.exists(os.path.join(os.path.dirname(__file__), 'virtual.py')):
    import virtual
    if hasattr(virtual, 'bearer_token'):
        bearer_token = virtual.bearer_token
    if hasattr(virtual, 'requests_proxies'):
        requests_proxies = virtual.requests_proxies
    if hasattr(virtual, 'tweets_search_timedelta'):
        tweets_search_timedelta = virtual.tweets_search_timedelta
    if hasattr(virtual, 'tweets_search_initial_start_timedelta'):
        tweets_search_initial_start_timedelta = virtual.tweets_search_initial_start_timedelta
    if hasattr(virtual, 'tweets_search_query'):
        tweets_search_query = virtual.tweets_search_query
    if hasattr(virtual, 'timberland_gateway'):
        timberland_gateway = virtual.timberland_gateway