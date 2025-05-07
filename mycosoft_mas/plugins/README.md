# Mycosoft MAS Plugins

This directory contains plugins for the Mycosoft Multi-Agent System (MAS).

## Available Plugins

### Fungal Knowledge Graph

The Fungal Knowledge Graph plugin provides a comprehensive knowledge base for fungal species and their relationships with other organisms. It uses Oxigraph as the underlying RDF store and provides a bidirectional interface for the MAS.

#### Features

- RDF-based knowledge representation
- Integration with Oxigraph for scalable storage
- NetworkX-based graph traversal
- Bidirectional data flow with the MAS
- Automatic synchronization with other agents

#### Configuration

The plugin can be configured using the `fungal_knowledge_config.json` file:

```json
{
    "oxigraph_url": "http://localhost:7878",
    "data_dir": "data/fungal_knowledge",
    "sync_interval": 60,
    "update_interval": 300,
    "namespaces": {
        "fungi": "http://mycosoft.org/fungi/",
        "plants": "http://mycosoft.org/plants/",
        "animals": "http://mycosoft.org/animals/",
        "bacteria": "http://mycosoft.org/bacteria/",
        "viruses": "http://mycosoft.org/viruses/",
        "relations": "http://mycosoft.org/relations/"
    }
}
```

#### Usage

1. Start the Oxigraph server:
   ```bash
   ./scripts/start_fungal_knowledge.sh  # Linux/Mac
   # or
   ./scripts/start_fungal_knowledge.ps1  # Windows
   ```

2. The knowledge graph will automatically integrate with the MycologyBioAgent and other agents in the MAS.

3. Data can be added to the knowledge graph through the MAS or directly using the plugin's API.

#### Integration with MAS

The fungal knowledge graph integrates with the MAS through the MycologyBioAgent. It:

1. Receives data from the import and analysis queues
2. Updates the knowledge graph with new information
3. Notifies other agents about updates
4. Provides query capabilities for other agents

### Bio Data Translator

The Bio Data Translator plugin provides functionality for translating between different biological data formats.

## BioDataTranslator Plugin

The BioDataTranslator plugin enables data sharing and normalization between bio agents in the Eliza framework. It translates biological, chemical, and physics data into formats compatible with the MycoDAO agent cluster.

### Features

- **Schema Management**: Register, update, and delete data schemas for different data types and formats.
- **Translation Rules**: Create, update, and delete translation rules between schemas.
- **Data Translation**: Translate data from one schema to another using defined rules.
- **Ontology Support**: Maintain an ontology for semantic mapping between different data types.
- **Agent Registration**: Register and unregister agents with the translator.
- **Path Finding**: Find translation paths between schemas that don't have direct translation rules.
- **Composite Rules**: Create composite translation rules for multi-step translations.

### Data Categories

- Biology
- Chemistry
- Physics
- Mixed

### Data Formats

- JSON
- CSV
- XML
- RDF
- OWL
- FASTA
- GFF
- VCF
- BAM
- PDB
- TSV
- Binary
- Custom

### Data Sources

- NCBI
- UniProt
- PDB
- KEGG
- MetaCyc
- Ensembl
- PubMed
- ChEBI
- PubChem
- Custom

### Usage

```python
from plugins import BioDataTranslator

# Initialize the plugin
translator = BioDataTranslator({
    'plugin_id': 'bio_data_translator',
    'name': 'Bio Data Translator',
    'data_directory': 'data/bio_translator',
    'output_directory': 'output/bio_translator'
})

# Initialize the plugin
await translator.initialize()

# Register a schema
schema_result = await translator.register_schema({
    'name': 'Mycology Species Schema',
    'category': 'BIOLOGY',
    'format': 'JSON',
    'source': 'CUSTOM',
    'version': '1.0',
    'schema_definition': {
        'id': 'string',
        'name': 'string',
        'scientific_name': 'string',
        'common_name': 'string',
        'taxonomy': 'object',
        'habitat': 'string',
        'description': 'string'
    }
})

# Create a translation rule
rule_result = await translator.create_translation_rule({
    'name': 'Mycology to DAO Schema Rule',
    'source_schema_id': schema_result['schema_id'],
    'target_schema_id': 'dao_schema_id',
    'mapping': {
        'id': 'species_id',
        'name': 'species_name',
        'scientific_name': 'scientific_name',
        'common_name': 'common_name',
        'taxonomy': 'taxonomy_data',
        'habitat': 'habitat_info',
        'description': 'description'
    },
    'transformation_functions': {
        'transform_taxonomy': """
def transform_taxonomy(data):
    # Transform taxonomy data
    taxonomy = data.get('taxonomy', {})
    data['taxonomy_data'] = {
        'kingdom': taxonomy.get('kingdom', ''),
        'phylum': taxonomy.get('phylum', ''),
        'class': taxonomy.get('class', ''),
        'order': taxonomy.get('order', ''),
        'family': taxonomy.get('family', ''),
        'genus': taxonomy.get('genus', ''),
        'species': taxonomy.get('species', '')
    }
    return data
"""
    }
})

# Translate data
translation_result = await translator.translate_data(
    data={
        'id': 'species_123',
        'name': 'Reishi',
        'scientific_name': 'Ganoderma lucidum',
        'common_name': 'Reishi',
        'taxonomy': {
            'kingdom': 'Fungi',
            'phylum': 'Basidiomycota',
            'class': 'Agaricomycetes',
            'order': 'Polyporales',
            'family': 'Ganodermataceae',
            'genus': 'Ganoderma',
            'species': 'lucidum'
        },
        'habitat': 'Deciduous forests',
        'description': 'A medicinal mushroom with various health benefits.'
    },
    source_schema_id=schema_result['schema_id'],
    target_schema_id='dao_schema_id'
)

# Get translated data
translated_data = await translator.get_translated_data(translation_result['translation_id'])
```

### Integration with MycoDAO Agent Cluster

The BioDataTranslator plugin is designed to work seamlessly with the MycoDAO agent cluster. It provides a standardized way to translate data between different bio agents and the MycoDAO agent, ensuring that all data is in a compatible format.

### Directory Structure

- `data/bio_translator/`: Directory for storing plugin data
  - `schemas/`: Directory for storing data schemas
  - `rules/`: Directory for storing translation rules
  - `translated/`: Directory for storing translated data
  - `agents/`: Directory for storing agent information
  - `ontology/`: Directory for storing the ontology
- `output/bio_translator/`: Directory for storing plugin output 