import argparse
import json
import os
import time
import uuid

import web3

from humbug.consent import HumbugConsent
from humbug.report import HumbugReporter, Report
from web3.types import GasPriceStrategy


def connect(ipc_path):
    print("Connecting to node over IPC socket:", ipc_path)
    web3_client = web3.Web3(web3.Web3.IPCProvider(ipc_path))
    return web3_client


def publish_pending_transaction(reporter, pending_transaction):
    """
    Returns an ordered pair of the form:
    ("<content>", [..., "<tags>", ...])
    """
    pending_transaction_hash = pending_transaction.hash.hex()
    pending_transaction_dict = {
        "to": pending_transaction.to,
        "from": pending_transaction["from"],
        "gas": pending_transaction.gas,
        "gasPrice": pending_transaction.gasPrice,
        "hash": pending_transaction_hash,
        "value": pending_transaction.value,
        "input": pending_transaction.input,
    }

    content = f"```\n{json.dumps(pending_transaction_dict, indent=4)}\n```"

    tags = reporter.system_tags() + [
        f"from:{pending_transaction['from']}",
        f"to:{pending_transaction.to}",
        f"tx_hash:{pending_transaction_hash}",
    ]

    report = Report(
        title=f"Pending transaction: {pending_transaction_hash}",
        content=content,
        tags=tags,
    )

    reporter.publish(report)


if __name__ == "__main__":
    default_ipc_path = os.path.expanduser("~/.ethereum/geth.ipc")
    parser = argparse.ArgumentParser(
        description="Set up a transaction pool reporter against an Ethereum node"
    )
    parser.add_argument(
        "--ipc",
        default=default_ipc_path,
        help="Path to IPC socket that this script should use to connect to Ethereum node",
    )
    parser.add_argument(
        "client_id",
        help="Client ID for transaction pool reporter - used when sending reports to Bugout",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=30.0,
        help="Seconds to wait between queries for pending transactions (default: 30)",
    )

    args = parser.parse_args()

    web3_client = connect(args.ipc)

    network_id = web3_client.net.version
    node_info = web3_client.geth.admin.node_info()
    node_id = node_info.get("id")

    session_id = str(uuid.uuid4())
    reporter_token = "5228dd08-bfb5-4bbf-9666-49b7d483d3d4"

    reporter_tags = [f"network:{network_id}"]
    if node_id is not None:
        reporter_tags.append(f"node:{node_id}")

    consent = HumbugConsent(True)
    reporter = HumbugReporter(
        name="txpool_reports",
        consent=consent,
        client_id=args.client_id,
        session_id=session_id,
        bugout_token=reporter_token,
        tags=reporter_tags,
    )

    reporter.system_report()

    pending_transactions_filter = web3_client.eth.filter("pending")

    while True:
        pending_transactions = web3_client.eth.get_filter_changes(
            pending_transactions_filter.filter_id
        )
        for pending_transaction_hash in pending_transactions:
            print(f"Processing pending transaction: {pending_transaction_hash.hex()}")
            pending_transaction = web3_client.eth.get_transaction(
                pending_transaction_hash
            )
            publish_pending_transaction(reporter, pending_transaction)
        time.sleep(args.interval)
