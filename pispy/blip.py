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

def send_to_proxy(series, names, values):
    payload = [{
        'name': series,
        'columns': names,
        'points': [values],
    }]
    proxy_url = '{}/incoming?u={}&p={}'.format(settings['app_url'],
        settings['influxdb']['user'], settings['influxdb']['password'])
    resp = requests.post(proxy_url, data=json.dumps(payload))
    print("InfluxDB Response: {}".format(resp.status_code))

def check_temp():
    try:
        with open('/sys/class/thermal/thermal_zone0/temp') as temp_file:
            temp = temp_file.read()
            try:
                return int(temp) / 1000
            except ValueError:
                pass
    except FileNotFoundError:
        pass
    return None


if __name__ == '__main__':
    while True:
        response_times = []
        for name, url in URLS.items():
            response_times.append(ping_url(name, url))
        send_to_proxy('http_ping_time', list(URLS.keys()), response_times)
        temp = check_temp()
        if temp is not None:
            send_to_proxy('cpu_temp', ['value'], [temp])
        time.sleep(1)



