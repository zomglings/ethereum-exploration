import argparse
import os
from eth_utils.address import to_checksum_address

import vyper
from vyper.compiler import compile_code
import web3


def connect(ipc_path):
    print("Connecting to node over IPC socket:", ipc_path)
    web3_client = web3.Web3(web3.Web3.IPCProvider(ipc_path))
    return web3_client


def compile(vyper_file_path):
    """
    Accepts path to a Vyper file. Returns a dcitionary of the form:
    {
        "abi": [<smart contract abi>],
        "bytecode": "<smart contract bytecode>"
    }
    """
    with open(vyper_file_path, "r") as ifp:
        source_code = ifp.read()
    return vyper.compile_code(source_code, ["abi", "bytecode"])


def estimate_gas(web3_client, compiled_contract, beneficiary, start_time, end_time):
    """
    Accepts:
        web3_client - to be used for deployment
        compiled_contract - as in output of "compile"
        beneficiary - checksum address which will be the beneficiary of the auction
        start_time - time at which auction starts/started
        end_time - time at which auction will end

    Estimates the gas required to deploy the contract to the blockchain represented by the given web3_client.
    """
    contract = web3_client.eth.contract(
        abi=compiled_contract["abi"], bytecode=compiled_contract["bytecode"]
    )
    return contract.constructor(beneficiary, start_time, end_time).estimateGas()


def deploy(
    web3_client,
    compiled_contract,
    beneficiary,
    start_time,
    end_time,
    deploying_address,
    gas,
):
    """
    Accepts:
        web3_client - to be used for deployment
        compiled_contract - as in output of "compile"
        beneficiary - checksum address which will be the beneficiary of the auction
        start_time - time at which auction starts/started
        end_time - time at which auction will end
        deploying_address - address which is deploying the contract
        gas - amount of fees to pay as gas

    Deploys the contract to the blockchain represented by the given web3_client and returns the transaction hash for
    the deployment transaction.
    """
    transaction = {
        "from": deploying_address,
        "gas": gas,
    }
    contract = web3_client.eth.contract(
        abi=compiled_contract["abi"], bytecode=compiled_contract["bytecode"]
    )
    return contract.constructor(beneficiary, start_time, end_time).transact(transaction)


if __name__ == "__main__":
    default_ipc_path = os.path.expanduser("~/.ethereum/geth.ipc")

    default_auction_contract = os.path.join(os.path.dirname(__file__), "auction.vy")

    parser = argparse.ArgumentParser(
        description="Get information about an Ethereum account"
    )
    parser.add_argument(
        "--ipc",
        default=default_ipc_path,
        help="Path to IPC socket that this script should use to connect to Ethereum node",
    )
    parser.add_argument(
        "-a",
        "--account",
        type=web3.Web3.toChecksumAddress,
        default=None,
        help="Account which will deploy the smart contract",
    )
    parser.add_argument(
        "--contract",
        required=(not os.path.isfile(default_auction_contract)),
        default=default_auction_contract,
        help="Path to Vyper file containing smart contract to deploy",
    )
    parser.add_argument(
        "beneficiary",
        type=web3.Web3.toChecksumAddress,
        help="Beneficiary of the auction",
    )
    parser.add_argument("start_time", type=int, help="Time at which auction started")
    parser.add_argument("end_time", type=int, help="Time at which auction will end")
    parser.add_argument(
        "--gas",
        type=str,
        default=None,
        help="Gas to send with transaction - leave as None to get a gas estimate",
    )

    args = parser.parse_args()

    web3_client = connect(args.ipc)

    compiled_contract = compile(args.contract)

    if args.gas is None:
        gas_estimate = estimate_gas(
            web3_client,
            compiled_contract,
            args.beneficiary,
            args.start_time,
            args.end_time,
        )
        print(f"Estimated gas required: {gas_estimate}")
    elif args.account is None:
        raise ValueError("Please specify a --account which will deploy this contract")
    else:
        tx_hash_raw = deploy(
            web3_client,
            compiled_contract,
            args.beneficiary,
            args.start_time,
            args.end_time,
            args.account,
            args.gas,
        )
        tx_receipt = web3_client.eth.wait_for_transaction_receipt(tx_hash_raw)
        contract_address = tx_receipt.contractAddress
        tx_hash = tx_hash_raw.hex()
        print(f"Contract deployed in transaction: {tx_hash}")
        print(f"Contract address: {contract_address}")
