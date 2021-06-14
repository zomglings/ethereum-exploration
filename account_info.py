import argparse
import json
import os
import sqlite3

import web3

def connect(ipc_path):
    return web3.Web3(web3.Web3.IPCProvider(ipc_path))

def account_info(web3_client, db, account):
    current_balance = web3_client.eth.get_balance(account)

    cur = db.cursor()

    incoming_transactions_query = "SELECT hash, block_number, from_address, value, input FROM transactions WHERE to_address = ?"
    incoming_transactions_raw = cur.execute(incoming_transactions_query, [account]).fetchall()
    incoming_transactions = [
        {
            "hash": f"0x{tx_hash.hex()}",
            "block_number": block_number,
            "from": from_address,
            "to": account,
            "value": value,
            "input": input_data,
        }
        for tx_hash, block_number, from_address, value, input_data in incoming_transactions_raw
    ]

    outgoing_transactions_query = "SELECT hash, block_number, to_address, value, input FROM transactions WHERE from_address = ?"
    outgoing_transactions_raw = cur.execute(outgoing_transactions_query, [account]).fetchall()
    outgoing_transactions = [
        {
            "hash": f"0x{tx_hash.hex()}",
            "block_number": block_number,
            "from": account,
            "to": to_address,
            "value": value,
            "input": input_data,
        }
        for tx_hash, block_number, to_address, value, input_data in outgoing_transactions_raw
    ]

    return {
        "current_balance": current_balance,
        "incoming_transactions": incoming_transactions,
        "outgoing_transactions": outgoing_transactions,
    }

if __name__ == "__main__":
    default_ipc_path = os.path.expanduser("~/.ethereum/geth.ipc")

    parser = argparse.ArgumentParser(description="Get information about an Ethereum account")
    parser.add_argument("--ipc", default=default_ipc_path, help="Path to IPC socket that this script should use to connect to Ethereum node")
    parser.add_argument("--index", required=True, help="Path to SQLite database containing transaction index")
    parser.add_argument("account", help="Account to get information about")

    args = parser.parse_args()

    account = web3.Web3.toChecksumAddress(args.account)

    db = sqlite3.connect(args.index)
    web3_client = connect(args.ipc)

    try:
        result = account_info(web3_client, db, account)
        print(json.dumps(result))
    finally:
        db.close()