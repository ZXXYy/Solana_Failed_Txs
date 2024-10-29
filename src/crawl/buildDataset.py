import os
import sys
import time
import asyncio
import pymongo
import motor.motor_asyncio

from dotenv import load_dotenv

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from utils.fileOps import async_read_from_file

load_dotenv()
INPUT_DIR = os.getenv("OUTPUT_DIR")
START_BLOCK = 252345000
# END_BLOCK = 253566000
END_BLOCK = 252345005


semaphore = asyncio.Semaphore(100)
myclient = pymongo.MongoClient("mongodb://localhost:27017/")
# myclient = motor.motor_asyncio.AsyncIOMotorClient('mongodb://localhost:27017')
mydb = myclient["solana"]
txs_table = mydb["txs_v2"]
txs_table.create_index([("block_id", 1), ("rank", 1)], unique=True)
print(mydb.list_collection_names())

async def insert_txs_per_block(blkid, txs=None):
    if txs is None:
        txs = await async_read_from_file(f"{INPUT_DIR}/{blkid}.json")
    for i, tx in enumerate(txs):
        tx['block_id'] = blkid
        tx['rank'] = i
    try:
        if len(txs) > 0:
            x = txs_table.insert_many(txs)
            # print(blkid)
    except pymongo.errors.BulkWriteError as e:
        for err in e.details['writeErrors']:
            print(f"Error: {err['errmsg']} (on document with _id: {err['op']['_id']})")
    except Exception as e:
        print(f"{blkid}: {e}")

        
async def delete_txs_per_block(blkid):
    if blkid % 1000 == 0:
        print(blkid)
    query = {
        'block_id': blkid
    }
    txs_table.delete_many(query)
        
async def update_txs_per_block(blkid, txs=None):
    if txs is None:
        txs = await async_read_from_file(f"{INPUT_DIR}/{blkid}.json")
    for i, tx in enumerate(txs):
        if 'vote' in tx:
            continue
        tx['rank'] = i
        query = {
            'block_id': blkid,
            'rank': i
        }
        signer = tx['signer']
        update = { "$set": tx }
        try:
            txs_table.update_one(
                query, update
            )
        except Exception as e:
            print(f"{blkid}-{i}: {e}")

# Wrapper function to enforce the concurrency limit
async def limited_insert_txs_per_block(block):
    async with semaphore:
        await insert_txs_per_block(block)

async def limited_delete_txs_per_block(blkid):
    async with semaphore:
        await delete_txs_per_block(blkid)

async def limited_update_txs_per_block(blkid):
    async with semaphore:
        await update_txs_per_block(blkid)

async def insert_txs():
    tasks = []
    blocks =  range(START_BLOCK, END_BLOCK) # if DEBUG else range(252366000, 252566000)
    tasks = [asyncio.create_task(limited_update_txs_per_block(i)) for i in blocks]
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    start_time = time.time()
    asyncio.run(insert_txs())
    end_time = time.time()
    print(f"Run Time: {end_time-start_time}")
    # plot_failed_ratio()
    # myquery = { "vote": True }

    # mydoc = txs_table.find(myquery)
    # for x in mydoc:
    #     print(x)
