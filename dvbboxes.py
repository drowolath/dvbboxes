#!/usr/bin/env python
# encoding: utf-8

import collections
import ConfigParser
import json
import logging
import redis
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler

CONFIG = ConfigParser.ConfigParser(allow_no_value=True)
CONFIG.read('/etc/dvbboxes/configuration')

CLUSTER = collections.OrderedDict()

TOWNS = [
    name.split(':')[-1] for name in CONFIG.sections()
    if name.startswith('CLUSTER:')
    ]

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
            raise exc
        else:
            self.day = day
            self.timestamp = timestamp or time.mktime(
                time.strptime('{} 073000'.format(self.day),
                              CONFIG.get('LOG', 'datefmt'))
                )
            self.redis_zset_key = '{day}:{service_id}'.format(
                day=day, service_id=service_id)

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
                if len(data) > foo[0] and data[-1][1] > foo[1]:
                    foo = (len(data), data[-1][1])
                    infos = data
        return infos


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


class Town(object):
    """represents a town's cluster"""
    def __init__(self, name):
        self.name = name
        self.servers = CLUSTER.get(self.name, None)
        self.rdbs = {
            server: {
                'programs': redis.Redis(
                    port=CONFIG.get('CLUSTER:'+self.name, server), db=0),
                'media': redis.Redis(
                    port=CONFIG.get('CLUSTER:'+self.name, server), db=1),
                }
            for server in self.servers
            }

    def __repr__(self):
        return '<Town {}>'.format(self.name)

    def parselisting(self, filepath):
        """extract infos from a listing file"""
        today = time.localtime()
        infos = {}
        day = None
        start = None
        errors = None
        bar = None
        files = {}
        with open(filepath) as infile:
            for line in infile:
                line = line.replace('\n', '')
                if line:
                    if line.startswith('['):
                        index = 0
                        if bar:
                            bar['stop'] = datetime.fromtimestamp(
                                start).strftime('%d-%m-%Y %H:%M:%S')
                            infos[day] = bar
                        errors = []
                        bar = {}
                        day = line.replace('[', '').replace(']', '')
                        day = day.replace('/', '')
                        year = today.tm_year
                        if int(day[2:]) < today.tm_mon:
                            year += 1
                        day = '{0}{1}'.format(day, year)
                        start = '{}073000'.format(day)
                        start = time.mktime(
                            time.strptime(start, '%d%m%Y%H%M%S')
                            )
                        bar['start'] = datetime.fromtimestamp(
                                start).strftime('%d-%m-%Y %H:%M:%S')
                    else:
                        if line not in files:
                            duration = self.media(line)[0]
                            files[line] = duration
                        else:
                            duration = files[line]
                        bar[line+':'+str(index)] = (start, duration)
                        start += duration
                        index += 1
            else:
                if bar:
                    bar['stop'] = datetime.fromtimestamp(
                        start).strftime('%d-%m-%Y %H:%M:%S')
                    infos[day] = bar
        return infos
        

    def program(self, day=None, service_id=None, timestamp=None):
        """program manager for the town"""
        if day:
            try:
                datetime.strptime(day, '%d%m%Y')
            except ValueError as exc:
                raise exc
            else:
                if not service_id:  # search for existing programs
                    results = set()
                    for server, rdb in self.rdbs.items():
                        for key in rdb['programs'].keys(day+':*'):
                            results.add(key)
                    return list(results)
                else:
                    bar = {}
                    for server, rdb in self.rdbs.items():
                        info = rdb['programs'].zrange(
                            day+':'+str(service_id), 0, -1, withscores=True)
                        bar[server] = info
                    # now we check the most accurate program
                    foo = (0, 0)
                    server = None
                    for i, j in bar.items():
                        if len(j) > foo[0] and j[-1][1] > foo[1]:
                            foo = (len(j), j[-1][1])
                            server = i
                    return bar[server]
        elif service_id:  # search for existing program
            results = set()
            for server, rdb in self.rdbs.items():
                for key in rdb['programs'].keys('*:'+str(service_id)):
                    results.add(key)
            return list(results)
        else:
            results = set()
            for server, rdb in self.rdbs.items():
                for key in rdb['programs'].keys('*:*'):
                    results.add(key)
            return list(results)
