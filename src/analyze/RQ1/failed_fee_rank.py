import os
import sys
import json
import time
import datetime
import asyncio
import pymongo
import statistics

import seaborn as sns
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from dotenv import load_dotenv
from scipy import stats

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

load_dotenv()
INPUT_DIR = os.getenv("OUTPUT_DIR")
FAILED_RATIO_DIR = os.getenv("FAILED_RATIO_DIR")
DEBUG = True if os.getenv("DEBUG") == "True" else False

df = pd.DataFrame(columns=['block', 'fee', 'cu', 'gas_per_cu', 'rank', 'rank_ratio', 'is_failed'])
semaphore = asyncio.Semaphore(100)

def get_txs_fee(blkid, txs):
    total_tx = len(txs)
    for i, tx in enumerate(txs):
        if 'vote' in tx:
            continue
        df.loc[len(df)] = {
            'block': blkid, 
            'fee': tx['fee'],
            'cu': tx['computeUnitsConsumed'],
            'gas_per_cu': int(tx['fee'])/int(tx['computeUnitsConsumed']) if int(tx['computeUnitsConsumed'])>0 else 0,
            'rank': i,
            'rank_ratio': i/total_tx,
            'is_failed': False if tx['error'] is None else True,
        }


def plot_cdf_gas_per_cu():
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["solana"]
    failed_gas = mydb["tx_failed_gas_per_cu"].aggregate([
        { "$project": { "fee": 1, "computeUnitsConsumed":1, "_id": 0 } },
    ])
    failed_gas = list(failed_gas)

    df_failed_fees = [x['fee'] for x in failed_gas]
    df_failed_gas = [x['fee']/x['computeUnitsConsumed'] if x['computeUnitsConsumed']!= 0 else 0 for x in failed_gas]
    # df_failed_gas = [value if value < 50 else 50 for value in df_failed_gas]
    df_failed_gas = [value for value in df_failed_gas if value < 5]

    success_gas = mydb["tx_success_gas_per_cu"].aggregate([
        { "$project": { "fee": 1, "computeUnitsConsumed":1, "_id": 0 } },
    ])
    success_gas = list(success_gas)
    df_success_fees = [x['fee'] for x in success_gas]
    df_success_gas = [x['fee']/x['computeUnitsConsumed'] if x['computeUnitsConsumed']!= 0 else 0 for x in success_gas]
    # df_success_gas = [value if value < 50 else 50 for value in df_success_gas]
    df_success_gas = [value for value in df_success_gas if value < 5]
    
    success_cdfx = np.sort(df_success_gas)
    success_cdfy = np.linspace(1 / len(df_success_gas), 1.0, len(df_success_gas))  

    failed_cdfx = np.sort(df_failed_gas) 
    failed_cdfy = np.linspace(1 / len(df_failed_gas), 1.0, len(df_failed_gas))  

    # plt.figure(figsize=(8, 6))
    fig1, ax1 = plt.subplots(figsize=(12, 6))
    ax1.plot(success_cdfx, success_cdfy, color='lightgreen', label='Success fee ')
    ax1.plot(failed_cdfx, failed_cdfy, color='orangered', label='Failed fee ')

    # 添加标题和标签
    ax1.set_title('CDF of fee ')
    ax1.set_xlabel('Fee ')
    ax1.set_ylabel('CDF')
    ax1.legend(loc='lower right')
    ax1.grid(True, linestyle='--', which="major")
    fig1.savefig('/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ1/output_fig/4_failed_fee_cdf_zoom.png', dpi=300) 

    success_cdfx = np.sort(df_success_fees)
    success_cdfy = np.linspace(1 / len(df_success_fees), 1.0, len(df_success_fees))  

    failed_cdfx = np.sort(df_failed_fees) 
    failed_cdfy = np.linspace(1 / len(df_failed_fees), 1.0, len(df_failed_fees))  

    fig2, ax2 = plt.subplots(figsize=(12, 6))
    ax2.plot(success_cdfx, success_cdfy, color='lightgreen', label='Success fee')
    ax2.plot(failed_cdfx, failed_cdfy, color='orangered', label='Failed fee')

    # 添加标题和标签
    ax2.set_title('CDF of fee')
    ax2.set_xlabel('Fees')
    ax2.set_ylabel('CDF')
    ax2.legend(loc='lower right')
    ax2.grid(True, linestyle='--', which="major")
    fig2.savefig('/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ1/output_fig/5_failed_fee_cdf.png', dpi=300) 

def plot_gas_per_cu():
    df_success = df[df['is_failed']==False]
    df_failed = df[df['is_failed']==True]
    success_aggregated_df = df_success.groupby('block').agg({
        'gas_per_cu': 'mean',  
    })
    failed_aggregated_df = df_failed.groupby('block').agg({
        'gas_per_cu': 'mean',  
    })
    fig2, ax2 = plt.subplots(figsize=(12, 6))
    ax2.plot(success_aggregated_df.index.tolist(), success_aggregated_df['gas_per_cu'], label='Success Tx Gas ', color='lightgreen')
    ax2.plot(failed_aggregated_df.index.tolist(), failed_aggregated_df['gas_per_cu'], label='Failed Tx Gas ', color='orangered')
    ax2.legend(loc='upper right')
    ax2.set_ylabel('Percentage')
    ax2.set_title("Failed Ratio")
    ax2.grid(True, which='both', axis='y', linestyle='--', alpha=0.7) 
    fig2.savefig('/data0/xiaoyez/Solana_Ecosystem/failed_fee.png', dpi=300) 

def plot_cu():
    pass

def plot_cdf_rank_ratio():
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["solana"]
    failed_rank = mydb["tx_failed_rank"].aggregate([
        { "$project": { "rank": 1, "_id": 0 } },
    ])
    df_failed_rank = [x['rank'] for x in failed_rank]
    success_rank = mydb["tx_success_rank"].aggregate([
        { "$project": { "rank": 1, "_id": 0 } }
    ])
    df_success_rank = [x['rank'] for x in success_rank]

    success_cdfx = np.sort(df_success_rank)
    success_cdfy = np.linspace(1 / len(df_success_rank), 1.0, len(df_success_rank))  

    failed_cdfx = np.sort(df_failed_rank) 
    failed_cdfy = np.linspace(1 / len(df_failed_rank), 1.0, len(df_failed_rank))  


    plt.figure(figsize=(8, 6))
    plt.plot(success_cdfx, success_cdfy, color='lightgreen', label='Success rank')
    plt.plot(failed_cdfx, failed_cdfy, color='orangered', label='Failed rank')

    # 添加标题和标签
    plt.title('CDF of tx rank')
    plt.xlabel('# rank')
    plt.ylabel('CDF')
    plt.legend(loc='lower right')
    plt.grid(True, linestyle='--', which="major")
    plt.savefig('/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ1/output_fig/3_failed_rank_cdf.png', dpi=300) 

def plot_distribution_rank():
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["solana"]
    failed_rank = mydb["tx_failed_rank"].aggregate([
        { "$project": { "rank": 1, "_id": 0 } },
        # { "$limit": 100000}
    ])
    df_failed_rank = [x['rank'] for x in failed_rank]
    success_rank = mydb["tx_success_rank"].aggregate([
        { "$project": { "rank": 1, "_id": 0 } },
        # { "$limit": 80000}
    ])
    df_success_rank = [x['rank'] for x in success_rank]
    print(len(df_failed_rank), len(df_success_rank))
    print(f"max failed rank: {max(df_failed_rank)}, min failed rank: {min(df_failed_rank)}")
    print(f"average failed rank: {sum(df_failed_rank)/len(df_failed_rank)}, median failed rank: {statistics.median(df_failed_rank)}")
    
    print(f"max success rank: {max(df_success_rank)}, min success rank: {min(df_success_rank)}")
    print(f"average success rank: {sum(df_success_rank)/len(df_success_rank)}, median success rank: {statistics.median(df_success_rank)}")

    # df = pd.DataFrame({ "sucess": df_success_rank, "failed": df_failed_rank })
    df = pd.DataFrame({
        'Rank': df_success_rank + df_failed_rank,
        'Transactions': ['Success'] * len(df_success_rank) + ['Failed'] * len(df_failed_rank)
    })
    plt.figure(figsize=(12, 8))
    sns.set_style("whitegrid")
    sns.violinplot(x='Transactions', y='Rank', data=df, cut=0, inner='box', hue='Transactions', legend=False, palette={'Success': '#1f77b4', 'Failed': '#ff7f0e'})
    plt.xlabel('Transactions', fontsize=18)
    plt.ylabel('Rank', fontsize=18)
    plt.xticks(fontsize=18)
    plt.yticks(fontsize=18)
    # sns.violinplot(data=df, cut=0, scale='width', inner='box')
    plt.savefig('/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ1/output_fig/5_rank_violin.png', facecolor='white', dpi=300)

    # plt.figure(figsize=(12, 8))
    # sns.set_style("whitegrid")
    # sns.violinplot(data=df_failed_rank, cut=0, scale='width', inner='box')
    # plt.savefig('/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ1/output_fig/5_failed_fee_violin.png', facecolor='white', dpi=200)

def print_statistics(df, FILTER_NUM):
    print(f"max failed fee per cu : {max(df)}, min failed fee per cu : {min(df)}")
    print(f"average failed fee per cu : {sum(df)/len(df)}, median failed fee per cu : {statistics.median(df)}")
    # print("filtered failed", len(df), len( [value for value in df if value > FILTER_NUM]))
    print("="*16)

def cost_stripplot(df_success, df_failed, cost_type):
    df = pd.DataFrame({
        cost_type: df_success + df_failed,
        'Transactions': ['Successful'] * len(df_success) + ['Failed'] * len(df_failed)
    })
    plt.figure(figsize=(12, 8))
    plt.xlabel(cost_type, fontsize=18)  # Changed from 'Transactions' to 'Fee per CU'
    plt.ylabel('Transactions', fontsize=18)      # Changed to 'Density' as it's a KDE plot
    plt.xticks(fontsize=16)
    plt.yticks(fontsize=14)
    plt.rcParams['legend.fontsize'] = 14
    plt.rcParams['legend.title_fontsize'] = 16
    plt.xscale('log')

    sns.set_style("whitegrid")
    sns.stripplot(data=df, 
                x=cost_type,             # Specify x variable
                y='Transactions',           # Specify y variable
                hue='Transactions',         
                legend=True, 
                palette={'Successful': '#1f77b4', 'Failed': '#ff7f0e'}, 
                jitter=0.35
                )
    # sns.violinplot(x='Transactions', y='Fee per CU', data=df, cut=0, inner='box', hue='Transactions', legend=False, palette={'Success': '#1f77b4', 'Failed': '#ff7f0e'})
    # sns.violinplot(data=df, cut=0, scale='width', inner='box')
    plt.savefig(f'/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ1/output_fig/10_{cost_type}_strip1.png', facecolor='white', dpi=200)


def plot_distribution_fee():
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["solana"]
    failed_fee = mydb["tx_failed_rank"].aggregate([
        { "$match": { "$expr": { "$lt": [{"$rand": {}}, 0.5] } } },
        { "$project": { "fee": 1, "computeUnitsConsumed":1, "_id": 0 } },
        # { "$limit": 100000}
    ])
    failed_fee = list(failed_fee)
    success_fee = mydb["tx_success_rank"].aggregate([
        { "$match": { "$expr": { "$lt": [{"$rand": {}}, 0.5] } } },
        { "$project": { "fee": 1, "computeUnitsConsumed":1, "_id": 0 } },
        # { "$limit": 500000}
    ])
    success_fee = list(success_fee)

    # FILTER_NUM = 600000
    FILTER_NUM = 50
    df_failed_fee_per_cu = [x['fee']/x['computeUnitsConsumed'] if x['computeUnitsConsumed']!=0 else 0 for x in failed_fee] 
    print_statistics(df_failed_fee_per_cu, FILTER_NUM)
    df_success_fee_per_cu = [x['fee']/x['computeUnitsConsumed'] if x['computeUnitsConsumed']!=0 else 0 for x in success_fee]
    print_statistics(df_success_fee_per_cu, FILTER_NUM)
    print()
    cost_stripplot(df_success_fee_per_cu, df_failed_fee_per_cu, 'Fee per CU')

    # df_failed_rank = [value for value in df_failed_rank if value < FILTER_NUM]
    df_failed_cu = [x['computeUnitsConsumed'] for x in failed_fee]
    print_statistics(df_failed_cu, FILTER_NUM)
    df_success_cu = [x['computeUnitsConsumed'] for x in success_fee]
    print_statistics(df_success_cu, FILTER_NUM)
    print()
    cost_stripplot(df_success_cu, df_failed_cu, 'Compute Units')
    # df_failed_rank = [value for value in df_failed_rank if value < FILTER_NUM]

    df_failed_fee = [x['fee'] for x in failed_fee]
    print_statistics(df_failed_fee, FILTER_NUM)
    df_success_fee = [x['fee'] for x in success_fee]
    print_statistics(df_success_fee, FILTER_NUM)
    print()
    cost_stripplot(df_success_fee, df_failed_fee, 'Fee')
    

    print(len(df_failed_fee_per_cu), len(df_success_fee_per_cu))

    

def get_gas_per_cu_from_db(is_failed):
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["solana"]
    txs_table = mydb["txs"]
    # Aggregation pipeline
    pipeline = [
        {
            "$match": {
                "$and": [
                        { "error": { "$ne": None } } if is_failed else { "error": None },  # 匹配 error 为 None
                        { "$expr": { "$eq": [ { "$type": "$vote" }, "missing" ] } }  # 检查 vote 字段是否不存在
                    ]
            }
        },
        {
            "$project": {
                "_id": 0,  
                "block": 1,
                "blockTime": 1,
                "transactionHash":1,
                "computeUnitsConsumed": 1,
                "fee": 1,
                # "gas_per_cu": {
                #     "$cond": {
                #         "if": {"$gt": ["$computeUnitsConsumed", 0]},  # 如果 computeUnitsConsumed > 0
                #         "then": {"$divide": [{"$toInt": "$fee"}, {"$toInt": "$computeUnitsConsumed"}]},  # fee/computeUnitsConsumed
                #         "else": 0  # 否则为 0
                #     }
                # }
            }
        },
        {
            "$out": "tx_failed_gas_per_cu" if is_failed else "tx_success_gas_per_cu"
        }
    ]

    results = txs_table.aggregate(pipeline)
    cnt = 0
    for result in results:
        print(result)
        cnt += 1
        if cnt == 5:
            break

def get_rank_from_db(is_failed):
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["solana"]
    txs_table = mydb["txs_v2"]
    # Aggregation pipeline
    pipeline = [
        {
            "$match": {
                "$and": [
                        { "error": { "$ne": None } } if is_failed else { "error": None },  # 匹配 error 为 None
                        { "$expr": { "$eq": [ { "$type": "$vote" }, "missing" ] } }  # 检查 vote 字段是否不存在
                    ]
            }
        },
        {
            "$project": {
                "_id": 0,  
                "fee": 1,
                "computeUnitsConsumed": 1,
                # "gas_per_cu": {
                #     "$cond": {
                #         "if": {"$gt": ["$computeUnitsConsumed", 0]},  # 如果 computeUnitsConsumed > 0
                #         "then": {"$divide": [{"$toInt": "$fee"}, {"$toInt": "$computeUnitsConsumed"}]},  # fee/computeUnitsConsumed
                #         "else": 0  # 否则为 0
                #     }
                # },
                # "block": 1,
                # "blockTime": 1,
                "rank": 1,
                # "transactionHash":1,
            }
        },
        {
            "$out": "tx_failed_rank" if is_failed else "tx_success_rank"
        }
    ]

    results = txs_table.aggregate(pipeline)

    
def get_mann_whitney_test():
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["solana"]
    failed_rank = mydb["tx_failed_rank"].aggregate([
        { "$project": { "rank": 1, "_id": 0 } },
        { "$limit": 500000}
    ])
    df_failed_rank = [x['rank'] for x in failed_rank]
    success_rank = mydb["tx_success_rank"].aggregate([
        { "$project": { "rank": 1, "_id": 0 } },
        { "$limit": 400000}
    ])
    df_success_rank = [x['rank'] for x in success_rank]
    statistic, p_value = stats.mannwhitneyu(df_failed_rank, df_success_rank, alternative='two-sided')
    print(f"Statistic: {statistic}, p-value: {p_value}")

if __name__ == "__main__":
    # start_time = time.time()
    # asyncio.run(get_failed_fees())
    # end_time = time.time()
    # print(f"Run Time:{end_time-start_time}")
    # # plot_cdf_gas_per_cu()
    # plot_gas_per_cu()
    start_time = time.time()
    # print("Finish gas !")
    # get_rank_from_db(is_failed=True)
    # get_rank_from_db(is_failed=False)
    # plot_distribution_rank()

    # get_gas_per_cu_from_db(is_failed=True)
    # get_gas_per_cu_from_db(is_failed=False)
    # plot_distribution_fee()
    # get_mann_whitney_test()
    end_time = time.time()
    print(f"Run Time:{end_time-start_time}")