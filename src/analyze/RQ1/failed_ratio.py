import os
import sys
import json
import time
import asyncio
import pymongo

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.dates import date2num
from statsmodels.tsa.stattools import acf
from statsmodels.graphics.tsaplots import plot_acf

from datetime import datetime
from dotenv import load_dotenv


sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

load_dotenv()
INPUT_DIR = os.getenv("OUTPUT_DIR")
FAILED_RATIO_DIR = os.getenv("FAILED_RATIO_DIR")
DEBUG = True if os.getenv("DEBUG") == "True" else False


def get_failed_ratio_from_db():
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["solana"]
    txs_table = mydb["txs_v2"]
    txs_table.create_index([("block_id", 1)])
    print("finish creating index")
    # Aggregation pipeline
    pipeline = [
        # 1. Group by 'block' field
        {
            "$group": {
                "_id": "$block_id",  # Group by the block field
                "blockTime": {
                    "$first": "$blockTime"
                },
                # Count the vote transactions
                "voteCount": {
                    "$sum": {
                        "$cond": [{"$eq": ["$vote", True]}, 1, 0]
                    }
                },
                # Count the non-vote failed transactions
                "nonVoteFailedCount": {
                    "$sum": {
                        "$cond": [
                            {"$and": [
                                {"$ne": ["$error", None]},
                                {"$eq": [{"$type": "$vote"}, "missing"]} 
                            ]},
                            1,
                            0
                        ]
                    }
                },
                # Count the non-vote success transactions
                "nonVoteSuccessedCount": {
                    "$sum": {
                        "$cond": [
                            {"$and": [
                                {"$eq": ["$error", None]},
                                {"$eq": [{"$type": "$vote"}, "missing"]} 
                            ]},
                            1,
                            0
                        ]
                    }
                },
            }
        },
        # 2. Sort by block number (optional)
        {
            "$sort": {"_id": 1}  # Sort the results by block (_id) in ascending order
        },
        {
            "$out": "tx_type_cnts"
        }
    ]
    txs_table.aggregate(pipeline)
    

def get_failed_ratio_per_hour_from_db():
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["solana"]
    txs_type_cnts = mydb["tx_type_cnts"]
    # Aggregation pipeline
    pipeline = [
        { 
            "$match": { 
                "blockTime": { "$ne": None }  # 过滤掉 blockTime 为 None 的文档
            } 
        },
        {
            "$addFields": {
                "blockTimeDate": {
                    "$toDate": {
                        "$multiply": ["$blockTime", 1000]  # 将 Unix 时间戳转换为毫秒
                    }
                }
            }
        },
        {
            "$group": {
                "_id": {
                    "year": { "$year": "$blockTimeDate" },
                    "month": { "$month": "$blockTimeDate" },
                    "day": { "$dayOfMonth": "$blockTimeDate" },
                    "hour": { "$hour": "$blockTimeDate" }
                },
                "totalVoteCount": { "$sum": "$voteCount" },
                "totalNonVoteFailedCount": { "$sum": "$nonVoteFailedCount" },
                "totalNonVoteSuccessedCount": { "$sum": "$nonVoteSuccessedCount" },
                "count": { "$sum": 1 }  # 统计每个小时的文档数
            }
        },
        {
            "$sort": { "_id": 1 }  # 按时间顺序排序
        },
        {
            "$out": "failed_ratio_per_our"
        }
    ]

    txs_type_cnts.aggregate(pipeline)
    return list(mydb['failed_ratio_per_our'].find())

def plot_tx_cnt_per_hour(txs):
    for tx in txs:
        tx['date_hour'] = datetime.strptime(f"{tx['_id']['year']}-{tx['_id']['month']}-{tx['_id']['day']} {tx['_id']['hour']}", "%Y-%m-%d %H")
    block_ids = [entry['date_hour'] for entry in txs]
    vote_counts = [entry['totalVoteCount'] for entry in txs]
    success_non_vote_counts = [entry['totalNonVoteSuccessedCount'] for entry in txs]
    failed_non_vote_counts = [entry['totalNonVoteFailedCount'] for entry in txs]
    failed_non_vote_ratio = [entry['totalNonVoteFailedCount']/(entry['totalNonVoteFailedCount']+entry['totalNonVoteSuccessedCount']) if (entry['totalNonVoteFailedCount']+entry['totalNonVoteSuccessedCount']) > 0 else 0 for entry in txs] 
    total_count = [entry['totalNonVoteFailedCount'] +entry['totalNonVoteSuccessedCount'] for entry in txs]
    print(len(block_ids))
    print(len(success_non_vote_counts))
    print(len(failed_non_vote_counts))
    print(block_ids[:10])
    
    # 创建图形和轴
    fig1, ax1 = plt.subplots(figsize=(12, 6))

    # 绘制堆叠柱状图
    colors = ['crimson', 'blue']
    # j = 0
    # for i in [0] + list(range(8, len(block_ids)-1, 12)):
    #     if i == 0:
    #         ax1.axvspan(block_ids[i], block_ids[i+8], color=colors[j%2], alpha=0.2)
    #     else:
    #         ax1.axvspan(block_ids[i], block_ids[i+12 if i+12 < len(block_ids)-1 else len(block_ids)-1], color=colors[j%2], alpha=0.2)
    #     j = j + 1
    ax1.bar(block_ids[:176], success_non_vote_counts[:176], label='Success Non-Vote Count', color='lightgreen', width=0.04, edgecolor='black')
    ax1.bar(block_ids[:176], failed_non_vote_counts[:176], bottom=success_non_vote_counts[:176], label='Failed Non-Vote Count', color='orangered', width=0.04, edgecolor='black')
    # ax1.bar(block_ids[:176], vote_counts[:176],  bottom=[i+j for i, j in zip(failed_non_vote_counts, success_non_vote_counts)], label='Vote Count', color='royalblue', width=0.04, edgecolor='black')


    ax1.set_ylabel('Count', color='black', fontsize=16)
    ax1.tick_params(axis='both', labelsize=16)
    ax1.legend(loc='upper left', fontsize=18)
    fig1.autofmt_xdate()

    # ax.bar(block_ids, vote_counts, bottom=[x+y for x, y in zip(success_non_vote_counts, failed_non_vote_counts)], label='Vote Count', color='blue', width=1)
    # 显示网格
    ax1.grid(True, which='both', axis='y', linestyle='--', alpha=0.7) 
    ax1.set_title('Distribution of Vote and Non-Vote Counts Over Time')

    fig2, ax2 = plt.subplots(figsize=(12, 6))
    colors = ['crimson', 'blue']
    j = 0
    for i in [0] + list(range(8, len(block_ids)-1, 12)):
        if i == 0:
            ax2.axvspan(block_ids[i], block_ids[i+8], color=colors[j%2], alpha=0.2)
        else:
            ax2.axvspan(block_ids[i], block_ids[i+12 if i+12 < len(block_ids)-1 else len(block_ids)-1], color=colors[j%2], alpha=0.2)
        j = j + 1
    # ax2 = ax1.twinx()
    ax3 = ax2.twinx()
    ax2.plot(block_ids, failed_non_vote_ratio, label='Failed Non-Vote Ratio', color='blue')
    # ax2.xaxis.set_major_locator(mdates.HourLocator(interval=1))  # 每小时显示一个刻度
    # ax2.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))  # 格式化为小时:分钟   
    ax2.legend(loc='upper right', fontsize=14)
    ax2.set_ylabel('Percentage', fontsize=16)
    
    ax3.plot(block_ids, total_count, label='Total Non-Vote Txs', color='green')
    ax3.legend(loc='upper left', fontsize=14)
    ax3.set_ylabel('Count', fontsize=16)
    ax2.tick_params(axis='both', labelsize=16)

    # ax2.grid(True, which='both', axis='y', linestyle='--', alpha=0.7) 
    fig2.autofmt_xdate()
    # 显示图表
    fig1.savefig('/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ1/output_fig/0_failed_cnt.png', dpi=300) 
    fig2.savefig('/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ1/output_fig/1_failed_ratio.png', dpi=300) 

def my_plot_acf(data, is_count=True, lags=24*5):
    fig, ax = plt.subplots(figsize=(12, 6))
    plot_acf(data, lags=lags, ax=ax)
    # Customize the plot (optional)
    # plt.title("Autocorrelation Function (ACF)")
    plt.xlabel("Lag", fontsize=18)
    plt.ylabel("Autocorrelation", fontsize=18)
    plt.tick_params(axis='both', which='major', labelsize=16)
    out_name = "count" if is_count else "ratio"
    plt.grid(True, linestyle='--', alpha=0.7)
    for i in range(1, 6):
        plt.axvline(x=24*i, color='red', linestyle='--', alpha=0.5)

    plt.savefig(f"/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ1/output_fig/2_acf_{out_name}.png", dpi=300)
    

def calculate_correlation(txs):
    failed_non_vote_counts = [entry['totalNonVoteFailedCount'] for entry in txs]
    failed_non_vote_ratio = [entry['totalNonVoteFailedCount']/(entry['totalNonVoteFailedCount']+entry['totalNonVoteSuccessedCount']) if (entry['totalNonVoteFailedCount']+entry['totalNonVoteSuccessedCount']) > 0 else 0 for entry in txs] 
    print(f"min failed non vote count: {min(failed_non_vote_counts)}")
    print(f"average failed non vote count: {sum(failed_non_vote_counts)/len(failed_non_vote_counts)}")
    # calculate correlation
    corr = np.corrcoef(failed_non_vote_counts, failed_non_vote_ratio)
    print(f"Correlation between failed non vote count and failed non vote ratio: {corr[0][1]}")

    # calculate correlation for time series
    my_plot_acf(failed_non_vote_counts, is_count=True)
    my_plot_acf(failed_non_vote_ratio, is_count=False)

if __name__ == "__main__":
    # start_time = time.time()
    # if os.path.exists(f"{FAILED_RATIO_DIR}/failed_ratio.json"):
    #     os.remove(f"{FAILED_RATIO_DIR}/failed_ratio.json")
    # asyncio.run(get_failed_ratio())
    # end_time = time.time()
    # print(f"Run Time:{end_time-start_time}")
    # plot_failed_ratio()
    # plot_cdf_failed_cnt()
    start_time = time.time()
    # get_failed_ratio_from_db()
    # print(f"Finish failed tx count: {time.time()-start_time}")
    results = get_failed_ratio_per_hour_from_db()
    print(f"Finish failed tx count: {time.time()-start_time}")
    calculate_correlation(results)
    plot_tx_cnt_per_hour(results)
    end_time = time.time()
    print(f"Run Time:{end_time-start_time}")