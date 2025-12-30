# MINDEX - Mycological Index Data System

Central knowledge base for fungal information that continuously scrapes, organizes, and serves data from multiple sources.

## Data Sources

| Source | Data Type | Update Frequency |
|--------|-----------|------------------|
| **iNaturalist** | Species observations, photos, citizen science | Every 6 hours |
| **GBIF** | Global biodiversity occurrences | Every 12 hours |
| **MycoBank** | Taxonomic nomenclature, classifications | Daily |
| **FungiDB** | Genomic data, molecular biology | Daily |
| **GenBank** | NCBI sequences, genome assemblies | Daily |

## Storage Configuration

MINDEX uses network-attached storage for persistent data:

### Primary Storage (16TB Synology NAS)
- **Path**: `/mnt/nas/mindex`
- **Contains**: Main SQLite database, raw scraped data
- **Backup**: Daily to secondary storage

### Secondary Storage (26TB UniFi Dream Machine)
- **Path**: `/mnt/dream/mindex`
- **Contains**: Backups, image cache, large genomic files

## Quick Start

### Run with Docker Compose

```bash
# Start MINDEX service
docker-compose -f docker-compose.mindex.yml up -d

# View logs
docker-compose -f docker-compose.mindex.yml logs -f mindex

# Trigger manual sync
curl -X POST http://localhost:8000/api/mindex/sync
```

### Environment Variables

Create a `.env` file with:

```env
# NAS Storage (mount point on host)
MINDEX_HOST_PATH=/mnt/synology/mindex

# API Keys for higher rate limits
NCBI_API_KEY=your_ncbi_api_key
INATURALIST_API_KEY=your_inaturalist_token

# Sync configuration
MINDEX_SYNC_INTERVAL=24
MINDEX_MAX_RECORDS=100000
```

### Windows NAS Mount

```powershell
# Mount NAS share
net use Z: \\192.168.1.100\mindex /persistent:yes

# Set environment variable
$env:MINDEX_HOST_PATH = "Z:\mindex"
```

### Linux NAS Mount

```bash
# Add to /etc/fstab
//192.168.1.100/mindex /mnt/nas/mindex cifs credentials=/etc/nas-creds,uid=1000 0 0

# Create mount
sudo mount -a
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/api/mindex/stats` | GET | Database statistics |
| `/api/mindex/search?q=` | GET | Search species |
| `/api/mindex/taxa` | GET | List taxa (paginated) |
| `/api/mindex/taxa/{id}` | GET | Get taxon details |
| `/api/mindex/observations` | GET | List observations |
| `/api/mindex/etl-status` | GET | Scraper status |
| `/api/mindex/sync` | POST | Trigger manual sync |
| `/api/mindex/sync/{source}` | POST | Sync specific source |

## Database Schema

```sql
-- Species/Taxa table
CREATE TABLE species (
    id INTEGER PRIMARY KEY,
    source TEXT,
    source_id TEXT,
    scientific_name TEXT,
    common_name TEXT,
    rank TEXT,
    family TEXT,
    genus TEXT,
    -- ... full taxonomy
);

-- Observations table  
CREATE TABLE observations (
    id INTEGER PRIMARY KEY,
    source TEXT,
    species_id INTEGER,
    scientific_name TEXT,
    observed_on TEXT,
    latitude REAL,
    longitude REAL,
    photos TEXT,
    quality_grade TEXT
);

-- Genomic data table
CREATE TABLE genomic_data (
    id INTEGER PRIMARY KEY,
    source TEXT,
    organism_name TEXT,
    gene_name TEXT,
    sequence TEXT,
    genome_size TEXT
);
```

## Scraper Development

To add a new data source:

1. Create a new scraper in `mycosoft_mas/mindex/scrapers/`:

```python
from .base import BaseScraper, ScraperResult

class NewSourceScraper(BaseScraper):
    @property
    def source_name(self) -> str:
        return "NewSource"
    
    @property
    def base_url(self) -> str:
        return "https://api.newsource.org"
    
    async def search_species(self, query: str, limit: int = 100) -> ScraperResult:
        # Implementation
        pass
```

2. Register in `scrapers/__init__.py`
3. Add to manager's `sync_source` method

## Monitoring

MINDEX exposes Prometheus metrics at `/metrics`:

- `mindex_species_total` - Total species in database
- `mindex_observations_total` - Total observations
- `mindex_sync_duration_seconds` - Sync duration by source
- `mindex_sync_records_total` - Records synced by source

## Troubleshooting

### Service won't start
```bash
# Check if port is in use
netstat -an | grep 8000

# Check logs
docker-compose -f docker-compose.mindex.yml logs mindex
```

### NAS not mounting
```bash
# Check NAS is accessible
ping 192.168.1.100

# Check credentials
smbclient //192.168.1.100/mindex -U username
```

### Sync failing
```bash
# Check ETL status
curl http://localhost:8000/api/mindex/etl-status

# Check rate limits (iNaturalist: 60/min, NCBI: 3/sec)
# Wait and retry, or add API key for higher limits
```

# MINDEX - Mycological Index Data System

Central knowledge base for fungal information that continuously scrapes, organizes, and serves data from multiple sources.

## Data Sources

| Source | Data Type | Update Frequency |
|--------|-----------|------------------|
| **iNaturalist** | Species observations, photos, citizen science | Every 6 hours |
| **GBIF** | Global biodiversity occurrences | Every 12 hours |
| **MycoBank** | Taxonomic nomenclature, classifications | Daily |
| **FungiDB** | Genomic data, molecular biology | Daily |
| **GenBank** | NCBI sequences, genome assemblies | Daily |

## Storage Configuration

MINDEX uses network-attached storage for persistent data:

### Primary Storage (16TB Synology NAS)
- **Path**: `/mnt/nas/mindex`
- **Contains**: Main SQLite database, raw scraped data
- **Backup**: Daily to secondary storage

### Secondary Storage (26TB UniFi Dream Machine)
- **Path**: `/mnt/dream/mindex`
- **Contains**: Backups, image cache, large genomic files

## Quick Start

### Run with Docker Compose

```bash
# Start MINDEX service
docker-compose -f docker-compose.mindex.yml up -d

# View logs
docker-compose -f docker-compose.mindex.yml logs -f mindex

# Trigger manual sync
curl -X POST http://localhost:8000/api/mindex/sync
```

### Environment Variables

Create a `.env` file with:

```env
# NAS Storage (mount point on host)
MINDEX_HOST_PATH=/mnt/synology/mindex

# API Keys for higher rate limits
NCBI_API_KEY=your_ncbi_api_key
INATURALIST_API_KEY=your_inaturalist_token

# Sync configuration
MINDEX_SYNC_INTERVAL=24
MINDEX_MAX_RECORDS=100000
```

### Windows NAS Mount

```powershell
# Mount NAS share
net use Z: \\192.168.1.100\mindex /persistent:yes

# Set environment variable
$env:MINDEX_HOST_PATH = "Z:\mindex"
```

### Linux NAS Mount

```bash
# Add to /etc/fstab
//192.168.1.100/mindex /mnt/nas/mindex cifs credentials=/etc/nas-creds,uid=1000 0 0

# Create mount
sudo mount -a
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/api/mindex/stats` | GET | Database statistics |
| `/api/mindex/search?q=` | GET | Search species |
| `/api/mindex/taxa` | GET | List taxa (paginated) |
| `/api/mindex/taxa/{id}` | GET | Get taxon details |
| `/api/mindex/observations` | GET | List observations |
| `/api/mindex/etl-status` | GET | Scraper status |
| `/api/mindex/sync` | POST | Trigger manual sync |
| `/api/mindex/sync/{source}` | POST | Sync specific source |

## Database Schema

```sql
-- Species/Taxa table
CREATE TABLE species (
    id INTEGER PRIMARY KEY,
    source TEXT,
    source_id TEXT,
    scientific_name TEXT,
    common_name TEXT,
    rank TEXT,
    family TEXT,
    genus TEXT,
    -- ... full taxonomy
);

-- Observations table  
CREATE TABLE observations (
    id INTEGER PRIMARY KEY,
    source TEXT,
    species_id INTEGER,
    scientific_name TEXT,
    observed_on TEXT,
    latitude REAL,
    longitude REAL,
    photos TEXT,
    quality_grade TEXT
);

-- Genomic data table
CREATE TABLE genomic_data (
    id INTEGER PRIMARY KEY,
    source TEXT,
    organism_name TEXT,
    gene_name TEXT,
    sequence TEXT,
    genome_size TEXT
);
```

## Scraper Development

To add a new data source:

1. Create a new scraper in `mycosoft_mas/mindex/scrapers/`:

```python
from .base import BaseScraper, ScraperResult

class NewSourceScraper(BaseScraper):
    @property
    def source_name(self) -> str:
        return "NewSource"
    
    @property
    def base_url(self) -> str:
        return "https://api.newsource.org"
    
    async def search_species(self, query: str, limit: int = 100) -> ScraperResult:
        # Implementation
        pass
```

2. Register in `scrapers/__init__.py`
3. Add to manager's `sync_source` method

## Monitoring

MINDEX exposes Prometheus metrics at `/metrics`:

- `mindex_species_total` - Total species in database
- `mindex_observations_total` - Total observations
- `mindex_sync_duration_seconds` - Sync duration by source
- `mindex_sync_records_total` - Records synced by source

## Troubleshooting

### Service won't start
```bash
# Check if port is in use
netstat -an | grep 8000

# Check logs
docker-compose -f docker-compose.mindex.yml logs mindex
```

### NAS not mounting
```bash
# Check NAS is accessible
ping 192.168.1.100

# Check credentials
smbclient //192.168.1.100/mindex -U username
```

### Sync failing
```bash
# Check ETL status
curl http://localhost:8000/api/mindex/etl-status

# Check rate limits (iNaturalist: 60/min, NCBI: 3/sec)
# Wait and retry, or add API key for higher limits
```


# MINDEX - Mycological Index Data System

Central knowledge base for fungal information that continuously scrapes, organizes, and serves data from multiple sources.

## Data Sources

| Source | Data Type | Update Frequency |
|--------|-----------|------------------|
| **iNaturalist** | Species observations, photos, citizen science | Every 6 hours |
| **GBIF** | Global biodiversity occurrences | Every 12 hours |
| **MycoBank** | Taxonomic nomenclature, classifications | Daily |
| **FungiDB** | Genomic data, molecular biology | Daily |
| **GenBank** | NCBI sequences, genome assemblies | Daily |

## Storage Configuration

MINDEX uses network-attached storage for persistent data:

### Primary Storage (16TB Synology NAS)
- **Path**: `/mnt/nas/mindex`
- **Contains**: Main SQLite database, raw scraped data
- **Backup**: Daily to secondary storage

### Secondary Storage (26TB UniFi Dream Machine)
- **Path**: `/mnt/dream/mindex`
- **Contains**: Backups, image cache, large genomic files

## Quick Start

### Run with Docker Compose

```bash
# Start MINDEX service
docker-compose -f docker-compose.mindex.yml up -d

# View logs
docker-compose -f docker-compose.mindex.yml logs -f mindex

# Trigger manual sync
curl -X POST http://localhost:8000/api/mindex/sync
```

### Environment Variables

Create a `.env` file with:

```env
# NAS Storage (mount point on host)
MINDEX_HOST_PATH=/mnt/synology/mindex

# API Keys for higher rate limits
NCBI_API_KEY=your_ncbi_api_key
INATURALIST_API_KEY=your_inaturalist_token

# Sync configuration
MINDEX_SYNC_INTERVAL=24
MINDEX_MAX_RECORDS=100000
```

### Windows NAS Mount

```powershell
# Mount NAS share
net use Z: \\192.168.1.100\mindex /persistent:yes

# Set environment variable
$env:MINDEX_HOST_PATH = "Z:\mindex"
```

### Linux NAS Mount

```bash
# Add to /etc/fstab
//192.168.1.100/mindex /mnt/nas/mindex cifs credentials=/etc/nas-creds,uid=1000 0 0

# Create mount
sudo mount -a
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/api/mindex/stats` | GET | Database statistics |
| `/api/mindex/search?q=` | GET | Search species |
| `/api/mindex/taxa` | GET | List taxa (paginated) |
| `/api/mindex/taxa/{id}` | GET | Get taxon details |
| `/api/mindex/observations` | GET | List observations |
| `/api/mindex/etl-status` | GET | Scraper status |
| `/api/mindex/sync` | POST | Trigger manual sync |
| `/api/mindex/sync/{source}` | POST | Sync specific source |

## Database Schema

```sql
-- Species/Taxa table
CREATE TABLE species (
    id INTEGER PRIMARY KEY,
    source TEXT,
    source_id TEXT,
    scientific_name TEXT,
    common_name TEXT,
    rank TEXT,
    family TEXT,
    genus TEXT,
    -- ... full taxonomy
);

-- Observations table  
CREATE TABLE observations (
    id INTEGER PRIMARY KEY,
    source TEXT,
    species_id INTEGER,
    scientific_name TEXT,
    observed_on TEXT,
    latitude REAL,
    longitude REAL,
    photos TEXT,
    quality_grade TEXT
);

-- Genomic data table
CREATE TABLE genomic_data (
    id INTEGER PRIMARY KEY,
    source TEXT,
    organism_name TEXT,
    gene_name TEXT,
    sequence TEXT,
    genome_size TEXT
);
```

## Scraper Development

To add a new data source:

1. Create a new scraper in `mycosoft_mas/mindex/scrapers/`:

```python
from .base import BaseScraper, ScraperResult

class NewSourceScraper(BaseScraper):
    @property
    def source_name(self) -> str:
        return "NewSource"
    
    @property
    def base_url(self) -> str:
        return "https://api.newsource.org"
    
    async def search_species(self, query: str, limit: int = 100) -> ScraperResult:
        # Implementation
        pass
```

2. Register in `scrapers/__init__.py`
3. Add to manager's `sync_source` method

## Monitoring

MINDEX exposes Prometheus metrics at `/metrics`:

- `mindex_species_total` - Total species in database
- `mindex_observations_total` - Total observations
- `mindex_sync_duration_seconds` - Sync duration by source
- `mindex_sync_records_total` - Records synced by source

## Troubleshooting

### Service won't start
```bash
# Check if port is in use
netstat -an | grep 8000

# Check logs
docker-compose -f docker-compose.mindex.yml logs mindex
```

### NAS not mounting
```bash
# Check NAS is accessible
ping 192.168.1.100

# Check credentials
smbclient //192.168.1.100/mindex -U username
```

### Sync failing
```bash
# Check ETL status
curl http://localhost:8000/api/mindex/etl-status

# Check rate limits (iNaturalist: 60/min, NCBI: 3/sec)
# Wait and retry, or add API key for higher limits
```

# MINDEX - Mycological Index Data System

Central knowledge base for fungal information that continuously scrapes, organizes, and serves data from multiple sources.

## Data Sources

| Source | Data Type | Update Frequency |
|--------|-----------|------------------|
| **iNaturalist** | Species observations, photos, citizen science | Every 6 hours |
| **GBIF** | Global biodiversity occurrences | Every 12 hours |
| **MycoBank** | Taxonomic nomenclature, classifications | Daily |
| **FungiDB** | Genomic data, molecular biology | Daily |
| **GenBank** | NCBI sequences, genome assemblies | Daily |

## Storage Configuration

MINDEX uses network-attached storage for persistent data:

### Primary Storage (16TB Synology NAS)
- **Path**: `/mnt/nas/mindex`
- **Contains**: Main SQLite database, raw scraped data
- **Backup**: Daily to secondary storage

### Secondary Storage (26TB UniFi Dream Machine)
- **Path**: `/mnt/dream/mindex`
- **Contains**: Backups, image cache, large genomic files

## Quick Start

### Run with Docker Compose

```bash
# Start MINDEX service
docker-compose -f docker-compose.mindex.yml up -d

# View logs
docker-compose -f docker-compose.mindex.yml logs -f mindex

# Trigger manual sync
curl -X POST http://localhost:8000/api/mindex/sync
```

### Environment Variables

Create a `.env` file with:

```env
# NAS Storage (mount point on host)
MINDEX_HOST_PATH=/mnt/synology/mindex

# API Keys for higher rate limits
NCBI_API_KEY=your_ncbi_api_key
INATURALIST_API_KEY=your_inaturalist_token

# Sync configuration
MINDEX_SYNC_INTERVAL=24
MINDEX_MAX_RECORDS=100000
```

### Windows NAS Mount

```powershell
# Mount NAS share
net use Z: \\192.168.1.100\mindex /persistent:yes

# Set environment variable
$env:MINDEX_HOST_PATH = "Z:\mindex"
```

### Linux NAS Mount

```bash
# Add to /etc/fstab
//192.168.1.100/mindex /mnt/nas/mindex cifs credentials=/etc/nas-creds,uid=1000 0 0

# Create mount
sudo mount -a
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/api/mindex/stats` | GET | Database statistics |
| `/api/mindex/search?q=` | GET | Search species |
| `/api/mindex/taxa` | GET | List taxa (paginated) |
| `/api/mindex/taxa/{id}` | GET | Get taxon details |
| `/api/mindex/observations` | GET | List observations |
| `/api/mindex/etl-status` | GET | Scraper status |
| `/api/mindex/sync` | POST | Trigger manual sync |
| `/api/mindex/sync/{source}` | POST | Sync specific source |

## Database Schema

```sql
-- Species/Taxa table
CREATE TABLE species (
    id INTEGER PRIMARY KEY,
    source TEXT,
    source_id TEXT,
    scientific_name TEXT,
    common_name TEXT,
    rank TEXT,
    family TEXT,
    genus TEXT,
    -- ... full taxonomy
);

-- Observations table  
CREATE TABLE observations (
    id INTEGER PRIMARY KEY,
    source TEXT,
    species_id INTEGER,
    scientific_name TEXT,
    observed_on TEXT,
    latitude REAL,
    longitude REAL,
    photos TEXT,
    quality_grade TEXT
);

-- Genomic data table
CREATE TABLE genomic_data (
    id INTEGER PRIMARY KEY,
    source TEXT,
    organism_name TEXT,
    gene_name TEXT,
    sequence TEXT,
    genome_size TEXT
);
```

## Scraper Development

To add a new data source:

1. Create a new scraper in `mycosoft_mas/mindex/scrapers/`:

```python
from .base import BaseScraper, ScraperResult

class NewSourceScraper(BaseScraper):
    @property
    def source_name(self) -> str:
        return "NewSource"
    
    @property
    def base_url(self) -> str:
        return "https://api.newsource.org"
    
    async def search_species(self, query: str, limit: int = 100) -> ScraperResult:
        # Implementation
        pass
```

2. Register in `scrapers/__init__.py`
3. Add to manager's `sync_source` method

## Monitoring

MINDEX exposes Prometheus metrics at `/metrics`:

- `mindex_species_total` - Total species in database
- `mindex_observations_total` - Total observations
- `mindex_sync_duration_seconds` - Sync duration by source
- `mindex_sync_records_total` - Records synced by source

## Troubleshooting

### Service won't start
```bash
# Check if port is in use
netstat -an | grep 8000

# Check logs
docker-compose -f docker-compose.mindex.yml logs mindex
```

### NAS not mounting
```bash
# Check NAS is accessible
ping 192.168.1.100

# Check credentials
smbclient //192.168.1.100/mindex -U username
```

### Sync failing
```bash
# Check ETL status
curl http://localhost:8000/api/mindex/etl-status

# Check rate limits (iNaturalist: 60/min, NCBI: 3/sec)
# Wait and retry, or add API key for higher limits
```





# MINDEX - Mycological Index Data System

Central knowledge base for fungal information that continuously scrapes, organizes, and serves data from multiple sources.

## Data Sources

| Source | Data Type | Update Frequency |
|--------|-----------|------------------|
| **iNaturalist** | Species observations, photos, citizen science | Every 6 hours |
| **GBIF** | Global biodiversity occurrences | Every 12 hours |
| **MycoBank** | Taxonomic nomenclature, classifications | Daily |
| **FungiDB** | Genomic data, molecular biology | Daily |
| **GenBank** | NCBI sequences, genome assemblies | Daily |

## Storage Configuration

MINDEX uses network-attached storage for persistent data:

### Primary Storage (16TB Synology NAS)
- **Path**: `/mnt/nas/mindex`
- **Contains**: Main SQLite database, raw scraped data
- **Backup**: Daily to secondary storage

### Secondary Storage (26TB UniFi Dream Machine)
- **Path**: `/mnt/dream/mindex`
- **Contains**: Backups, image cache, large genomic files

## Quick Start

### Run with Docker Compose

```bash
# Start MINDEX service
docker-compose -f docker-compose.mindex.yml up -d

# View logs
docker-compose -f docker-compose.mindex.yml logs -f mindex

# Trigger manual sync
curl -X POST http://localhost:8000/api/mindex/sync
```

### Environment Variables

Create a `.env` file with:

```env
# NAS Storage (mount point on host)
MINDEX_HOST_PATH=/mnt/synology/mindex

# API Keys for higher rate limits
NCBI_API_KEY=your_ncbi_api_key
INATURALIST_API_KEY=your_inaturalist_token

# Sync configuration
MINDEX_SYNC_INTERVAL=24
MINDEX_MAX_RECORDS=100000
```

### Windows NAS Mount

```powershell
# Mount NAS share
net use Z: \\192.168.1.100\mindex /persistent:yes

# Set environment variable
$env:MINDEX_HOST_PATH = "Z:\mindex"
```

### Linux NAS Mount

```bash
# Add to /etc/fstab
//192.168.1.100/mindex /mnt/nas/mindex cifs credentials=/etc/nas-creds,uid=1000 0 0

# Create mount
sudo mount -a
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/api/mindex/stats` | GET | Database statistics |
| `/api/mindex/search?q=` | GET | Search species |
| `/api/mindex/taxa` | GET | List taxa (paginated) |
| `/api/mindex/taxa/{id}` | GET | Get taxon details |
| `/api/mindex/observations` | GET | List observations |
| `/api/mindex/etl-status` | GET | Scraper status |
| `/api/mindex/sync` | POST | Trigger manual sync |
| `/api/mindex/sync/{source}` | POST | Sync specific source |

## Database Schema

```sql
-- Species/Taxa table
CREATE TABLE species (
    id INTEGER PRIMARY KEY,
    source TEXT,
    source_id TEXT,
    scientific_name TEXT,
    common_name TEXT,
    rank TEXT,
    family TEXT,
    genus TEXT,
    -- ... full taxonomy
);

-- Observations table  
CREATE TABLE observations (
    id INTEGER PRIMARY KEY,
    source TEXT,
    species_id INTEGER,
    scientific_name TEXT,
    observed_on TEXT,
    latitude REAL,
    longitude REAL,
    photos TEXT,
    quality_grade TEXT
);

-- Genomic data table
CREATE TABLE genomic_data (
    id INTEGER PRIMARY KEY,
    source TEXT,
    organism_name TEXT,
    gene_name TEXT,
    sequence TEXT,
    genome_size TEXT
);
```

## Scraper Development

To add a new data source:

1. Create a new scraper in `mycosoft_mas/mindex/scrapers/`:

```python
from .base import BaseScraper, ScraperResult

class NewSourceScraper(BaseScraper):
    @property
    def source_name(self) -> str:
        return "NewSource"
    
    @property
    def base_url(self) -> str:
        return "https://api.newsource.org"
    
    async def search_species(self, query: str, limit: int = 100) -> ScraperResult:
        # Implementation
        pass
```

2. Register in `scrapers/__init__.py`
3. Add to manager's `sync_source` method

## Monitoring

MINDEX exposes Prometheus metrics at `/metrics`:

- `mindex_species_total` - Total species in database
- `mindex_observations_total` - Total observations
- `mindex_sync_duration_seconds` - Sync duration by source
- `mindex_sync_records_total` - Records synced by source

## Troubleshooting

### Service won't start
```bash
# Check if port is in use
netstat -an | grep 8000

# Check logs
docker-compose -f docker-compose.mindex.yml logs mindex
```

### NAS not mounting
```bash
# Check NAS is accessible
ping 192.168.1.100

# Check credentials
smbclient //192.168.1.100/mindex -U username
```

### Sync failing
```bash
# Check ETL status
curl http://localhost:8000/api/mindex/etl-status

# Check rate limits (iNaturalist: 60/min, NCBI: 3/sec)
# Wait and retry, or add API key for higher limits
```

# MINDEX - Mycological Index Data System

Central knowledge base for fungal information that continuously scrapes, organizes, and serves data from multiple sources.

## Data Sources

| Source | Data Type | Update Frequency |
|--------|-----------|------------------|
| **iNaturalist** | Species observations, photos, citizen science | Every 6 hours |
| **GBIF** | Global biodiversity occurrences | Every 12 hours |
| **MycoBank** | Taxonomic nomenclature, classifications | Daily |
| **FungiDB** | Genomic data, molecular biology | Daily |
| **GenBank** | NCBI sequences, genome assemblies | Daily |

## Storage Configuration

MINDEX uses network-attached storage for persistent data:

### Primary Storage (16TB Synology NAS)
- **Path**: `/mnt/nas/mindex`
- **Contains**: Main SQLite database, raw scraped data
- **Backup**: Daily to secondary storage

### Secondary Storage (26TB UniFi Dream Machine)
- **Path**: `/mnt/dream/mindex`
- **Contains**: Backups, image cache, large genomic files

## Quick Start

### Run with Docker Compose

```bash
# Start MINDEX service
docker-compose -f docker-compose.mindex.yml up -d

# View logs
docker-compose -f docker-compose.mindex.yml logs -f mindex

# Trigger manual sync
curl -X POST http://localhost:8000/api/mindex/sync
```

### Environment Variables

Create a `.env` file with:

```env
# NAS Storage (mount point on host)
MINDEX_HOST_PATH=/mnt/synology/mindex

# API Keys for higher rate limits
NCBI_API_KEY=your_ncbi_api_key
INATURALIST_API_KEY=your_inaturalist_token

# Sync configuration
MINDEX_SYNC_INTERVAL=24
MINDEX_MAX_RECORDS=100000
```

### Windows NAS Mount

```powershell
# Mount NAS share
net use Z: \\192.168.1.100\mindex /persistent:yes

# Set environment variable
$env:MINDEX_HOST_PATH = "Z:\mindex"
```

### Linux NAS Mount

```bash
# Add to /etc/fstab
//192.168.1.100/mindex /mnt/nas/mindex cifs credentials=/etc/nas-creds,uid=1000 0 0

# Create mount
sudo mount -a
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/api/mindex/stats` | GET | Database statistics |
| `/api/mindex/search?q=` | GET | Search species |
| `/api/mindex/taxa` | GET | List taxa (paginated) |
| `/api/mindex/taxa/{id}` | GET | Get taxon details |
| `/api/mindex/observations` | GET | List observations |
| `/api/mindex/etl-status` | GET | Scraper status |
| `/api/mindex/sync` | POST | Trigger manual sync |
| `/api/mindex/sync/{source}` | POST | Sync specific source |

## Database Schema

```sql
-- Species/Taxa table
CREATE TABLE species (
    id INTEGER PRIMARY KEY,
    source TEXT,
    source_id TEXT,
    scientific_name TEXT,
    common_name TEXT,
    rank TEXT,
    family TEXT,
    genus TEXT,
    -- ... full taxonomy
);

-- Observations table  
CREATE TABLE observations (
    id INTEGER PRIMARY KEY,
    source TEXT,
    species_id INTEGER,
    scientific_name TEXT,
    observed_on TEXT,
    latitude REAL,
    longitude REAL,
    photos TEXT,
    quality_grade TEXT
);

-- Genomic data table
CREATE TABLE genomic_data (
    id INTEGER PRIMARY KEY,
    source TEXT,
    organism_name TEXT,
    gene_name TEXT,
    sequence TEXT,
    genome_size TEXT
);
```

## Scraper Development

To add a new data source:

1. Create a new scraper in `mycosoft_mas/mindex/scrapers/`:

```python
from .base import BaseScraper, ScraperResult

class NewSourceScraper(BaseScraper):
    @property
    def source_name(self) -> str:
        return "NewSource"
    
    @property
    def base_url(self) -> str:
        return "https://api.newsource.org"
    
    async def search_species(self, query: str, limit: int = 100) -> ScraperResult:
        # Implementation
        pass
```

2. Register in `scrapers/__init__.py`
3. Add to manager's `sync_source` method

## Monitoring

MINDEX exposes Prometheus metrics at `/metrics`:

- `mindex_species_total` - Total species in database
- `mindex_observations_total` - Total observations
- `mindex_sync_duration_seconds` - Sync duration by source
- `mindex_sync_records_total` - Records synced by source

## Troubleshooting

### Service won't start
```bash
# Check if port is in use
netstat -an | grep 8000

# Check logs
docker-compose -f docker-compose.mindex.yml logs mindex
```

### NAS not mounting
```bash
# Check NAS is accessible
ping 192.168.1.100

# Check credentials
smbclient //192.168.1.100/mindex -U username
```

### Sync failing
```bash
# Check ETL status
curl http://localhost:8000/api/mindex/etl-status

# Check rate limits (iNaturalist: 60/min, NCBI: 3/sec)
# Wait and retry, or add API key for higher limits
```


# MINDEX - Mycological Index Data System

Central knowledge base for fungal information that continuously scrapes, organizes, and serves data from multiple sources.

## Data Sources

| Source | Data Type | Update Frequency |
|--------|-----------|------------------|
| **iNaturalist** | Species observations, photos, citizen science | Every 6 hours |
| **GBIF** | Global biodiversity occurrences | Every 12 hours |
| **MycoBank** | Taxonomic nomenclature, classifications | Daily |
| **FungiDB** | Genomic data, molecular biology | Daily |
| **GenBank** | NCBI sequences, genome assemblies | Daily |

## Storage Configuration

MINDEX uses network-attached storage for persistent data:

### Primary Storage (16TB Synology NAS)
- **Path**: `/mnt/nas/mindex`
- **Contains**: Main SQLite database, raw scraped data
- **Backup**: Daily to secondary storage

### Secondary Storage (26TB UniFi Dream Machine)
- **Path**: `/mnt/dream/mindex`
- **Contains**: Backups, image cache, large genomic files

## Quick Start

### Run with Docker Compose

```bash
# Start MINDEX service
docker-compose -f docker-compose.mindex.yml up -d

# View logs
docker-compose -f docker-compose.mindex.yml logs -f mindex

# Trigger manual sync
curl -X POST http://localhost:8000/api/mindex/sync
```

### Environment Variables

Create a `.env` file with:

```env
# NAS Storage (mount point on host)
MINDEX_HOST_PATH=/mnt/synology/mindex

# API Keys for higher rate limits
NCBI_API_KEY=your_ncbi_api_key
INATURALIST_API_KEY=your_inaturalist_token

# Sync configuration
MINDEX_SYNC_INTERVAL=24
MINDEX_MAX_RECORDS=100000
```

### Windows NAS Mount

```powershell
# Mount NAS share
net use Z: \\192.168.1.100\mindex /persistent:yes

# Set environment variable
$env:MINDEX_HOST_PATH = "Z:\mindex"
```

### Linux NAS Mount

```bash
# Add to /etc/fstab
//192.168.1.100/mindex /mnt/nas/mindex cifs credentials=/etc/nas-creds,uid=1000 0 0

# Create mount
sudo mount -a
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/api/mindex/stats` | GET | Database statistics |
| `/api/mindex/search?q=` | GET | Search species |
| `/api/mindex/taxa` | GET | List taxa (paginated) |
| `/api/mindex/taxa/{id}` | GET | Get taxon details |
| `/api/mindex/observations` | GET | List observations |
| `/api/mindex/etl-status` | GET | Scraper status |
| `/api/mindex/sync` | POST | Trigger manual sync |
| `/api/mindex/sync/{source}` | POST | Sync specific source |

## Database Schema

```sql
-- Species/Taxa table
CREATE TABLE species (
    id INTEGER PRIMARY KEY,
    source TEXT,
    source_id TEXT,
    scientific_name TEXT,
    common_name TEXT,
    rank TEXT,
    family TEXT,
    genus TEXT,
    -- ... full taxonomy
);

-- Observations table  
CREATE TABLE observations (
    id INTEGER PRIMARY KEY,
    source TEXT,
    species_id INTEGER,
    scientific_name TEXT,
    observed_on TEXT,
    latitude REAL,
    longitude REAL,
    photos TEXT,
    quality_grade TEXT
);

-- Genomic data table
CREATE TABLE genomic_data (
    id INTEGER PRIMARY KEY,
    source TEXT,
    organism_name TEXT,
    gene_name TEXT,
    sequence TEXT,
    genome_size TEXT
);
```

## Scraper Development

To add a new data source:

1. Create a new scraper in `mycosoft_mas/mindex/scrapers/`:

```python
from .base import BaseScraper, ScraperResult

class NewSourceScraper(BaseScraper):
    @property
    def source_name(self) -> str:
        return "NewSource"
    
    @property
    def base_url(self) -> str:
        return "https://api.newsource.org"
    
    async def search_species(self, query: str, limit: int = 100) -> ScraperResult:
        # Implementation
        pass
```

2. Register in `scrapers/__init__.py`
3. Add to manager's `sync_source` method

## Monitoring

MINDEX exposes Prometheus metrics at `/metrics`:

- `mindex_species_total` - Total species in database
- `mindex_observations_total` - Total observations
- `mindex_sync_duration_seconds` - Sync duration by source
- `mindex_sync_records_total` - Records synced by source

## Troubleshooting

### Service won't start
```bash
# Check if port is in use
netstat -an | grep 8000

# Check logs
docker-compose -f docker-compose.mindex.yml logs mindex
```

### NAS not mounting
```bash
# Check NAS is accessible
ping 192.168.1.100

# Check credentials
smbclient //192.168.1.100/mindex -U username
```

### Sync failing
```bash
# Check ETL status
curl http://localhost:8000/api/mindex/etl-status

# Check rate limits (iNaturalist: 60/min, NCBI: 3/sec)
# Wait and retry, or add API key for higher limits
```

# MINDEX - Mycological Index Data System

Central knowledge base for fungal information that continuously scrapes, organizes, and serves data from multiple sources.

## Data Sources

| Source | Data Type | Update Frequency |
|--------|-----------|------------------|
| **iNaturalist** | Species observations, photos, citizen science | Every 6 hours |
| **GBIF** | Global biodiversity occurrences | Every 12 hours |
| **MycoBank** | Taxonomic nomenclature, classifications | Daily |
| **FungiDB** | Genomic data, molecular biology | Daily |
| **GenBank** | NCBI sequences, genome assemblies | Daily |

## Storage Configuration

MINDEX uses network-attached storage for persistent data:

### Primary Storage (16TB Synology NAS)
- **Path**: `/mnt/nas/mindex`
- **Contains**: Main SQLite database, raw scraped data
- **Backup**: Daily to secondary storage

### Secondary Storage (26TB UniFi Dream Machine)
- **Path**: `/mnt/dream/mindex`
- **Contains**: Backups, image cache, large genomic files

## Quick Start

### Run with Docker Compose

```bash
# Start MINDEX service
docker-compose -f docker-compose.mindex.yml up -d

# View logs
docker-compose -f docker-compose.mindex.yml logs -f mindex

# Trigger manual sync
curl -X POST http://localhost:8000/api/mindex/sync
```

### Environment Variables

Create a `.env` file with:

```env
# NAS Storage (mount point on host)
MINDEX_HOST_PATH=/mnt/synology/mindex

# API Keys for higher rate limits
NCBI_API_KEY=your_ncbi_api_key
INATURALIST_API_KEY=your_inaturalist_token

# Sync configuration
MINDEX_SYNC_INTERVAL=24
MINDEX_MAX_RECORDS=100000
```

### Windows NAS Mount

```powershell
# Mount NAS share
net use Z: \\192.168.1.100\mindex /persistent:yes

# Set environment variable
$env:MINDEX_HOST_PATH = "Z:\mindex"
```

### Linux NAS Mount

```bash
# Add to /etc/fstab
//192.168.1.100/mindex /mnt/nas/mindex cifs credentials=/etc/nas-creds,uid=1000 0 0

# Create mount
sudo mount -a
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
| `/api/mindex/stats` | GET | Database statistics |
| `/api/mindex/search?q=` | GET | Search species |
| `/api/mindex/taxa` | GET | List taxa (paginated) |
| `/api/mindex/taxa/{id}` | GET | Get taxon details |
| `/api/mindex/observations` | GET | List observations |
| `/api/mindex/etl-status` | GET | Scraper status |
| `/api/mindex/sync` | POST | Trigger manual sync |
| `/api/mindex/sync/{source}` | POST | Sync specific source |

## Database Schema

```sql
-- Species/Taxa table
CREATE TABLE species (
    id INTEGER PRIMARY KEY,
    source TEXT,
    source_id TEXT,
    scientific_name TEXT,
    common_name TEXT,
    rank TEXT,
    family TEXT,
    genus TEXT,
    -- ... full taxonomy
);

-- Observations table  
CREATE TABLE observations (
    id INTEGER PRIMARY KEY,
    source TEXT,
    species_id INTEGER,
    scientific_name TEXT,
    observed_on TEXT,
    latitude REAL,
    longitude REAL,
    photos TEXT,
    quality_grade TEXT
);

-- Genomic data table
CREATE TABLE genomic_data (
    id INTEGER PRIMARY KEY,
    source TEXT,
    organism_name TEXT,
    gene_name TEXT,
    sequence TEXT,
    genome_size TEXT
);
```

## Scraper Development

To add a new data source:

1. Create a new scraper in `mycosoft_mas/mindex/scrapers/`:

```python
from .base import BaseScraper, ScraperResult

class NewSourceScraper(BaseScraper):
    @property
    def source_name(self) -> str:
        return "NewSource"
    
    @property
    def base_url(self) -> str:
        return "https://api.newsource.org"
    
    async def search_species(self, query: str, limit: int = 100) -> ScraperResult:
        # Implementation
        pass
```

2. Register in `scrapers/__init__.py`
3. Add to manager's `sync_source` method

## Monitoring

MINDEX exposes Prometheus metrics at `/metrics`:

- `mindex_species_total` - Total species in database
- `mindex_observations_total` - Total observations
- `mindex_sync_duration_seconds` - Sync duration by source
- `mindex_sync_records_total` - Records synced by source

## Troubleshooting

### Service won't start
```bash
# Check if port is in use
netstat -an | grep 8000

# Check logs
docker-compose -f docker-compose.mindex.yml logs mindex
```

### NAS not mounting
```bash
# Check NAS is accessible
ping 192.168.1.100

# Check credentials
smbclient //192.168.1.100/mindex -U username
```

### Sync failing
```bash
# Check ETL status
curl http://localhost:8000/api/mindex/etl-status

# Check rate limits (iNaturalist: 60/min, NCBI: 3/sec)
# Wait and retry, or add API key for higher limits
```





