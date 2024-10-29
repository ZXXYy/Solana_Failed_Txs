import pymongo
import time

import matplotlib.pyplot as plt


def get_signer_cnt_from_db():
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["solana"]
    txs_table = mydb["txs_v2"]
    # txs_table.create_index([("block_id", 1)], unique=True)
    # txs_table.create_index([("signer", 1)])
    pipeline = [
        {
            "$match": {
                "$and": [
                        { "$expr": { "$eq": [ { "$type": "$vote" }, "missing" ] } },  # 检查 vote 字段是否不存在
                        { "$expr": { "$ne": [ { "$type": "$signer" }, "missing" ] } },  # 检查 signer字段存在
                        # { "block_id": { "$gte": 255117800, "$lte": 255643000 } }
                    ]
            }
        },
        {
            "$group": {
                "_id": "$signer",
                "total_count": {
                    "$sum": 1
                },
                "failed_count": {
                    "$sum": {
                        "$cond": [ { "$eq": [ "$error", None ] }, 0, 1 ]
                    }
                },
                "success_count": {
                    "$sum": {
                        "$cond": [ { "$eq": [ "$error", None ] }, 1, 0 ]
                    }
                },
                "total_fees": {
                    "$sum": "$fee"
                }
            }
        },
        {
            "$project": {
                "_id": 1,
                "total_count": 1,
                "failed_count": 1,
                "success_count": 1,
                "failed_ratio": {
                    "$cond": [
                        { "$eq": ["$total_count", 0] },
                        0,
                        { "$divide": ["$failed_count", "$total_count"] }
                    ]
                },
                "total_fees": 1
            }
        },
        {
            "$sort": {
                "total_count": -1
            }
        },
        {
            "$out": "signer_cnt"
        }
    ]
    results = txs_table.aggregate(pipeline)
    
# def get_signer_cnt_from_db():
#     myclient = pymongo.MongoClient("mongodb://localhost:27017/")
#     mydb = myclient["solana"]
#     signers = mydb["failed_signer_cnt"]
#     results = signers.find()
#     return list(results)

def plot_signer_pie(signers):
    print(len(signers))
    print(len([signer for signer in signers if signer["count"] > 200]))
    print(len([signer for signer in signers if signer["count"] < 20]))
    signer = [signer for signer in signers if signer["count"] > 200]
    labels = []
    counts = []
    for signer in signers[:10]:
        print(signer)
        # labels.append(signer["_id"])
        labels.append(0)
        counts.append(signer["count"])
    fig1, ax1 = plt.subplots()
    # ax1.scatter(counts, labels, alpha=0.6)
    # ax1.set_yticks([])
    ax1.pie(counts, labels=labels, autopct='%1.1f%%', startangle=90)
    ax1.axis('equal')
    fig1.savefig("/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ2/output_fig/0_failed_signer_pie.png")

if __name__ == "__main__":
    start_time = time.time()
    # signers = get_signer_cnt_from_db()
    # plot_signer_pie(signers)
    get_signer_cnt_from_db()
    # results = get_failed_ratio_per_hour_from_db()
    # plot_tx_cnt_per_hour(results)
    end_time = time.time()
    print(f"Run Time:{end_time-start_time}")