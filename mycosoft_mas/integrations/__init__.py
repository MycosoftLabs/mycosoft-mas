"""Integrations module for external service clients."""

from mycosoft_mas.integrations.a2a_client import A2AClient
from mycosoft_mas.integrations.asana_client import AsanaClient
from mycosoft_mas.integrations.chemspider_client import ChemSpiderClient
from mycosoft_mas.integrations.elevenlabs_client import ElevenLabsClient
from mycosoft_mas.integrations.inaturalist_client import INaturalistClient, INaturalistConfig
from mycosoft_mas.integrations.mycorrhizae_client import MycorrhizaeClient
from mycosoft_mas.integrations.natureos_client import NATUREOSClient
from mycosoft_mas.integrations.ncbi_client import NCBIClient
from mycosoft_mas.integrations.notion_client import NotionClient
from mycosoft_mas.integrations.slack_client import SlackClient
from mycosoft_mas.integrations.supabase_client import SupabaseClient

try:
    from mycosoft_mas.integrations.google_workspace_client import GoogleWorkspaceClient
except ImportError:
    GoogleWorkspaceClient = None

try:
    from mycosoft_mas.integrations.quickbooks_client import QuickBooksClient
except ImportError:
    QuickBooksClient = None

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

try:
    from mycosoft_mas.integrations.github_client import GitHubClient
except ImportError:
    GitHubClient = None

try:
    from mycosoft_mas.integrations.huggingface_client import HuggingFaceClient
except ImportError:
    HuggingFaceClient = None

try:
    from mycosoft_mas.integrations.stripe_client import StripeClient
except ImportError:
    StripeClient = None

try:
    from mycosoft_mas.integrations.paypal_client import PayPalClient
except ImportError:
    PayPalClient = None

try:
    from mycosoft_mas.integrations.relay_client import RelayClient
except ImportError:
    RelayClient = None

try:
    from mycosoft_mas.integrations.openai_client import OpenAIClient
except ImportError:
    OpenAIClient = None

try:
    from mycosoft_mas.integrations.anthropic_client import AnthropicClient
except ImportError:
    AnthropicClient = None

try:
    from mycosoft_mas.integrations.perplexity_client import PerplexityClient
except ImportError:
    PerplexityClient = None

try:
    from mycosoft_mas.integrations.solana_client import SolanaClient
except ImportError:
    SolanaClient = None

try:
    from mycosoft_mas.integrations.coinbase_client import CoinbaseClient
except ImportError:
    CoinbaseClient = None

try:
    from mycosoft_mas.integrations.phantom_client import PhantomClient
except ImportError:
    PhantomClient = None

try:
    from mycosoft_mas.integrations.jupiter_client import JupiterClient
except ImportError:
    JupiterClient = None

try:
    from mycosoft_mas.integrations.solana_dex_client import SolanaDexClient
except ImportError:
    SolanaDexClient = None

try:
    from mycosoft_mas.integrations.alphafold_client import AlphaFoldClient
except ImportError:
    AlphaFoldClient = None

try:
    from mycosoft_mas.integrations.protein_design_client import ProteinDesignClient
except ImportError:
    ProteinDesignClient = None

try:
    from mycosoft_mas.integrations.illumina_client import IlluminaClient
except ImportError:
    IlluminaClient = None

try:
    from mycosoft_mas.integrations.uniprot_client import UniProtClient
except ImportError:
    UniProtClient = None

try:
    from mycosoft_mas.integrations.pdb_client import PDBClient
except ImportError:
    PDBClient = None

try:
    from mycosoft_mas.integrations.tecan_client import TecanClient
except ImportError:
    TecanClient = None

try:
    from mycosoft_mas.integrations.culture_vision_client import CultureVisionClient
except ImportError:
    CultureVisionClient = None

try:
    from mycosoft_mas.integrations.chembl_client import ChEMBLClient
except ImportError:
    ChEMBLClient = None

try:
    from mycosoft_mas.integrations.kegg_client import KEGGClient
except ImportError:
    KEGGClient = None

try:
    from mycosoft_mas.integrations.preprint_watcher_client import PreprintWatcherClient
except ImportError:
    PreprintWatcherClient = None

try:
    from mycosoft_mas.integrations.exostar_client import ExostarClient
except ImportError:
    ExostarClient = None

try:
    from mycosoft_mas.integrations.export_control_client import ExportControlClient
except ImportError:
    ExportControlClient = None

try:
    from mycosoft_mas.integrations.sam_gov_client import SamGovClient
except ImportError:
    SamGovClient = None

try:
    from mycosoft_mas.integrations.grants_gov_client import GrantsGovClient
except ImportError:
    GrantsGovClient = None

try:
    from mycosoft_mas.integrations.sbir_client import SbirClient
except ImportError:
    SbirClient = None

try:
    from mycosoft_mas.integrations.gao_client import GaoClient
except ImportError:
    GaoClient = None

try:
    from mycosoft_mas.integrations.nasa_client import NasaClient
except ImportError:
    NasaClient = None

try:
    from mycosoft_mas.integrations.noaa_client import NoaaClient
except ImportError:
    NoaaClient = None

try:
    from mycosoft_mas.integrations.osint_defense_client import OsintDefenseClient
except ImportError:
    OsintDefenseClient = None

try:
    from mycosoft_mas.integrations.academic_client import AcademicClient
except ImportError:
    AcademicClient = None

try:
    from mycosoft_mas.integrations.patent_client import PatentClient
except ImportError:
    PatentClient = None

try:
    from mycosoft_mas.integrations.biodiversity_client import BiodiversityClient
except ImportError:
    BiodiversityClient = None

try:
    from mycosoft_mas.integrations.ibm_quantum_client import IbmQuantumClient
except ImportError:
    IbmQuantumClient = None

try:
    from mycosoft_mas.integrations.google_quantum_client import GoogleQuantumClient
except ImportError:
    GoogleQuantumClient = None

try:
    from mycosoft_mas.integrations.gpu_compute_client import GpuComputeClient
except ImportError:
    GpuComputeClient = None

try:
    from mycosoft_mas.integrations.wandb_client import WandbClient
except ImportError:
    WandbClient = None

try:
    from mycosoft_mas.integrations.fiat_ramp_client import FiatRampClient
except ImportError:
    FiatRampClient = None

try:
    from mycosoft_mas.integrations.crypto_tax_client import CryptoTaxClient
except ImportError:
    CryptoTaxClient = None

try:
    from mycosoft_mas.integrations.ows_client import OWSClient
except ImportError:
    OWSClient = None

__all__ = [
    "NotionClient",
    "NCBIClient",
    "GoogleWorkspaceClient",
    "QuickBooksClient",
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
    "GitHubClient",
    "HuggingFaceClient",
    "StripeClient",
    "PayPalClient",
    "RelayClient",
    "OpenAIClient",
    "AnthropicClient",
    "PerplexityClient",
    "SolanaClient",
    "CoinbaseClient",
    "PhantomClient",
    "JupiterClient",
    "SolanaDexClient",
    "AlphaFoldClient",
    "ProteinDesignClient",
    "IlluminaClient",
    "UniProtClient",
    "PDBClient",
    "TecanClient",
    "CultureVisionClient",
    "ChEMBLClient",
    "KEGGClient",
    "PreprintWatcherClient",
    "ExostarClient",
    "SamGovClient",
    "GrantsGovClient",
    "SbirClient",
    "ExportControlClient",
    "GaoClient",
    "NasaClient",
    "NoaaClient",
    "OsintDefenseClient",
    "AcademicClient",
    "PatentClient",
    "BiodiversityClient",
    "IbmQuantumClient",
    "GoogleQuantumClient",
    "GpuComputeClient",
    "WandbClient",
    "FiatRampClient",
    "CryptoTaxClient",
    "OWSClient",
]
