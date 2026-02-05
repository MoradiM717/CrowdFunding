"""ABI file loader."""

import json
import os
from pathlib import Path
from typing import Any, Dict

from log import get_logger

logger = get_logger(__name__)

# ABI directory relative to this file
ABI_DIR = Path(__file__).parent.parent / "abi"


def load_abi(contract_name: str) -> list[Dict[str, Any]]:
    """Load ABI from JSON file.

    Args:
        contract_name: Contract name (e.g., "CampaignFactory" or "Campaign")

    Returns:
        ABI as list of dictionaries

    Raises:
        FileNotFoundError: If ABI file doesn't exist
        ValueError: If ABI file is invalid JSON
    """
    abi_path = ABI_DIR / f"{contract_name}.json"
    
    if not abi_path.exists():
        raise FileNotFoundError(
            f"ABI file not found: {abi_path}. "
            f"Expected file at: {abi_path.absolute()}"
        )

    try:
        with open(abi_path, "r") as f:
            abi = json.load(f)
        
        if not isinstance(abi, list):
            raise ValueError(f"ABI must be a list, got {type(abi)}")
        
        logger.debug(f"Loaded ABI for {contract_name} ({len(abi)} entries)")
        return abi

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in ABI file {abi_path}: {e}") from e


def get_factory_abi() -> list[Dict[str, Any]]:
    """Get CampaignFactory ABI.

    Returns:
        CampaignFactory ABI
    """
    return load_abi("CampaignFactory")


def get_campaign_abi() -> list[Dict[str, Any]]:
    """Get Campaign ABI.

    Returns:
        Campaign ABI
    """
    return load_abi("Campaign")

