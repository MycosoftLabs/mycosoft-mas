# MYCA NLQ (Natural Language Query)

**Component**: Parse and execute natural language queries  
**Status**: Implemented

## Location

- `mycosoft_mas/core/routers/nlq_api.py`
- Prefix: `/api/nlq`

## Endpoints

- POST /api/nlq/parse - Intent detection via LLM
- POST /api/nlq/execute - Route to SearchAgent, Metabase, MINDEX
- POST /api/nlq/query - Full parse plus execute

## Intents

- search - SearchAgent (keyword, semantic, fuzzy)
- query_metabase - Metabase LLM-generated SQL
- mindex - MINDEX direct
- unknown - Fallback

## Routing

- Parse uses MAS Brain for intent classification
- Execute routes to SearchAgent, Metabase, or MINDEX
