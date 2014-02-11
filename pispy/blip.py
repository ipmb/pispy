#!/usr/bin/env python
import json
import time
import requests

from pispy.app import settings


URLS = {
    'gstatic': 'http://gstatic.com/generate_204',
    'lincolnloop': 'http://lincolnloop.com/generate_204'
}


def ping_url(name, url):
    resp = requests.get(url)
    response_time = resp.elapsed.total_seconds()
    print(name, response_time)
    return response_time

def send_to_proxy(names, values):
    payload = [{
        'name': 'http_ping_time',
        'columns': names,
        'points': [values],
    }]
    proxy_url = '{}/incoming?u={}&p={}'.format(settings['app_url'],
        settings['influxdb']['user'], settings['influxdb']['password'])
    resp = requests.post(proxy_url, data=json.dumps(payload))
    print("InfluxDB Response: {}".format(resp.status_code))


if __name__ == '__main__':
    while True:
        response_times = []
        for name, url in URLS.items():
            response_times.append(ping_url(name, url))
        send_to_proxy(list(URLS.keys()), response_times)
        time.sleep(1)



