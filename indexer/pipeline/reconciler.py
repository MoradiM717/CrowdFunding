"""Reconciler - periodic reconciliation of campaign status."""

import time

from config import Config
from db.models import Campaign
from db.session import get_session
from log import get_logger

logger = get_logger(__name__)


class Reconciler:
    """Periodic campaign status reconciler."""

    def __init__(self, config: Config):
        """Initialize reconciler.

        Args:
            config: Configuration object
        """
        self.config = config
        self.last_reconciliation = 0
        self.reconciliation_interval = 60  # Run every 60 seconds

    def should_reconcile(self) -> bool:
        """Check if reconciliation should run.

        Returns:
            True if reconciliation should run
        """
        now = time.time()
        if now - self.last_reconciliation >= self.reconciliation_interval:
            self.last_reconciliation = now
            return True
        return False

    def reconcile(self) -> int:
        """Reconcile campaign statuses.

        Marks campaigns as FAILED if:
        - status is ACTIVE
        - deadline has passed
        - total_raised_wei < goal_wei
        - not withdrawn

        Returns:
            Number of campaigns updated
        """
        logger.debug("Running campaign reconciliation")

        now_ts = int(time.time())
        updated_count = 0

        with get_session() as session:
            # Find expired active campaigns that haven't met goal
            campaigns = (
                session.query(Campaign)
                .filter(
                    Campaign.status == "ACTIVE",
                    Campaign.deadline_ts < now_ts,
                    Campaign.total_raised_wei < Campaign.goal_wei,
                    Campaign.withdrawn == False,
                )
                .all()
            )

            for campaign in campaigns:
                campaign.status = "FAILED"
                updated_count += 1
                logger.info(
                    f"Marked campaign {campaign.address} as FAILED: "
                    f"deadline passed, goal not met"
                )

        if updated_count > 0:
            logger.info(f"Reconciliation: updated {updated_count} campaigns to FAILED")

        return updated_count

