from .service import (
    WSMessageProjector,
    WSMetadata,
    WSOutboundMessage,
    WSStatusUpdatePayload,
)

# Backward compatibility alias
ProjectorService = WSMessageProjector

__all__ = [
    "WSMetadata",
    "WSMessageProjector",
    "WSOutboundMessage",
    "WSStatusUpdatePayload",
    # Backward compatibility
    "ProjectorService",
]
