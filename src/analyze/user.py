import re
import time
import json
import logging
import matplotlib.pyplot as plt
from collections import defaultdict

from deprecated.analyze.handleFailedLog import handle_failed_tx_logs, process_failed_tx_file

# Set up logging
logging.basicConfig(level=logging.INFO, format='[%(filename)s:%(lineno)d] - %(message)s')
logger = logging.getLogger(__name__)

def get_user_logs():
    with open('signer.json') as f:
        signers = json.load(f)

    users = {k:v for k,v in signers.items() if v['count'] <= 100 and v['is_vote'] == False}
    user_ids = list(users.keys())
    print(len(user_ids))

    # get the bots' failed logs
    logs = handle_failed_tx_logs("./data/failed_transactions_blockid", outname="user_inspect", filtered_signers=user_ids)
    logs = {k: v for k, v in sorted(logs.items(), key=lambda item: item[1])}
    with open("user_inspect.log", 'w') as f:
        for log, cnt in logs.items():
            f.write(f"{cnt}=={log}\n")

def handle_corner_cases(inst_error):
    return inst_error

def get_cnt_sum(items):
    return sum([int(item[0]) for item in items])

def hanlde_user_logs():
    logs = defaultdict(list)
    with open('user_inspect.log') as f:
        lines = f.readlines()
        # 136430==9uW2TqLyfYyrcNVrgCy4jPpqDKQoBZhXWypzzFxbixQE: Instruction: PepperRaydiumSwapOnceV3
        for line in lines:
            if '==' not in line or 'assertion `left == right` failed' in line:
                continue
            cnt = line.split('==')[0]
            log = line.split('==')[1]
            program = log.split(':')[0]
            inst_error = log[log.find(': ')+len(': '):]
            inst_error = handle_corner_cases(inst_error)
            logs[inst_error].append([cnt, program])

    sorted_logs = {k: v for k, v in sorted(logs.items(), key=lambda item: get_cnt_sum(item[1]), reverse=True)}

    with open('user_error.json', 'w') as f:
        json.dump(sorted_logs, f)
    print(f"error types: {len(sorted_logs)}")


def plot_error_log_distribution():
    with open('user_error.json') as f:
        logs = json.load(f)
        logs = {k: get_cnt_sum(v) for k, v in logs.items() if get_cnt_sum(v) > 1000}
        print(len(logs))
        # plot error log pie chart
        fig, ax = plt.subplots(figsize=(10, 10))
        ax.pie(logs.values(), labels=logs.keys(), autopct='%1.1f%%', startangle=90)
        ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
        plt.savefig('src/user_error_pie.png')

# get_user_logs()
# hanlde_user_logs()
plot_error_log_distribution()