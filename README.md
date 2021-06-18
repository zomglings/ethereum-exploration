We built these scripts as part of a Twitch stream: https://www.twitch.tv/videos/1055600601

### Setup

You will have to prepare a Python environment to run these scripts.

First, if you want to use a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

Then, to install dependencies:
```bash
pip install -r requirements.txt
```

### `index_transactions.py`

This script builds an index of all the transactions on an Ethereum network. This index is stored as a SQLite database.

If you are already running an Ethereum node, you can build this index as follows:

```bash
# Create tables in SQLite database
python index_transactions.py --ipc <path to geth data directory>/geth.ipc --init <path to db file>

# Index transactions
python index_transactions.py --ipc <path to geth data directory>/geth.ipc <path to db file>
```

The invocations we used on stream:
```bash
python index_transactions.py --ipc "$PWD/data/geth.ipc" --init lol.db
python index_transactions.py --ipc "$PWD/data/geth.ipc" lol.db
```

### `account_info.py`

This script looks up information about an address on the blockchain and in a prepared transaction index (as
created by the `index_transactions.py` script).

To run it:
```bash
python account_info.py --ipc <path to geth data directory>/geth.ipc --index <path to db file> <account address>
```

The invocation we used on stream:
```bash
python account_info.py --ipc "$PWD/data/geth.ipc" --index lol.db "0x2e337e0fb68f5e51ce9295e80bcd02273d7420c4"
```

