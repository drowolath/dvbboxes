#!/usr/bin/env python
# encoding: utf-8

import collections
import ConfigParser
import json
import logging
import redis
import sys
import time
from datetime import datetime, timedelta
from flask import Flask
from flask_script import Manager
from logging.handlers import RotatingFileHandler

CONFIG = ConfigParser.ConfigParser(allow_no_value=True)
CONFIG.read('/etc/dvbboxes/configuration')

CLUSTER = collections.OrderedDict()

TOWNS = [
    name.split(':')[-1] for name in CONFIG.sections()
    if name.startswith('CLUSTER:')
    ]

CHANNELS = {
    i: CONFIG.get('CHANNELS', i) for i in CONFIG.options('CHANNELS')
    }

for town in sorted(TOWNS):
    CLUSTER[town] = CONFIG.options('CLUSTER:'+town)

# define logger
LOGGER = logging.getLogger()
LOGGER.setLevel(int(CONFIG.get('LOG', 'level')))
formatter = logging.Formatter(
    '[%(asctime)s] %(levelname)s %(message)s',
    datefmt=CONFIG.get('LOG', 'datefmt')
    )
LOGS = RotatingFileHandler(CONFIG.get('LOG', 'filepath'), 'a', 1000000, 1)
LOGS.setLevel(int(CONFIG.get('LOG', 'level')))
LOGS.setFormatter(formatter)
LOGGER.addHandler(LOGS)

APP = Flask(__name__)
MANAGER = Manager(APP)

reload(sys)
sys.setdefaultencoding('utf-8')

__all__ = [
    'CHANNELS',
    'CLUSTER',
    'CONFIG',
    'Listing',
    'LOGGER',
    'MANAGER',
    'Media',
    'Program',
    'TOWNS'
    ]


class Program(object):
    """represents a program"""
    def __init__(self, day, service_id, timestamp=None):
        """
        :day: string representing a day under format %d%m%Y
        :service_id: integer representing a service id
        :timestamp: float representing a moment in time from which we want
        the program
        """
        self.service_id = str(service_id)
        try:
            datetime.strptime(day, '%d%m%Y')
        except ValueError as exc:
            raise ValueError(exc.message)
        else:
            self.day = day
            self.timestamp = timestamp or time.mktime(
                time.strptime('{} 073000'.format(self.day), '%d%m%Y %H%M%S')
                )
            self.redis_zset_key = '{day}:{service_id}'.format(
                day=day, service_id=service_id)

    def __repr__(self):
        return '<Program {}>'.format(self.redis_zset_key)

    def infos(self, towns=None):
        """return adequate infos"""
        foo = (0, 0)
        infos = None
        if not towns:
            towns = TOWNS
        elif type(towns) is str:
            towns = [towns]
        for town in towns:
            servers = CLUSTER[town]
            for server in servers:
                rdb = redis.Redis(host=server, db=0)
                data = rdb.zrange(self.redis_zset_key, 0, -1, withscores=True)
                if data:
                    initial = data[0][1]
                    if self.timestamp >= initial:
                        recalculated_start = (
                            self.timestamp - min(
                                [
                                    self.timestamp-item for entry, item in data
                                    if item <= self.timestamp
                                    ]
                                )
                            )
                        data = rdb.zrangebyscore(
                            self.redis_zset_key,
                            recalculated_start,
                            initial+86400,
                            withscores=True
                            )
                    if len(data) > foo[0] and data[-1][1] > foo[1]:
                        foo = (len(data), data[-1][1])
                        infos = data
        result = []
        for filepath, timestamp in infos:
            result.append((filepath.split('/')[-1], timestamp))
        result = sorted(result, key=lambda x: int(x[0].split(':')[-1]))
        yield result

    def get_start_time(self, filename, towns=None):
        """returns the start time(s) of a filename in the program"""
        if not filename.endswith('.ts'):
            filename += '.ts'
        result = [
            timestamp for name, timestamp in self.infos(towns)
            if name.split(':')[0].startswith(filename)
            ]
        result = sorted(result)
        return result


class Listing(object):
    """listing operations"""
    def __init__(self, filepath):
        self.filepath = filepath
        listing = ConfigParser.ConfigParser(allow_no_value=True)
        listing.read(self.filepath)
        days = listing.sections()
        today = time.localtime()
        year = today.tm_year
        self.days = []
        for day in days:
            year = today.tm_year
            if int(day[3:]) < today.tm_mon:
                year += 1
            bar = '{0}{1}'.format(day, year)
            bar = bar.replace('/', '')
            self.days.append(bar)
        self.filenames = {}
        filenames = [listing.options(i) for i in days]
        filenames = [
            i for sublist in filenames for i in sublist
            ]
        filenames = list(set(filenames))
        for filename in filenames:
            self.filenames[filename] = Media(filename).duration

    def __repr__(self):
        return '<Listing {}>'.format(self.filepath)

    def parse(self):
        day = None
        data = None
        with open(self.filepath) as infile:
            for line in infile:
                line = line.replace('\n', '').replace('\r', '')
                if line and line.startswith('['):
                    if day:
                        yield json.dumps(data)
                    data = {}
                    day = line.replace(
                        '[', '').replace(
                            ']', '').replace(
                                '/', '')
                    day = [i for i in self.days if i.startswith(day)].pop()
                    start = time.mktime(
                        time.strptime('{} 073000'.format(day), '%d%m%Y %H%M%S')
                        )
                    data['day'] = day
                elif line:
                    duration = self.filenames[line]
                    data[start] = {
                        'filename': line,
                        'duration': duration
                        }
                    start += duration
            else:
                yield json.dumps(data)

    def apply(self, service_id, towns=None):
        for infos in self.parse():
            index = 0
            zset_key = '{0}:{1}'.format(infos['day'], service_id)
            del infos['day']
            if not towns:
                towns = TOWNS
            elif type(towns) is str:
                towns = [towns]
            for town in towns:
                servers = CLUSTER[town]
                for server in servers:
                    rdb = redis.Redis(host=server, db=0)
                    rdb.delete(zset_key)
                    timestamps = sorted(infos)
                    for timestamp in timestamps:
                        info = infos[timestamp]
                        filepath = '/opt/tsfiles/'+info['filename']
                        rdb.zadd(
                            zset_key, filepath+':'+str(index), float(timestamp)
                            )
                        index += 1


class Media(object):
    """media manager"""
    def __init__(self, name):
        self.name = name
        if not name.endswith('.ts'):
            self.name += '.ts'
        self.towns = set()
        self.duration = 0
        for town, servers in CLUSTER.items():
            for server in servers:
                rdb = redis.Redis(
                    port=CONFIG.get('CLUSTER:'+town, server),
                    db=1
                    )
                duration_value = rdb.get(self.name)
                try:
                    if eval(duration_value) > self.duration:
                        self.duration = eval(duration_value)
                    self.towns.add(town)
                except TypeError:
                    pass
        r = redis.Redis(db=1)
        if not self.towns and not self.duration:
            r.delete(self.name)
        else:
            r.set(self.name, self.duration)

    def __repr__(self):
        return '<Media {}>'.format(self.name)

    @staticmethod
    def search(expression, towns=None):
        """search for a filename in the cluster"""
        result = set()
        if not towns:
            towns = TOWNS
        elif type(towns) is str:
            towns = [towns]
        for town in towns:
            servers = CLUSTER[town]
            for server in servers:
                rdb = redis.Redis(
                    port=CONFIG.get('CLUSTER:'+town, server),
                    db=1
                    )
                for i in rdb.keys('*{}*'.format(expression)):
                    result.add(i)
        return sorted(list(result))

    @property
    def schedule(self):
        """return datetimes for which the file is scheduled"""
        result = collections.OrderedDict()
        days = [
            datetime.today() + timedelta(i)
            for i in range(-29, 30)
            ]
        for town in self.towns:
            servers = CLUSTER[town]
            for server in servers:
                rdb = redis.Redis(
                    port=CONFIG.get('CLUSTER:'+town, server),
                    db=0
                    )
                for day in days:
                    day = day.strftime('%d%m%Y')
                    keys = [i.split(':') for i in rdb.keys(day+':*')]
                    for _, service_id in keys:
                        p = Program(day, service_id)
                        timestamps = p.get_start_time(self.name, self.towns)
                        if service_id not in result:
                            result[service_id] = set()
                        for timestamp in timestamps:
                            result[service_id].add(timestamp)
        return result


def cli():
    MANAGER.run()


if __name__ == '__main__':
    cli()
