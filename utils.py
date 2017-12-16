try:
    import urllib.parse
except ImportError:
    import urllib
import pymongo
from pymongo.errors import OperationFailure
from collections import defaultdict
import logging
import yaml
import time
import re
import datetime
from functools import partial


logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(name)-4s %(levelname)-6s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


with open('./config.yml', 'r') as f:
    CONFIG = yaml.load(f)

MONGO_CONFIG = CONFIG['mongo_readonly']


class MongoDBReader(object):
    """A mongoDB reader to read data from MongoDB
    """
    client = None

    def __init__(self, db_name, mongo_config=MONGO_CONFIG):
        """
        Connect to MongoDB database
        :param mongo_config: a Python dict object for DB access
        :param kwargs: for future use
        """
        if self.client is None:
            self.db_connect(mongo_config)
        self.db = self.client[db_name]

    @classmethod
    def db_connect(cls, mongo_config):
        """
        Create connection to mongoDB
        :param mongo_config: from configuration file
        :return: None
        """
        for key in ['username', 'password', 'host', 'port', 'database']:
            if key not in mongo_config:
                raise ValueError('{} is missing in configuration'.format(key))

        for key in ['username', 'password']:
            mongo_config[key] = urllib.parse.quote_plus(mongo_config[key])

        cls.client = pymongo.MongoClient(
            'mongodb://{username}:{password}@{host}:{port}/{database}'.format(**mongo_config)
        )

    @property
    def collections(self):
        """List collection names
        :return: a list of collection names
        """
        try:
            return self.db.collection_names()
        except OperationFailure as e:
            logger.error(e)
            return []

    def _get_documents(self, collection, hours=None, filter=None, projection=None, count=True):
        """Return documents from collection within certain seconds from now
        :param collection: name of collection
        :param hours: number of hours to count
        :param filter: filter condition
        :param count: return counts if True, else collections
        :return:
        """
        if filter is None:
            filter = dict()
        if hours is not None:
            filter['timestamp'] = {'$gt': int(time.time() - hours * 3600)}
        posts = self.db[collection]
        if count:
            return posts.find(filter).count()
        else:
            if projection is None:
                return posts.find(filter)
            else:
                return posts.find(filter, projection)

    def count(self, collection, hours=None, filter=None):
        """Return documents from collection within certain seconds from now
        :param collection: name of collection
        :param hours: number of hours to count
        :param filter: searching conditions
        :return:
        """
        return self._get_documents(collection=collection,
                                   hours=hours,
                                   filter=filter,
                                   count=True)

    def read(self, collection, hours=None, filter=None, projection=None):
        """Return documents from collection within certain seconds from now
        :param collection: name of collection
        :param hours: number of hours to search
        :param filter: searching conditions
        :return:
        """
        return self._get_documents(collection=collection,
                                   hours=hours,
                                   filter=filter,
                                   projection=projection,
                                   count=False)

    def read_most_recent(self, collection, n=-1):
        """Return n most recently added documents from collection
        :param collection: name of collection
        :return:
        """
        if n < 0:
            return self._get_documents(collection=collection, count=False)
        else:
            self.db[collection].find().sort({"$natural": -1}).limit(n)


def epoch_converter(timestamp):
    """Convert Unix timestamp to python datetime
    :param timestamp:
    :return:
    """
    return datetime.datetime.fromtimestamp(timestamp)


def hourly_inserts(db, collection, hours=72, window=3):
    """Simple stats of new documents inserted in the past hours
    :param db: instance of MongoDBReader class
    :param collection: name of collection
    :param hours: number of hours to count
    :return:
    """
    counter = defaultdict(int)
    for dt in db.read(collection=collection,
                      hours=hours,
                      projection={'_id': 0, 'timestamp': 1}):
        d = epoch_converter(dt['timestamp'])
        counter[(d.year, d.month, d.day, d.hour//window*window)] += 1
    return counter.items()


def format_rows(cols, row):
    dt, counts = row
    return list(dt), [counts[c] if c in counts else 0 for c in cols]


def insert_stats(hours=72, window=3, exclude=[]):
    """A simple counts of insertions in the past hours
    :param hours: number of hours to search
    :param window: time window for counting
    :param exclude: collections to exclude
    :return: cols: collection names, rows: timestamp and document counts i
    """
    db = MongoDBReader('jobs')
    cols, rows = list(), defaultdict(dict)
    for collection in db.collections:
        if re.search('_job$', collection) and collection not in exclude:
            cols.append(collection)
            inserts = hourly_inserts(db=db,
                                     collection=collection,
                                     hours=hours,
                                     window=window)
            for dt, count in inserts:
                rows[dt][collection] = count
    cols.sort()
    rows = sorted(list(map(partial(format_rows, cols), rows.items())))
    return cols, rows


def get_counts(hours=24, exclude=[]):
    """Counts new documents inserted in the past hours
    :param hours: number of hours to count
    :return: a dict to
    """
    db = MongoDBReader('jobs')
    counts = dict()
    for collection in db.collections:
        if re.search('_job$', collection) and collection not in exclude:
            counts[collection] = db.count(collection=collection,
                                          hours=hours)
    return counts


if __name__ == '__main__':
    print(get_counts())
