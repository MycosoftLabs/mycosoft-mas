# Eliza Framework Plugins

This directory contains plugins that extend the functionality of the Eliza framework.

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