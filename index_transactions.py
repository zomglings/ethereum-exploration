import argparse
from datetime import datetime
import os
import sqlite3

import web3

def connect(ipc_path):
    print("Connecting to node over IPC socket:", ipc_path)
    web3_client = web3.Web3(web3.Web3.IPCProvider(ipc_path))
    return web3_client

def init(db):
    cur = db.cursor()

    # All numbers are overestimates
    # Addresses - https://www.reddit.com/r/ethereum/comments/6l3da1/how_long_are_ethereum_addresses/
    # extra_data - https://ethereum.stackexchange.com/questions/16202/what-does-the-extradata-field-of-a-block-represent
    # logs_bloom - https://ethereum.stackexchange.com/questions/11523/how-to-decode-logsbloom/57445
    create_blocks_table = """
    CREATE TABLE IF NOT EXISTS blocks (
        block_number UNSIGNED BIG INT PRIMARY KEY,
        difficulty UNSIGNED BIG INT,
        extra_data VARCHAR(40),
        gas_limit UNSIGNED BIG INT,
        gas_used UNSIGNED BIG INT,
        hash VARCHAR(256),
        logs_bloom VARCHAR(1024),
        miner VARCHAR(256),
        nonce VARCHAR(256),
        parent_hash VARCHAR(256),
        receipt_root VARCHAR(256),
        uncles VARCHAR(256),
        size INTEGER,
        state_root VARCHAR(256),
        timestamp UNSIGNED BIG INT,
        total_difficulty UNSIGNED BIG INT,
        transactions_root VARCHAR(256),
        indexed_at DATETIME
    );"""
    cur.execute(create_blocks_table)
    
    create_transactions_table = """
    CREATE TABLE IF NOT EXISTS transactions (
        hash VARCHAR(256) PRIMARY KEY,
        block_number UNSIGNED BIG INT,
        from_address VARCHAR(256),
        to_address VARCHAR(256),
        gas TEXT,
        gas_price TEXT,
        input VARCHAR(256),
        nonce VARCHAR(256),
        transaction_index UNSIGNED INT,
        value TEXT,
        FOREIGN KEY(block_number) REFERENCES blocks(block_number)
    );"""
    cur.execute(create_transactions_table)
    db.commit()

def index_transactions(web3_client: web3.Web3, db, num_blocks=None):
    """
    Indexes transactions from the given web3 client for the given number of blocks beyond the 
    last block from which transactions were indexed.

    If num_blocks is None, it first gets the current block number from the web3_client and goes till there.
    """
    cur = db.cursor()
    last_indexed_block_query = "SELECT COALESCE(MAX(block_number), -1) FROM blocks;"
    last_indexed_block_rows = cur.execute(last_indexed_block_query).fetchall()
    if not last_indexed_block_rows:
        raise Exception("No rows returned for query on last indexed block")
    last_indexed_block_number = last_indexed_block_rows[0][0]

    current_block_number = web3_client.eth.block_number
    to_block_number = current_block_number
    if num_blocks is not None:
        to_block_number = min(last_indexed_block_number + num_blocks, current_block_number)
    
    print(f"Processing blocks: start={last_indexed_block_number+1}, end={to_block_number}")

    try:    
        for block_number in range(last_indexed_block_number + 1, to_block_number + 1):
            print(f"\tIndexing transactions from block: {block_number}...")
            block = web3_client.eth.get_block(block_number, full_transactions=True)
            insert_block_query = "INSERT INTO blocks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            cur.execute(
                insert_block_query,
                (
                    block.number,
                    block.difficulty,
                    block.extraData,
                    block.gasLimit,
                    block.gasUsed,
                    block.hash,
                    block.logsBloom,
                    block.miner,
                    block.nonce,
                    block.parentHash,
                    block.get("receiptRoot", ""),
                    block.sha3Uncles,
                    block.size,
                    block.stateRoot,
                    block.timestamp,
                    block.totalDifficulty,
                    block.transactionsRoot,
                    datetime.utcnow().timestamp()
                ),
            )

            insert_transaction_query = "INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            transaction_tuples = [
                (
                    transaction.hash,
                    block.number,
                    transaction["from"],
                    transaction.to,
                    str(transaction.gas),
                    str(transaction.gasPrice),
                    transaction.input,
                    transaction.nonce,
                    transaction.transactionIndex,
                    str(transaction.value),
                )
                for transaction in block.transactions
            ]
            try:
                cur.executemany(insert_transaction_query, transaction_tuples)
            except:
                print(transaction_tuples)
                raise
            db.commit()
    except Exception:
        db.rollback()
        raise
    
if __name__ == "__main__":
    default_ipc_path = os.path.expanduser("~/.ethereum/geth.ipc")

    parser = argparse.ArgumentParser(description="Get information about an Ethereum account")
    parser.add_argument("--ipc", default=default_ipc_path, help="Path to IPC socket that this script should use to connect to Ethereum node")
    parser.add_argument("--init", action="store_true", help="Set this flag to initialize the database (create tables, etc.)")
    parser.add_argument("index_db", help="Path to SQLite databse containing transaction index")

    args = parser.parse_args()

    web3_client = connect(args.ipc)
    db = sqlite3.connect(args.index_db)

    try:
        if args.init:
            init(db)
        else:
            index_transactions(web3_client, db)
    finally:
        db.close()