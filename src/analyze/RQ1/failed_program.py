import time
import pymongo
import traceback
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def get_failed_program_cnt_from_db():
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["solana"]
    txs_table = mydb["txs_v2"]
    txs_table.create_index([("failedInstruction.program", pymongo.ASCENDING)])
    
    # # First, get all unique program IDs
    # program_ids = txs_table.distinct("failedInstruction.program", {
    #     "error": { "$ne": None },
    #     "vote": { "$exists": False },
    #     "limit": 10
    # })
    pipeline = [
        {"$match": {"error": {"$ne": None}, "vote": {"$exists": False}}},
        {"$project": {"_id":0, "program": "$failedInstruction.program", "signer": "$signer"}},
        {
            "$addFields": {
                "is_failed": True
            }
        },
        {"$out": "program_signer"}
    ]
    txs_table.aggregate(pipeline, allowDiskUse=True)
    mydb['program_signer'].create_index([("program")])
    myclient.close()

def get_success_tx_called_programs():
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["solana"]
    txs_table = mydb["txs_v2"]
    pipeline = [
        {
         "$match": {
                "$and": [
                        { "error": { "$eq": None } },  # 匹配 error 为 None
                        { "$expr": { "$eq": [ { "$type": "$vote" }, "missing" ] } }  # 检查 vote 字段是否不存在
                    ]
            }
        },
        {
            "$project": {
                "transactionHash": 1,
                "programIds": {
                    "$setUnion":{
                        "$map": {
                            "input": "$successInstructions.instructions",
                            "as": "inst",
                            "in": {
                                "$arrayElemAt": [
                                    "$successInstructions.accounts",
                                    "$$inst.programIdIndex"
                                ]
                            }
                        }
                    }
                },
                "signer": 1
            }
        },
        # {
        #     "$limit": 100
        # },
        {
            "$out": "success_program"
        }
    ]
    results = txs_table.aggregate(pipeline, allowDiskUse=True)
    for result in results:
        print(result)
    myclient.close()

def get_active_success_signers_for_program(program_id):
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["solana"]
    success_program = mydb["success_program"]
    success_program.create_index([("programIds", pymongo.ASCENDING)])
    pipeline = [
        {
            "$match": {
                "programIds":  program_id
            }
        },
        {
            "$project": {
                "signer": "$signer",
                "program": program_id
            }
        },
    ]
    results = success_program.aggregate(pipeline, allowDiskUse=True)
    for result in results:
        # active_signers.append(result["signer"])
        mydb['program_signer'].insert({
            "program": result["program"],
            "signer": result["signer"],
            "is_failed": False
        })

def set_signers4programs():
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["solana"]
    failed_program_cnt = mydb["program_signer"]
    pipeline = [
        {   
            "$match": {
                "is_failed":  True
            },
        },
        {
            "$project": {
                "_id": 0,
                "program": 1,
            }
        }
    ]
    results = list(failed_program_cnt.aggregate(pipeline))
    for result in results:
        program_id = result["program"]
        get_active_success_signers_for_program(program_id)
    myclient.close()

def top_failed_programs():
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["solana"]
    program_signer = mydb["program_signer"]
    pipeline = [
        {
            "$group": {
                "_id": "$program",
                "count": { "$sum": 1 },
                "num_failed_signers": { 
                    "$addToSet": {
                        "$cond": { "if": "$is_failed", "then": "$signer", "else": None }
                    } 
                },
                "num_success_signers": { 
                    "$addToSet": {
                        "$cond": { "if": "$is_failed", "then": None, "else": "$signer" }
                    } 
                },
                "num_total_signers": {
                    "$addToSet": "$signer"
                }
            }
        },
        {
            "$project": {
                "_id":1,
                "count": 1,
                "num_failed_signers": { "$size": { "$setDifference": ["$num_failed_signers", [None]] } },
                "num_success_signers": { "$size": { "$setDifference": ["$num_success_signers", [None]] } },
                "num_total_signers": { "$size": "$num_total_signers" }
            }
        },
        {
            "$sort": {
                "count": -1
            }
        },
        {
            "$limit": 10
        }
    ]
    results = program_signer.aggregate(pipeline, allowDiskUse=True)
    for result in results:
        print(result)
    myclient.close()

def get_top_failed_programs():
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["solana"]
    program_signer = mydb["program_signer"]
    pipeline = [
        {
            "$group": {
                "_id": "$program",
                "count": { "$sum": 1 },
                "failed_signers": { 
                    "$addToSet": "$signer" 
                },
            }
        },
        {
            "$project": {
                "program": "$_id",
                "count": 1,
                "failed_unique_signer_count": { "$size": "$failed_signers" }
            }
        },
        {
            "$sort": {
                "count": -1
            }
        }
    ]
    results = program_signer.aggregate(pipeline, allowDiskUse=True)
    i = 0
    program_counts = []
    top_programs =  {}
    for result in results:
        if i < 20:
            print(result)
            print(f"Failed signers: {result['failed_unique_signer_count']}")
            top_programs[result["program"]] = result["count"]
        i = i+1
        program_counts.append(result["count"])
    print(f"len: {len(program_counts)}")
    print(f"Min: {min(program_counts)}")
    print(f"Max: {max(program_counts)}")
    print(f"Median: {np.median(program_counts)}")
    print(f"Average: {np.mean(program_counts)}")
    return program_counts, top_programs

def plot_failed_cdf(programs):
    programs_cdfx = np.sort(programs)
    programs_cdfy = np.linspace(1 / len(programs), 1.0, len(programs))  

    # human_cdfx = np.sort(human_failed_counts) 
    # huamn_cdfy = np.linspace(1 / len(human_failed_counts), 1.0, len(human_failed_counts))  

    plt.figure(figsize=(8, 6))
    plt.semilogx(programs_cdfx, programs_cdfy, 'o', color='blue', 
                 markersize=4,      # Size of dots
                 alpha=0.5,         # Transparency
                 rasterized=True)   # Better performance for many points
    # plt.plot(human_cdfx, huamn_cdfy, color='orangered', label='Human Failed #Txs')

    # 添加标题和标签
    plt.title(f'CDF of Failed #Txs')
    plt.ylabel('CDF')
    plt.grid(True, which='both', axis='y', linestyle='--', alpha=0.7) 
    # label size
    ax = plt.gca()
    ax.tick_params(labelsize=25)
    ax.yaxis.label.set_size(18)
    ax.title.set_size(20)
    plt.grid(True, linestyle='--', which="major")
    plt.savefig(f'src/analyze/RQ1/output_fig/9_failed_program_cdf.png', dpi=300) 

def get_top_program_success_tx_cnt(top_program_id):
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["solana"]
    txs_table = mydb["success_program"]
    pipeline = [
        {
            "$match": {
               "programIds":  top_program_id  # Match if top_program_id exists in programIds array
            }
        },
        {
            "$count": "success_cnt"
        }
    ]
    results = txs_table.aggregate(pipeline)
    success_cnt = None
    for result in results:
        print(f"Success tx count for program {top_program_id}: {result['success_cnt']}")
        success_cnt = result['success_cnt']
    myclient.close()
    return success_cnt

if __name__ == "__main__":
    start_time = time.time()
    programs, top_programs = get_top_failed_programs()
    plot_failed_cdf(programs)
    print(f"Run Time:{time.time()-start_time}")
    cnt = []
    for program_id, failed_cnt in top_programs.items():
        success_cnt = get_top_program_success_tx_cnt(program_id)
        cnt.append({
            "program_id": program_id,
            "failed_cnt": failed_cnt,
            "success_cnt": success_cnt,
            "failed_ratio": failed_cnt/(failed_cnt+success_cnt),
            "percentage": failed_cnt/801017921
        })
    for c in cnt:
        print(c)
    # get_failed_program_cnt_from_db() # step1
    # get_success_tx_called_programs() # step2
    # set_signers4programs() # step3
    # top_failed_programs() # step4
    # signers = ['ANNiExyBjQ2iAViUbSFTvwWBvvVqQsE77QdAb4qxfTQj', 'BEmUSjqs7mpgaSXw6QdrePfTsD8aQHbdtnqUxa63La6E']
    # failed_program = ['675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8', '4ngnN8dA9sAf1sbz3m6qwquxbHkyzgXVpeTYcxKPtZuf']
    # for program_id in failed_program:
    #     active_signers = get_active_signers_for_failed_program(program_id)
    #     print(f"Active signers for failed program {program_id}: {active_signers}")
    end_time = time.time()
    print(f"Run Time:{end_time-start_time}")