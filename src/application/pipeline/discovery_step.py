import logging

from src.application.interfaces.capability_gateway import CapabilityGatewayPort
from src.domain.value_objects.capability import CapabilityDescriptor

logger = logging.getLogger(__name__)


async def run_discovery(gateway: CapabilityGatewayPort) -> list[CapabilityDescriptor]:
    """Discover the capabilities the system is allowed to use. Deterministic."""
    capabilities = await gateway.discover()
    logger.info("discovered %d capabilities", len(capabilities))
    return capabilities
