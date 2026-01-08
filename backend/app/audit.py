import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger("audit")
logging.basicConfig(level=logging.INFO)


def audit(event: str, **fields):
    # Keep logs structured; do NOT log secrets/token contents.
    rec = {"ts": datetime.now(timezone.utc).isoformat(), "event": event, **fields}
    logger.info(json.dumps(rec))
