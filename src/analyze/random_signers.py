import json
import pymongo

# randomly select signers from the list of signers
def get_signers():
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
            }
        }, 
        {
            "$sample": { "size": 43 }
        }
    ]
    signers = [res for res in signer_labels.aggregate(pipeline)]
    print(signers)
    json.dump(signers, open("/data0/xiaoyez/Solana_Ecosystem/src/analyze/manual_signers.json", "w"))
    return signers

if __name__ == "__main__":
    get_signers()