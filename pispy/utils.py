import os
import time
from urllib.parse import urlparse

def parse_db_conn(conn_str=None):
    """Convert DB connection string to dictionary"""
    parsed = urlparse(conn_str)
    url = parsed.scheme + '://' + parsed.hostname + ':' + str(parsed.port)
    return {
        'user': parsed.username,
        'password': parsed.password,
        'url': url,
        'host': parsed.hostname,
        'port': parsed.port,
        'name': parsed.path.strip('/')
    }

def timestamp_data(data):
    """Adds current timstamp to dictionary formatted for InfluxDB"""
    received = int(time.time() * 1000)
    for datum in data:
        datum['columns'].append('time')
        for point in datum['points']:
            point.append(received)
    return data

def local_path(directory):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), directory)
