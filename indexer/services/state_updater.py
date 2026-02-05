"""State update service - applies event-driven state changes to database."""

from typing import Dict, Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db.models import Campaign, Contribution, Event
from eth.decoder import event_data_to_json
from log import get_logger

logger = get_logger(__name__)


def insert_event(
    session: Session,
    chain_id: int,
    tx_hash: str,
    log_index: int,
    block_number: int,
    block_hash: str,
    address: str,
    event_name: str,
    event_data: Dict[str, Any],
) -> bool:
    """Insert event into database (idempotent).

    Args:
        session: Database session
        chain_id: Chain ID
        tx_hash: Transaction hash
        log_index: Log index
        block_number: Block number
        block_hash: Block hash
        address: Contract address
        event_name: Event name
        event_data: Decoded event data

    Returns:
        True if event was inserted, False if it already existed (idempotent)
    """
    try:
        event = Event(
            chain_id=chain_id,
            tx_hash=tx_hash,
            log_index=log_index,
            block_number=block_number,
            block_hash=block_hash,
            address=address,
            event_name=event_name,
            event_data=event_data_to_json(event_data),
            removed=False,
        )
        session.add(event)
        session.flush()  # Flush to trigger unique constraint check
        return True
    except IntegrityError:
        # Event already exists (idempotent)
        session.rollback()
        logger.debug(f"Event already exists: {tx_hash}:{log_index}")
        return False


def apply_campaign_created(
    session: Session,
    chain_id: int,
    event_data: Dict[str, Any],
    block_number: int,
    block_hash: str,
    tx_hash: str,
    log_index: int,
) -> None:
    """Apply CampaignCreated event state update.

    Args:
        session: Database session
        chain_id: Chain ID
        event_data: Decoded event data
        block_number: Block number
        block_hash: Block hash
        tx_hash: Transaction hash
        log_index: Log index
    """
    args = event_data["args"]
    campaign_address = args["campaign"].lower()
    factory_address = args["factory"].lower()
    creator_address = args["creator"].lower()
    goal_wei = int(args["goal"])
    deadline_ts = int(args["deadline"])
    cid = args["cid"]

    # Insert/update campaign
    campaign = session.query(Campaign).filter(Campaign.address == campaign_address).first()
    
    if campaign is None:
        campaign = Campaign(
            address=campaign_address,
            factory_address=factory_address,
            creator_address=creator_address,
            goal_wei=goal_wei,
            deadline_ts=deadline_ts,
            cid=cid,
            status="ACTIVE",
            total_raised_wei=0,
            withdrawn=False,
        )
        session.add(campaign)
        logger.info(f"Created campaign: {campaign_address}")
    else:
        # Update existing campaign (shouldn't happen, but handle gracefully)
        logger.debug(f"Campaign already exists: {campaign_address}, updating")
        campaign.factory_address = factory_address
        campaign.creator_address = creator_address
        campaign.goal_wei = goal_wei
        campaign.deadline_ts = deadline_ts
        campaign.cid = cid
        if campaign.status not in ["SUCCESS", "WITHDRAWN"]:
            campaign.status = "ACTIVE"


def apply_donation_received(
    session: Session,
    chain_id: int,
    event_data: Dict[str, Any],
    block_number: int,
    block_hash: str,
    tx_hash: str,
    log_index: int,
) -> None:
    """Apply DonationReceived event state update.

    Args:
        session: Database session
        chain_id: Chain ID
        event_data: Decoded event data
        block_number: Block number
        block_hash: Block hash
        tx_hash: Transaction hash
        log_index: Log index
    """
    args = event_data["args"]
    campaign_address = args["campaign"].lower()
    donor_address = args["donor"].lower()
    amount = int(args["amount"])
    new_total_raised = int(args["newTotalRaised"])

    # Get or create campaign
    campaign = session.query(Campaign).filter(Campaign.address == campaign_address).first()
    if campaign is None:
        logger.warning(f"Campaign not found for donation: {campaign_address}")
        return

    # Upsert contribution
    contribution = (
        session.query(Contribution)
        .filter(
            Contribution.campaign_address == campaign_address,
            Contribution.donor_address == donor_address,
        )
        .first()
    )

    if contribution is None:
        contribution = Contribution(
            campaign_address=campaign_address,
            donor_address=donor_address,
            contributed_wei=amount,
            refunded_wei=0,
        )
        session.add(contribution)
    else:
        contribution.contributed_wei += amount

    # Update campaign totals
    campaign.total_raised_wei = new_total_raised

    # Update status if goal met
    if new_total_raised >= campaign.goal_wei and campaign.status == "ACTIVE":
        campaign.status = "SUCCESS"
        logger.info(f"Campaign {campaign_address} reached goal: {new_total_raised} >= {campaign.goal_wei}")


def apply_withdrawn(
    session: Session,
    chain_id: int,
    event_data: Dict[str, Any],
    block_number: int,
    block_hash: str,
    tx_hash: str,
    log_index: int,
) -> None:
    """Apply Withdrawn event state update.

    Args:
        session: Database session
        chain_id: Chain ID
        event_data: Decoded event data
        block_number: Block number
        block_hash: Block hash
        tx_hash: Transaction hash
        log_index: Log index
    """
    args = event_data["args"]
    campaign_address = args["campaign"].lower()
    amount = int(args["amount"])

    # Get campaign
    campaign = session.query(Campaign).filter(Campaign.address == campaign_address).first()
    if campaign is None:
        logger.warning(f"Campaign not found for withdrawal: {campaign_address}")
        return

    # Update campaign
    campaign.withdrawn = True
    campaign.withdrawn_amount_wei = amount
    campaign.status = "WITHDRAWN"
    logger.info(f"Campaign {campaign_address} withdrawn: {amount} wei")


def apply_refunded(
    session: Session,
    chain_id: int,
    event_data: Dict[str, Any],
    block_number: int,
    block_hash: str,
    tx_hash: str,
    log_index: int,
) -> None:
    """Apply Refunded event state update.

    Args:
        session: Database session
        chain_id: Chain ID
        event_data: Decoded event data
        block_number: Block number
        block_hash: Block hash
        tx_hash: Transaction hash
        log_index: Log index

    Note:
        We keep contributed_wei as lifetime total and track refunded_wei separately.
        Status becomes "FAILED" via reconciler, not directly from this event.
    """
    args = event_data["args"]
    campaign_address = args["campaign"].lower()
    donor_address = args["donor"].lower()
    amount = int(args["amount"])

    # Get contribution
    contribution = (
        session.query(Contribution)
        .filter(
            Contribution.campaign_address == campaign_address,
            Contribution.donor_address == donor_address,
        )
        .first()
    )

    if contribution is None:
        logger.warning(
            f"Contribution not found for refund: campaign={campaign_address}, donor={donor_address}"
        )
        return

    # Update refunded amount (keep contributed_wei as lifetime total)
    contribution.refunded_wei += amount
    logger.debug(f"Refunded {amount} wei to {donor_address} for campaign {campaign_address}")


def apply_event_state_update(
    session: Session,
    chain_id: int,
    event_name: str,
    event_data: Dict[str, Any],
    block_number: int,
    block_hash: str,
    tx_hash: str,
    log_index: int,
) -> None:
    """Apply state update for any event type.

    Args:
        session: Database session
        chain_id: Chain ID
        event_name: Event name
        event_data: Decoded event data
        block_number: Block number
        block_hash: Block hash
        tx_hash: Transaction hash
        log_index: Log index
    """
    # Check if event already processed (idempotency)
    existing = (
        session.query(Event)
        .filter(
            Event.chain_id == chain_id,
            Event.tx_hash == tx_hash,
            Event.log_index == log_index,
        )
        .first()
    )

    if existing and not existing.removed:
        # Event already processed, skip state update
        logger.debug(f"Event already processed, skipping state update: {tx_hash}:{log_index}")
        return

    # Apply state update based on event type
    if event_name == "CampaignCreated":
        apply_campaign_created(session, chain_id, event_data, block_number, block_hash, tx_hash, log_index)
    elif event_name == "DonationReceived":
        apply_donation_received(session, chain_id, event_data, block_number, block_hash, tx_hash, log_index)
    elif event_name == "Withdrawn":
        apply_withdrawn(session, chain_id, event_data, block_number, block_hash, tx_hash, log_index)
    elif event_name == "Refunded":
        apply_refunded(session, chain_id, event_data, block_number, block_hash, tx_hash, log_index)
    else:
        logger.warning(f"Unknown event type: {event_name}")

