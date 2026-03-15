"""
Earth Search Data Source Registry — all external APIs and data feeds mapped to domains.

Each source declares which EarthSearchDomains it can serve, its API URL, and whether
it requires authentication. The connector layer uses this registry to route queries.

Created: March 15, 2026
"""

from __future__ import annotations

from typing import Dict, List, Optional

from mycosoft_mas.earth_search.models import DataSourceInfo, EarthSearchDomain

# =============================================================================
# Master registry of all data sources
# =============================================================================

EARTH_DATA_SOURCES: List[DataSourceInfo] = [
    # --- Species / Biodiversity ---
    DataSourceInfo(
        source_id="inaturalist",
        name="iNaturalist",
        api_url="https://api.inaturalist.org/v1",
        domains=[
            EarthSearchDomain.ALL_SPECIES, EarthSearchDomain.FUNGI,
            EarthSearchDomain.PLANTS, EarthSearchDomain.BIRDS,
            EarthSearchDomain.MAMMALS, EarthSearchDomain.REPTILES,
            EarthSearchDomain.AMPHIBIANS, EarthSearchDomain.INSECTS,
            EarthSearchDomain.MARINE_LIFE, EarthSearchDomain.FISH,
            EarthSearchDomain.INVERTEBRATES,
        ],
        description="Global citizen-science biodiversity observations with photos and geolocation",
    ),
    DataSourceInfo(
        source_id="gbif",
        name="GBIF",
        api_url="https://api.gbif.org/v1",
        domains=[
            EarthSearchDomain.ALL_SPECIES, EarthSearchDomain.FUNGI,
            EarthSearchDomain.PLANTS, EarthSearchDomain.BIRDS,
            EarthSearchDomain.MAMMALS, EarthSearchDomain.REPTILES,
            EarthSearchDomain.AMPHIBIANS, EarthSearchDomain.INSECTS,
            EarthSearchDomain.MARINE_LIFE, EarthSearchDomain.FISH,
            EarthSearchDomain.MICROORGANISMS, EarthSearchDomain.INVERTEBRATES,
        ],
        description="Global Biodiversity Information Facility — 2B+ occurrence records",
    ),
    DataSourceInfo(
        source_id="col",
        name="Catalogue of Life",
        api_url="https://api.checklistbank.org",
        domains=[EarthSearchDomain.ALL_SPECIES],
        description="Authoritative global species checklist",
    ),
    DataSourceInfo(
        source_id="eol",
        name="Encyclopedia of Life",
        api_url="https://eol.org/api",
        domains=[EarthSearchDomain.ALL_SPECIES],
        description="Species pages, media, and trait data",
    ),
    DataSourceInfo(
        source_id="itis",
        name="ITIS",
        api_url="https://www.itis.gov/ITISWebService/jsonservice",
        domains=[EarthSearchDomain.ALL_SPECIES],
        description="US Integrated Taxonomic Information System",
    ),
    DataSourceInfo(
        source_id="worms",
        name="WoRMS",
        api_url="https://www.marinespecies.org/rest",
        domains=[EarthSearchDomain.MARINE_LIFE, EarthSearchDomain.FISH, EarthSearchDomain.INVERTEBRATES],
        description="World Register of Marine Species — authoritative marine taxonomy",
    ),
    DataSourceInfo(
        source_id="bold",
        name="BOLD Systems",
        api_url="https://v3.boldsystems.org/index.php/API_Public",
        domains=[EarthSearchDomain.ALL_SPECIES, EarthSearchDomain.GENETICS],
        description="Barcode of Life — DNA barcoding database",
    ),
    DataSourceInfo(
        source_id="mycobank",
        name="MycoBank",
        api_url="https://www.mycobank.org",
        domains=[EarthSearchDomain.FUNGI],
        description="International mycological nomenclature and taxonomy",
    ),
    DataSourceInfo(
        source_id="fungidb",
        name="FungiDB",
        api_url="https://fungidb.org",
        domains=[EarthSearchDomain.FUNGI, EarthSearchDomain.GENETICS],
        description="Fungal genomics and functional data",
    ),
    DataSourceInfo(
        source_id="genbank",
        name="GenBank/NCBI",
        api_url="https://eutils.ncbi.nlm.nih.gov/entrez/eutils",
        domains=[EarthSearchDomain.GENETICS, EarthSearchDomain.ALL_SPECIES],
        description="NCBI nucleotide sequences, genomes, protein data",
    ),
    DataSourceInfo(
        source_id="pubchem",
        name="PubChem",
        api_url="https://pubchem.ncbi.nlm.nih.gov/rest/pug",
        domains=[EarthSearchDomain.COMPOUNDS],
        description="Chemical compound database — structures, bioactivity, safety",
    ),
    DataSourceInfo(
        source_id="pubmed",
        name="PubMed",
        api_url="https://eutils.ncbi.nlm.nih.gov/entrez/eutils",
        domains=[EarthSearchDomain.RESEARCH],
        description="Biomedical literature — 36M+ citations and abstracts",
    ),

    # --- Environmental Events ---
    DataSourceInfo(
        source_id="usgs_earthquake",
        name="USGS Earthquake Hazards",
        api_url="https://earthquake.usgs.gov/fdsnws/event/1",
        domains=[EarthSearchDomain.EARTHQUAKES, EarthSearchDomain.SEISMIC_STATIONS],
        realtime=True,
        description="Real-time and historical earthquake data worldwide",
    ),
    DataSourceInfo(
        source_id="smithsonian_volcanoes",
        name="Smithsonian Global Volcanism",
        api_url="https://volcano.si.edu/database/webservices.cfm",
        domains=[EarthSearchDomain.VOLCANOES],
        description="Active volcanoes, eruption history, monitoring data",
    ),
    DataSourceInfo(
        source_id="firms_wildfires",
        name="NASA FIRMS",
        api_url="https://firms.modaps.eosdis.nasa.gov/api/area",
        domains=[EarthSearchDomain.WILDFIRES],
        requires_key=True,
        realtime=True,
        description="Fire Information for Resource Management — active fire detection via MODIS/VIIRS",
    ),
    DataSourceInfo(
        source_id="noaa_storms",
        name="NOAA Storm Events",
        api_url="https://www.ncdc.noaa.gov/stormevents/ftp.jsp",
        domains=[EarthSearchDomain.STORMS, EarthSearchDomain.TORNADOES, EarthSearchDomain.FLOODS, EarthSearchDomain.LIGHTNING],
        realtime=True,
        description="NOAA severe weather events — storms, tornadoes, lightning, floods",
    ),
    DataSourceInfo(
        source_id="noaa_nhc",
        name="NOAA National Hurricane Center",
        api_url="https://www.nhc.noaa.gov/data",
        domains=[EarthSearchDomain.STORMS],
        realtime=True,
        description="Active tropical cyclones and hurricane tracking",
    ),

    # --- Atmospheric / Climate ---
    DataSourceInfo(
        source_id="openweathermap",
        name="OpenWeatherMap",
        api_url="https://api.openweathermap.org/data/2.5",
        domains=[EarthSearchDomain.WEATHER, EarthSearchDomain.AIR_QUALITY],
        requires_key=True,
        realtime=True,
        description="Current weather, forecasts, air quality index",
    ),
    DataSourceInfo(
        source_id="noaa_co2",
        name="NOAA Global Monitoring Lab",
        api_url="https://gml.noaa.gov/webdata",
        domains=[EarthSearchDomain.CO2, EarthSearchDomain.METHANE],
        description="CO2 and methane measurements — Mauna Loa and global network",
    ),
    DataSourceInfo(
        source_id="airnow",
        name="AirNow",
        api_url="https://www.airnowapi.org/aq",
        domains=[EarthSearchDomain.AIR_QUALITY],
        requires_key=True,
        realtime=True,
        description="US EPA real-time air quality data and forecasts",
    ),
    DataSourceInfo(
        source_id="nasa_earthdata",
        name="NASA Earthdata",
        api_url="https://cmr.earthdata.nasa.gov/search",
        domains=[EarthSearchDomain.MODIS, EarthSearchDomain.LANDSAT, EarthSearchDomain.AIRS, EarthSearchDomain.GROUND_QUALITY],
        requires_key=True,
        description="NASA satellite data — MODIS, Landsat, AIRS imagery and measurements",
    ),

    # --- Ocean ---
    DataSourceInfo(
        source_id="ndbc_buoys",
        name="NOAA NDBC",
        api_url="https://www.ndbc.noaa.gov/data/realtime2",
        domains=[EarthSearchDomain.OCEAN_BUOYS, EarthSearchDomain.OCEAN_TEMPERATURE, EarthSearchDomain.WEATHER_STATIONS],
        realtime=True,
        description="National Data Buoy Center — ocean buoys, sea surface temp, wave data",
    ),

    # --- Transportation ---
    DataSourceInfo(
        source_id="crep_flights",
        name="CREP ADS-B (OpenSky/ADS-B Exchange)",
        api_url="http://192.168.0.187:3000/api/crep/flights",
        domains=[EarthSearchDomain.FLIGHTS],
        realtime=True,
        description="Real-time aircraft positions via ADS-B transponders",
    ),
    DataSourceInfo(
        source_id="crep_marine",
        name="CREP AIS (MarineTraffic)",
        api_url="http://192.168.0.187:3000/api/crep/marine",
        domains=[EarthSearchDomain.VESSELS, EarthSearchDomain.SHIPPING_PORTS],
        realtime=True,
        description="Real-time vessel positions via AIS transponders",
    ),
    DataSourceInfo(
        source_id="crep_satellites",
        name="CREP Satellites",
        api_url="http://192.168.0.187:3000/api/crep/satellites",
        domains=[EarthSearchDomain.SATELLITES],
        realtime=True,
        description="Active satellite positions and orbital data",
    ),
    DataSourceInfo(
        source_id="ourairports",
        name="OurAirports",
        api_url="https://ourairports.com/data",
        domains=[EarthSearchDomain.AIRPORTS],
        description="Global airport database with coordinates and runways",
    ),
    DataSourceInfo(
        source_id="wpi_ports",
        name="World Port Index",
        api_url="https://msi.nga.mil/api/publications/download",
        domains=[EarthSearchDomain.SHIPPING_PORTS],
        description="NGA World Port Index — global shipping port locations",
    ),

    # --- Space ---
    DataSourceInfo(
        source_id="noaa_swpc",
        name="NOAA Space Weather Prediction Center",
        api_url="https://services.swpc.noaa.gov/json",
        domains=[EarthSearchDomain.SPACE_WEATHER, EarthSearchDomain.SOLAR_FLARES],
        realtime=True,
        description="Solar flares, geomagnetic storms, solar wind, SOHO/STEREO data",
    ),
    DataSourceInfo(
        source_id="nasa_donki",
        name="NASA DONKI",
        api_url="https://api.nasa.gov/DONKI",
        domains=[EarthSearchDomain.SPACE_WEATHER, EarthSearchDomain.SOLAR_FLARES],
        requires_key=True,
        realtime=True,
        description="Space weather notifications — CME, solar flare, geomagnetic storm",
    ),
    DataSourceInfo(
        source_id="spacex_launches",
        name="SpaceX / Launch Library 2",
        api_url="https://ll.thespacedevs.com/2.2.0",
        domains=[EarthSearchDomain.LAUNCHES, EarthSearchDomain.SPACEPORTS],
        description="Rocket launches, landing pads, launch sites worldwide",
    ),

    # --- Industrial Infrastructure ---
    DataSourceInfo(
        source_id="osm_overpass",
        name="OpenStreetMap Overpass",
        api_url="https://overpass-api.de/api/interpreter",
        domains=[
            EarthSearchDomain.FACTORIES, EarthSearchDomain.POWER_PLANTS,
            EarthSearchDomain.MINING, EarthSearchDomain.OIL_GAS,
            EarthSearchDomain.DAMS, EarthSearchDomain.WATER_TREATMENT,
            EarthSearchDomain.RIVERS, EarthSearchDomain.CELL_TOWERS,
            EarthSearchDomain.AM_FM_ANTENNAS, EarthSearchDomain.INTERNET_CABLES,
            EarthSearchDomain.MILITARY_BASES, EarthSearchDomain.RAILWAYS,
        ],
        description="OpenStreetMap infrastructure queries via Overpass API",
    ),
    DataSourceInfo(
        source_id="epa_frs",
        name="US EPA FRS",
        api_url="https://ofmpub.epa.gov/frs_public2/frs_rest_services.get_facilities",
        domains=[EarthSearchDomain.POLLUTION_SOURCES, EarthSearchDomain.FACTORIES],
        description="EPA Facility Registry — regulated pollution-emitting facilities",
    ),
    DataSourceInfo(
        source_id="gem_powerplants",
        name="Global Energy Monitor",
        api_url="https://globalenergymonitor.org",
        domains=[EarthSearchDomain.POWER_PLANTS, EarthSearchDomain.OIL_GAS, EarthSearchDomain.MINING],
        description="Global power plant, coal mine, and fossil fuel tracker",
    ),

    # --- Telecommunications ---
    DataSourceInfo(
        source_id="opencellid",
        name="OpenCelliD",
        api_url="https://opencellid.org/ajax/searchCell.php",
        domains=[EarthSearchDomain.CELL_TOWERS, EarthSearchDomain.SIGNAL_MAPS],
        requires_key=True,
        description="Global cell tower database with signal coverage",
    ),
    DataSourceInfo(
        source_id="wigle",
        name="WiGLE",
        api_url="https://api.wigle.net/api/v2",
        domains=[EarthSearchDomain.WIFI_HOTSPOTS, EarthSearchDomain.CELL_TOWERS],
        requires_key=True,
        description="Wireless network mapping — WiFi and Bluetooth hotspots worldwide",
    ),
    DataSourceInfo(
        source_id="telegeography",
        name="TeleGeography Submarine Cable Map",
        api_url="https://www.submarinecablemap.com/api/v3",
        domains=[EarthSearchDomain.INTERNET_CABLES],
        description="Submarine internet cable routes and landing points",
    ),

    # --- Webcams ---
    DataSourceInfo(
        source_id="windy_webcams",
        name="Windy Webcams",
        api_url="https://api.windy.com/webcams/api/v3/webcams",
        domains=[EarthSearchDomain.WEBCAMS],
        requires_key=True,
        description="Global webcam directory — 70k+ webcams with live images",
    ),

    # --- Device Telemetry ---
    DataSourceInfo(
        source_id="mycobrain",
        name="MycoBrain IoT",
        api_url="http://192.168.0.187:8003",
        domains=[EarthSearchDomain.MYCOBRAIN_DEVICES],
        realtime=True,
        description="MycoBrain BME688/690 environmental sensor telemetry",
    ),

    # --- Earth2 Climate Prediction ---
    DataSourceInfo(
        source_id="earth2",
        name="NVIDIA Earth2",
        api_url="http://192.168.0.188:8001/api/earth2",
        domains=[EarthSearchDomain.WEATHER],
        requires_key=True,
        description="NVIDIA Earth2 climate simulation and weather prediction",
    ),

    # --- MINDEX Local (already ingested) ---
    DataSourceInfo(
        source_id="mindex_local",
        name="MINDEX Local",
        api_url="http://192.168.0.189:8000",
        domains=list(EarthSearchDomain),
        description="Local MINDEX database — low-latency pre-ingested data for all domains",
    ),
]

# Build lookup indexes
_SOURCE_BY_ID: Dict[str, DataSourceInfo] = {s.source_id: s for s in EARTH_DATA_SOURCES}
_SOURCES_BY_DOMAIN: Dict[EarthSearchDomain, List[DataSourceInfo]] = {}
for _src in EARTH_DATA_SOURCES:
    for _dom in _src.domains:
        _SOURCES_BY_DOMAIN.setdefault(_dom, []).append(_src)


def get_source_info(source_id: str) -> Optional[DataSourceInfo]:
    return _SOURCE_BY_ID.get(source_id)


def get_sources_for_domain(domain: EarthSearchDomain) -> List[DataSourceInfo]:
    return _SOURCES_BY_DOMAIN.get(domain, [])


def get_all_realtime_sources() -> List[DataSourceInfo]:
    return [s for s in EARTH_DATA_SOURCES if s.realtime]
