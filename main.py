import datetime
import json
import time

from elasticsearch import Elasticsearch
from elasticsearch import helpers
from pymongo import MongoClient
from tqdm import tqdm


class MigrateToElastic(object):
    def __init__(self, mongodb, esdb, mapping):
        self._mongodb = mongodb
        self._esdb = esdb
        self._mapping = mapping

    def _createindexwithmap(self, index_name):
        response = self._esdb.indices.create(
            index=index_name,
            body=self._mapping,
            ignore=400
        )
        if 'acknowledged' in response:
            if response['acknowledged']:
                print("INDEX MAPPING SUCCESS FOR INDEX:", response['index'])

        # catch API error response
        elif 'error' in response:
            print("ERROR:", response['error']['root_cause'])
            print("TYPE:", response['error']['type'])

        # print out the response:
        print('\nresponse:', response)

    def _defaultdateconverter(self, o):
        if isinstance(o, datetime):
            return o.__str__()

    def migrate(self):
        list_of_collections = self._mongodb.list_collection_names()
        number_of_collections = len(list_of_collections)
        for col in tqdm(list_of_collections, total=number_of_collections):
            collection = self._mongodb[col].find()
            number_of_documents = collection.count()
            actions = []
            for i in range(number_of_documents):
                data = collection[i]
                mongo_id = data['_id'].generation_time
                data.pop('_id', None)

                actions.append({
                    "_index": col,
                    "_id": str(data.get("column_id")),
                    "_source": data
                })
            # create index
            self._createindexwithmap(col)
            # write data
            helpers.bulk(self._esdb, actions, request_timeout=500)
            time.sleep(0.01)


if __name__ == '__main__':
    # connect to mongo
    _mongo_client = MongoClient("localhost", 27017)
    _mydb = _mongo_client["local_test"]

    # Elasticsearch Config
    _es = Elasticsearch(["localhost"])

    # Load Index Mapping
    _mapping = json.load(open("mapping.json"))

    MigrateToElastic(_mydb, _es, _mapping).migrate()
