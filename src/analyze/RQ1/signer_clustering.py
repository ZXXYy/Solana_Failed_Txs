import time
import pymongo
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from tqdm import tqdm
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import MinMaxScaler

def knn_clustering(df_features):
    cluster_eval_res = {}
    scaler = MinMaxScaler()
    df_features = pd.DataFrame(scaler.fit_transform(df_features), columns=df_features.columns)
    for num_cluster in range(2, 3):
        kmeans = KMeans(n_clusters=num_cluster, random_state=42)
        kmeans.fit(df_features.values)
        y_kmeans = kmeans.predict(df_features.values)
        silhouette_avg = silhouette_score(df_features.values, y_kmeans)
        print(f"Silhouette Score: {silhouette_avg:.4f}")
        cluster_eval_res[num_cluster] = silhouette_avg

        # pca projection for visualization
        pca = PCA(n_components=2)
        X_pca = pca.fit_transform(df_features.values) 
        plt.scatter(X_pca[:, 0], X_pca[:, 1], c=y_kmeans, s=50, cmap='viridis')
        plt.savefig(f'src/analyze/RQ2/output_fig/1_{num_cluster}_signer_cluster.png')
    print(cluster_eval_res)
    return y_kmeans

if __name__ == "__main__":
    myclient = pymongo.MongoClient("mongodb://localhost:27017/")
    mydb = myclient["solana"]
    signer_features = mydb["signer_features"]

    start_time = time.time()
    df_features = pd.DataFrame(list(mydb["signer_features"].find()))
    df_features = df_features[df_features['total_blocks'] > 1]
    df_features = df_features.drop(columns=['label']) # drop signer column
    df_features = df_features.dropna()
    df_features_knn = df_features.drop(columns=['_id', 'signer', 'failed_txs_per_block', 'total_failed_txs', 'total_blocks', 'interval_mean', 'active_time']) # drop signer column
    # df_features_knn = pd.DataFrame(df_features["interval_variance", "txs_per_block", "total_txs"])
    print(df_features_knn.columns)
    print(df_features_knn)
    label = knn_clustering(df_features_knn)
    df_features['label'] = label
    print(df_features["label"].value_counts())
    # write label to mongodb
    df_features = df_features[["_id", "signer", "label"]]
    mydb["signer_labels"].drop()
    mydb["signer_labels"].insert_many(df_features.to_dict('records'))

    end_time = time.time()
    print(f"Run Time:{end_time-start_time}")

    # except Exception as e:
    #     print(f"Exception {e}")
    
    myclient.close()

    