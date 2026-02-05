"""State updater for consumer - applies event-driven state changes to database."""

import json
from typing import Any, Dict

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db.models import Campaign, Contribution, Event
from log import get_logger

logger = get_logger(__name__)


class ConsumerStateUpdater:
    """Handles state updates from consumed event messages."""

    def __init__(self, chain_id: int):
        """Initialize state updater.
        
        Args:
            chain_id: Chain ID for events
        """
        self.chain_id = chain_id

    def insert_event(
        self,
        session: Session,
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
        # Check if event already exists (avoid rollback issues)
        existing = (
            session.query(Event)
            .filter(
                Event.chain_id == self.chain_id,
                Event.tx_hash == tx_hash,
                Event.log_index == log_index,
            )
            .first()
        )
        
        if existing:
            logger.debug(f"Event already exists: {tx_hash}:{log_index}")
            return False
        
        try:
            event = Event(
                chain_id=self.chain_id,
                tx_hash=tx_hash,
                log_index=log_index,
                block_number=block_number,
                block_hash=block_hash,
                address=address,
                event_name=event_name,
                event_data=json.dumps(event_data),
                removed=False,
            )
            session.add(event)
            session.flush()  # Flush to trigger constraint checks
            return True
        except IntegrityError as e:
            session.rollback()
            error_str = str(e.orig) if e.orig else str(e)
            
            # Check what kind of constraint violation it is
            if "uq_events_chain_tx_log" in error_str.lower() or "duplicate key" in error_str.lower():
                # Duplicate event (race condition with another worker)
                logger.debug(f"Event already exists (race condition): {tx_hash}:{log_index}")
                return False
            
            # Foreign key violation - determine which one
            if "events_chain_id_fkey" in error_str.lower() or "chains" in error_str.lower():
                logger.error(
                    f"FOREIGN KEY ERROR: chain_id={self.chain_id} does not exist in 'chains' table!\n"
                    f"FIX: Run this SQL:\n"
                    f"  INSERT INTO chains (name, chain_id, rpc_url) VALUES ('Hardhat Local', {self.chain_id}, 'http://127.0.0.1:8545');\n"
                    f"Original error: {error_str}"
                )
                raise
            
            if "events_address_fkey" in error_str.lower() or "campaigns" in error_str.lower():
                logger.error(
                    f"FOREIGN KEY ERROR: address={address} does not exist in 'campaigns' table!\n"
                    f"This usually means the campaign was not created before the event.\n"
                    f"For CampaignCreated events, the campaign should be created first.\n"
                    f"Original error: {error_str}"
                )
                raise
            
            # Unknown foreign key violation
            if "foreign key" in error_str.lower():
                logger.error(f"FOREIGN KEY ERROR: {error_str}")
                raise
            
            # Unknown integrity error - log and re-raise
            logger.error(f"Integrity error inserting event: {error_str}")
            raise

    def apply_campaign_created(
        self,
        session: Session,
        event_data: Dict[str, Any],
    ) -> None:
        """Apply CampaignCreated event state update.

        Args:
            session: Database session
            event_data: Decoded event data (the event_data field from message)
        """
        campaign_address = str(event_data.get("campaign", "")).lower()
        factory_address = str(event_data.get("factory", "")).lower()
        creator_address = str(event_data.get("creator", "")).lower()
        goal_wei = int(event_data.get("goal", 0))
        deadline_ts = int(event_data.get("deadline", 0))
        cid = event_data.get("cid", "")

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
        self,
        session: Session,
        event_data: Dict[str, Any],
    ) -> None:
        """Apply DonationReceived event state update.

        Args:
            session: Database session
            event_data: Decoded event data
        """
        campaign_address = str(event_data.get("campaign", "")).lower()
        donor_address = str(event_data.get("donor", "")).lower()
        amount = int(event_data.get("amount", 0))
        new_total_raised = int(event_data.get("newTotalRaised", 0))

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
        self,
        session: Session,
        event_data: Dict[str, Any],
    ) -> None:
        """Apply Withdrawn event state update.

        Args:
            session: Database session
            event_data: Decoded event data
        """
        campaign_address = str(event_data.get("campaign", "")).lower()
        amount = int(event_data.get("amount", 0))

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
        self,
        session: Session,
        event_data: Dict[str, Any],
    ) -> None:
        """Apply Refunded event state update.

        Args:
            session: Database session
            event_data: Decoded event data
        """
        campaign_address = str(event_data.get("campaign", "")).lower()
        donor_address = str(event_data.get("donor", "")).lower()
        amount = int(event_data.get("amount", 0))

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

    def apply_event(
        self,
        session: Session,
        event_type: str,
        event_data: Dict[str, Any],
    ) -> None:
        """Apply state update for any event type.

        Args:
            session: Database session
            event_type: Event type (CampaignCreated, DonationReceived, etc.)
            event_data: Decoded event data
        """
        if event_type == "CampaignCreated":
            self.apply_campaign_created(session, event_data)
        elif event_type == "DonationReceived":
            self.apply_donation_received(session, event_data)
        elif event_type == "Withdrawn":
            self.apply_withdrawn(session, event_data)
        elif event_type == "Refunded":
            self.apply_refunded(session, event_data)
        else:
            logger.warning(f"Unknown event type: {event_type}")
