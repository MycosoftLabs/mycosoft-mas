"""Integrations module for external service clients."""

from mycosoft_mas.integrations.notion_client import NotionClient
from mycosoft_mas.integrations.ncbi_client import NCBIClient
from mycosoft_mas.integrations.chemspider_client import ChemSpiderClient
from mycosoft_mas.integrations.asana_client import AsanaClient
from mycosoft_mas.integrations.slack_client import SlackClient
from mycosoft_mas.integrations.natureos_client import NATUREOSClient
from mycosoft_mas.integrations.mycorrhizae_client import MycorrhizaeClient
from mycosoft_mas.integrations.a2a_client import A2AClient
from mycosoft_mas.integrations.supabase_client import SupabaseClient
from mycosoft_mas.integrations.elevenlabs_client import ElevenLabsClient
from mycosoft_mas.integrations.inaturalist_client import INaturalistClient, INaturalistConfig

try:
    from mycosoft_mas.integrations.discord_client import DiscordClient
except ImportError:
    DiscordClient = None
try:
    from mycosoft_mas.integrations.whatsapp_client import WhatsAppClient
except ImportError:
    WhatsAppClient = None
try:
    from mycosoft_mas.integrations.signal_client import SignalClient
except ImportError:
    SignalClient = None

__all__ = [
    "NotionClient",
    "NCBIClient",
    "ChemSpiderClient",
    "AsanaClient",
    "SlackClient",
    "NATUREOSClient",
    "MycorrhizaeClient",
    "A2AClient",
    "SupabaseClient",
    "ElevenLabsClient",
    "INaturalistClient",
    "INaturalistConfig",
    "DiscordClient",
    "WhatsAppClient",
    "SignalClient",
]