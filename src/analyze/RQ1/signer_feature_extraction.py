import time
import pymongo
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from tqdm import tqdm
from itertools import pairwise
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import MinMaxScaler

def get_signer_raw_feature(myclient):
    mydb = myclient["solana"]
    txs_table = mydb["txs_v2"]
    pipeline = [
        {
            "$project": {
                "blockTime": 1,
                # "computeUnitsConsumed": 1,
                "error": 1,
                "signer": 1,
            }
        },
        {
            "$group": {
                "_id": {
                    "signer": "$signer",
                    "blockTime": "$blockTime",
                },
                "total_count": {
                    "$sum": 1
                },
                "failed_count": {
                    "$sum": {
                        "$cond": [ { "$ne": [ "$error", None ] }, 1, 0 ]
                    }
                },
                # "consumed_units": {
                #     "$push": "$computeUnitsConsumed"
                # },
            }
        },
        {
            "$sort": {
                "_id.signer": 1,
                "_id.blockTime": 1,
            }
        },
        { "$out": "sign_raw_features"}
    ]
    results = txs_table.aggregate(pipeline, allowDiskUse=True)
    

def get_signer_feature(signer, myclient):
    mydb = myclient["solana"]
    raw_features = mydb["sign_raw_features"]
    signer_features = mydb["signer_features"]
    # # if signer in signer_features continue
    # if signer_features.find_one({"signer": signer}):
    #     print(f"{signer} already exists")
    #     return None
    start_time = time.time()
    pipeline = [
        {
            "$match": {
                 "_id.signer": signer ,
            }
        },
        {
            "$project":{
                "_id.blockTime": 1,
                "total_count": 1,
                "failed_count": 1,
            }
        }
    ]
    results = raw_features.aggregate(pipeline, allowDiskUse=True)
    # print(f"Get Signer Feature from db time:{time.time()-start_time}")

    results = list(results)
    valid_results = [r for r in results if 'blockTime' in r['_id']]
    block_times = [r['_id']['blockTime'] for r in valid_results]
    start_time, end_time = block_times[0], block_times[-1]
    interval = [t2 - t1 for t1, t2 in pairwise(block_times)]
    total_block_txs = sum(r["total_count"] for r in valid_results)
    total_failed_txs = sum(r["failed_count"] for r in valid_results)
    total_result_len = len(valid_results)

    # total_block_txs, total_failed_txs = 0, 0
    # consumed_units = []
    # interval = []
    # start_time, end_time = -1, -1
    # pre_time = -1
    # for i, result in enumerate(results):
    #     # print(result)
    #     if 'blockTime' not in result['_id']:
    #         continue
    #     if start_time == -1:
    #         start_time = result['_id']['blockTime']
    #     end_time = result['_id']['blockTime']
    #     total_block_txs += result["total_count"]
    #     total_failed_txs += result["failed_count"]
    #     # consumed_units.extend(result["consumed_units"])
    #     if pre_time != -1:
    #         interval.append(result['_id']['blockTime']-pre_time)
    #     pre_time = result['_id']['blockTime']
    #     total_result_len = i+1
    
    try:
        if DEBUG:
            print("Txs per block", total_block_txs/total_result_len)
            print("Failed Txs per block", total_failed_txs/total_result_len)
            print("Total blocks", total_result_len)
            print("Interval variance", np.var(interval) if len(interval) > 0 else 0)
            print("Mean interval", sum(interval)/len(interval) if len(interval) > 0 else 0)
            # print("CU variance", np.var(consumed_units))
            # print("Mean CU", sum(consumed_units)/len(consumed_units))
        res = {
            "signer": signer,
            "interval_variance": np.var(interval) if len(interval) > 0 else 0,
            "interval_mean": sum(interval)/len(interval) if len(interval) > 0 else 0,
            # "cu_variance": np.var(consumed_units),
            # "cu_mean": sum(consumed_units)/len(consumed_units),
            "txs_per_block": total_block_txs/total_result_len,
            "failed_txs_per_block": total_failed_txs/total_result_len,
            "total_blocks": total_result_len,
            "total_txs": total_block_txs,
            "total_failed_txs": total_failed_txs,  
            "active_time": end_time-start_time
        }
    except:
        res = None
    signer_features.update_one({"signer": signer}, {"$set": res}, upsert=True)

def get_signers_from_db(signers):
    results = signers.aggregate([
            { "$group": { "_id": "$_id.signer" } },
            { "$sort": { "_id": 1 } },
            { "$project": { "_id": 1 } }
        ], allowDiskUse=True
    )
    return [result['_id'] for result in results]

    
def signer_features_table_exits():
    with  pymongo.MongoClient("mongodb://localhost:27017/") as myclient:
        mydb = myclient["solana"]
    return "signer_features" in mydb.list_collection_names()

if __name__ == "__main__":
    DEBUG = False
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["solana"]

    start_time = time.time()
    #  get signer raw features
    get_signer_raw_feature(myclient)
    mydb["sign_raw_features"].create_index([("_id.signer", 1)])
    # get all signers
    signers = get_signers_from_db(mydb["sign_raw_features"])
    print(f"Total signers: {len(signers)}")
    if DEBUG:
        signers = signers[:10]
    
    # extract signer features
    signer_features = mydb["signer_features"]
    signer_features.create_index([("signer", 1)], unique=True)
    txs_table = mydb["txs_v2"]
    txs_table.create_index([("blockTime", 1)])
    txs_table.create_index([("signer", 1), ("blockTime", 1)])
    print(f"Finish create index: {time.time()-start_time}")
    
    for signer in tqdm(signers):
        # try:
            print(f"========{signer}==========")
            start_time = time.time()
            get_signer_feature(signer, myclient)
            end_time = time.time()
            # print(f"One Signer Run Time:{end_time-start_time}")
        # except Exception as e:
        #     print(f"{signer}: Exception {e}")        

    
    myclient.close()

    