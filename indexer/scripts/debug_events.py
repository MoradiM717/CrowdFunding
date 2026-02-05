#!/usr/bin/env python3
"""Debug script to directly query blockchain for events."""

import sys
sys.path.insert(0, '/Users/mostafamoradi/Desktop/work/crowdfunding/indexer')

from web3 import Web3

# Connect to Hardhat
w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))
print(f"Connected: {w3.is_connected()}")
print(f"Latest block: {w3.eth.block_number}")

# Factory address
FACTORY_ADDRESS = "0x5FbDB2315678afecb367f032d93F642f64180aa3"

# Compute CampaignCreated topic
signature = "CampaignCreated(address,address,address,uint256,uint256,string)"
topic = Web3.keccak(text=signature)
topic_hex = '0x' + topic.hex() if not topic.hex().startswith('0x') else topic.hex()
print(f"\nCampaignCreated topic: {topic_hex}")

# Get ALL logs from block 0 to latest (no filtering by topic)
print(f"\n--- Fetching ALL logs from Factory contract ---")
try:
    all_logs = w3.eth.get_logs({
        "fromBlock": 0,
        "toBlock": "latest",
        "address": Web3.to_checksum_address(FACTORY_ADDRESS),
    })
    print(f"Total logs from Factory: {len(all_logs)}")
    for i, log in enumerate(all_logs):
        print(f"\nLog {i+1}:")
        print(f"  Block: {log['blockNumber']}")
        print(f"  TX: {log['transactionHash'].hex()}")
        print(f"  Topics[0]: {log['topics'][0].hex() if log['topics'] else 'N/A'}")
        print(f"  Data length: {len(log['data'])} bytes")
except Exception as e:
    print(f"Error: {e}")

# Now try with topic filter
print(f"\n--- Fetching logs with CampaignCreated topic filter ---")
try:
    filtered_logs = w3.eth.get_logs({
        "fromBlock": 0,
        "toBlock": "latest",
        "address": Web3.to_checksum_address(FACTORY_ADDRESS),
        "topics": [topic_hex],
    })
    print(f"Filtered logs: {len(filtered_logs)}")
    for i, log in enumerate(filtered_logs):
        print(f"\nFiltered Log {i+1}:")
        print(f"  Block: {log['blockNumber']}")
        print(f"  TX: {log['transactionHash'].hex()}")
except Exception as e:
    print(f"Error: {e}")

# Also check for ANY events on ANY address
print(f"\n--- Fetching ALL logs from ALL addresses (last 20 blocks) ---")
latest = w3.eth.block_number
from_block = max(0, latest - 20)
try:
    all_events = w3.eth.get_logs({
        "fromBlock": from_block,
        "toBlock": "latest",
    })
    print(f"Total events in blocks {from_block}-{latest}: {len(all_events)}")
    for i, log in enumerate(all_events[:10]):  # Show first 10
        print(f"\nEvent {i+1}:")
        print(f"  Address: {log['address']}")
        print(f"  Block: {log['blockNumber']}")
        print(f"  Topics[0]: {log['topics'][0].hex() if log['topics'] else 'N/A'}")
except Exception as e:
    print(f"Error: {e}")
