import pymongo
import time

if __name__ == "__main__":
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["solana"]
    txs_table = mydb["txs_v2"]
    for index in txs_table.list_indexes():
        print(index)
    txs_table.drop_indexes()
    for index in txs_table.list_indexes():
        print(index)
    # txs_table.create_index([("block_id", 1)], unique=True)
    start_time = time.time()
    txs_table.create_index([("block_id", 1)])
    print("block_id index created in ", time.time()-start_time)
    
    start_time = time.time()
    txs_table.create_index([("signer", 1)])
    print("block_id index created in ", time.time()-start_time)

