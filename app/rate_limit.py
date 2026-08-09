from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings

# Backed by the same Redis instance RQ already requires — reusing infrastructure
# rather than standing up a second store just for rate-limit counters.
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.redis_url,
    default_limits=[settings.rate_limit],
)
