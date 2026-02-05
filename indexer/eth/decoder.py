"""Event log decoder."""

import json
from typing import Any, Dict, Optional

from web3 import Web3
from web3.types import LogReceipt

from eth.abi_loader import get_campaign_abi, get_factory_abi
from log import get_logger

logger = get_logger(__name__)

# Contract instances for decoding
_factory_contract = None
_campaign_contract = None


def _get_factory_contract() -> Any:
    """Get Web3 contract instance for Factory.

    Returns:
        Web3 contract instance
    """
    global _factory_contract
    if _factory_contract is None:
        abi = get_factory_abi()
        _factory_contract = Web3().eth.contract(abi=abi)
    return _factory_contract


def _get_campaign_contract() -> Any:
    """Get Web3 contract instance for Campaign.

    Returns:
        Web3 contract instance
    """
    global _campaign_contract
    if _campaign_contract is None:
        abi = get_campaign_abi()
        _campaign_contract = Web3().eth.contract(abi=abi)
    return _campaign_contract


def decode_event(log: LogReceipt, contract_type: str = "campaign") -> Optional[Dict[str, Any]]:
    """Decode a log receipt into structured event data.

    Args:
        log: Raw log receipt from get_logs
        contract_type: "factory" or "campaign"

    Returns:
        Decoded event data with keys:
        - event_name: Name of the event
        - args: Dictionary of decoded parameters
        - block_number: Block number
        - tx_hash: Transaction hash
        - log_index: Log index
        - address: Contract address
        None if decoding fails
    """
    try:
        if contract_type == "factory":
            contract = _get_factory_contract()
        elif contract_type == "campaign":
            contract = _get_campaign_contract()
        else:
            logger.error(f"Unknown contract type: {contract_type}")
            return None

        # Try to decode with each event in the contract
        # The first topic is the event signature hash
        event_topic = log["topics"][0].hex() if log["topics"] else None
        if not event_topic:
            return None

        # Find matching event by topic
        for event_abi in contract.abi:
            if event_abi.get("type") == "event":
                # Compute event signature
                event_name = event_abi["name"]
                inputs = event_abi.get("inputs", [])
                input_types = [inp["type"] for inp in inputs]
                signature = f"{event_name}({','.join(input_types)})"
                computed_topic = Web3.keccak(text=signature).hex()
                
                if computed_topic.lower() == event_topic.lower():
                    # Found matching event, decode it
                    try:
                        event_handler = getattr(contract.events, event_name)
                        decoded = event_handler().process_log(log)
                        
                        return {
                            "event_name": decoded["event"],
                            "args": dict(decoded["args"]),
                            "block_number": log["blockNumber"],
                            "tx_hash": log["transactionHash"].hex(),
                            "log_index": log["logIndex"],
                            "address": log["address"],
                        }
                    except Exception as decode_error:
                        logger.debug(f"Error decoding {event_name}: {decode_error}")
                        continue

        # Event not found
        logger.debug(f"Event not found in {contract_type} ABI for topic {event_topic}")
        return None

    except Exception as e:
        logger.warning(f"Failed to decode event: {e}")
        return None


def decode_factory_event(log: LogReceipt) -> Optional[Dict[str, Any]]:
    """Decode a Factory contract event.

    Args:
        log: Raw log receipt

    Returns:
        Decoded event data or None
    """
    return decode_event(log, contract_type="factory")


def decode_campaign_event(log: LogReceipt) -> Optional[Dict[str, Any]]:
    """Decode a Campaign contract event.

    Args:
        log: Raw log receipt

    Returns:
        Decoded event data or None
    """
    return decode_event(log, contract_type="campaign")


def event_data_to_json(event_data: Dict[str, Any]) -> str:
    """Convert event data dictionary to JSON string.

    Args:
        event_data: Decoded event data

    Returns:
        JSON string representation
    """
    # Convert any non-serializable types
    serializable = {}
    for key, value in event_data.items():
        if isinstance(value, (str, int, bool, type(None))):
            serializable[key] = value
        elif hasattr(value, "hex"):  # HexBytes
            serializable[key] = value.hex()
        else:
            serializable[key] = str(value)
    
    return json.dumps(serializable)

