import pymongo
import numpy as np
import matplotlib.pyplot as plt

def get_failed_txs_for_bot_or_human():
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["solana"]
    signer_labels = mydb["signer_labels"]
    pipeline = [
        {
            "$lookup": {
                "from": "signer_cnt",
                "localField": "signer",
                "foreignField": "_id",
                "as": "signer_cnt"
            }
        },
        {
            "$unwind": "$signer_cnt"
        },
        {
            "$project": {
                "_id": 0,
                "label": 1,
                "signer": 1,
                "failed_count": "$signer_cnt.failed_count",
                "success_count": "$signer_cnt.success_count",

            }
        }, 
        {
            "$group": {
                "_id": "$label",
                "failed_count": {
                    "$sum": "$failed_count"
                },
                "success_count": {
                    "$sum": "$success_count"
                },
                "count": {
                    "$sum": 1
                }
            }
        }
    ]
    results = signer_labels.aggregate(pipeline)
    for result in results:
        print(result)

def get_top_failed_signers(is_bot):
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["solana"]
    signer_labels = mydb["signer_labels"]
    pipeline = [
        {
            "$lookup": {
                "from": "signer_cnt",
                "localField": "signer",
                "foreignField": "_id",
                "as": "signer_cnt"
            }
        },
        {
            "$unwind": "$signer_cnt"
        },
        {
            "$project": {
                "_id": 0,
                "label": 1,
                "signer": 1,
                "failed_count": "$signer_cnt.failed_count",
                "success_count": "$signer_cnt.success_count",
                "failed_ratio": "$signer_cnt.failed_ratio"
            }
        }, 
        {
            '$match': {
                "label": 0 if is_bot else 1
            },
        },
        {
            "$sort": {
                "failed_count": -1,
                "failed_ratio": -1,
            }
        },
        
    ]
    results = signer_labels.aggregate(pipeline)
    failed_count = []
    success_count = []
    top_10_failure_account = []
    i = 0
    for result in results:
        # print(result)
        failed_count.append(result['failed_count'])
        success_count.append(result['success_count'])
        if i < 10:
            top_10_failure_account.append(result)
        i += 1

    print(f"Total failed: {sum(failed_count)}")
    print(f"Total success: {sum(success_count)}")

    return failed_count, success_count, top_10_failure_account

def plot_failed_cdf(failed, success, is_bot):
    failed_cdfx = np.sort(failed)
    failed_cdfy = np.linspace(1 / len(failed), 1.0, len(failed))  

    success_cdfx = np.sort(success) 
    success_cdfy = np.linspace(1 / len(success), 1.0, len(success))  

    plt.figure(figsize=(8, 6))
    plt.semilogx(failed_cdfx, failed_cdfy, 'o', color='orangered', 
                 markersize=4,      # Size of dots
                 alpha=0.5,         # Transparency
                 rasterized=True,
                 label='Failed Txs')   # Better performance for many points
    plt.semilogx(success_cdfx, success_cdfy, 'o', color='lightgreen', 
                 markersize=4,      # Size of dots
                 alpha=0.5,         # Transparency
                 rasterized=True,
                 label='Successful Txs')   # Better performance for many points
    # plt.plot(human_cdfx, huamn_cdfy, color='orangered', label='Human Failed #Txs')

    # 添加标题和标签
    plt.title(f'CDF of #Txs By {"Bot" if is_bot else "Human"}')
    plt.ylabel('CDF')
    plt.grid(True, which='both', axis='y', linestyle='--', alpha=0.7) 
    plt.legend(['Success', 'Failed'])
    # label size
    ax = plt.gca()
    ax.tick_params(labelsize=25)
    ax.yaxis.label.set_size(20)
    ax.title.set_size(20)
    plt.grid(True, linestyle='--', which="major")
    plt.savefig(f'/data0/xiaoyez/Solana_Ecosystem/src/analyze/RQ1/output_fig/3_{"Bot" if is_bot else "Human"}_failed_count_cdf.png', dpi=300) 

if __name__ == "__main__":
    # get_failed_txs_for_bot_or_human()
    bot_failed, bot_success, _ = get_top_failed_signers(is_bot=True)
    plot_failed_cdf(bot_failed, bot_success, is_bot=True)

    human_failed, human_success, _ = get_top_failed_signers(is_bot=False)
    plot_failed_cdf(human_failed, human_success, is_bot=False)
