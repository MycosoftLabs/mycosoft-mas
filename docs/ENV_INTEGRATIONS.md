# Global Integration Environment Variables

This document lists all API keys and environment variables required for the Mycosoft MAS global integration system.

## Quick Start

Copy the relevant variables to your `.env` file and fill in your API keys.

---

## Space & Weather APIs

### NASA APIs
```env
# NASA API Key - Get from https://api.nasa.gov/
# DEMO_KEY works for testing but has rate limits
NASA_API_KEY=your_nasa_api_key
```

**Free APIs (no key required):**
- NOAA Space Weather Prediction Center
- SOHO/STEREO Solar Data
- GOES Satellite Data
- ACE/DSCOVR Real-time Solar Wind

### Weather APIs
```env
# OpenWeatherMap - https://openweathermap.org/api
OPENWEATHERMAP_API_KEY=your_openweathermap_key
```

---

## Environmental Sensors

### Air Quality
```env
# OpenAQ - https://openaq.org/ (free tier available)
OPENAQ_API_KEY=your_openaq_api_key

# EPA AirNow - https://docs.airnowapi.org/
EPA_AIRNOW_API_KEY=your_airnow_api_key

# PurpleAir - https://www2.purpleair.com/community/faq#hc-access-the-purpleair-api
PURPLEAIR_API_KEY=your_purpleair_read_key

# IQAir - https://www.iqair.com/air-pollution-data-api
IQAIR_API_KEY=your_iqair_api_key
```

### Radiation & Environmental
```env
# Safecast - https://api.safecast.org/ (optional, works without key)
SAFECAST_API_KEY=your_safecast_api_key

# BreezoMeter - https://www.breezometer.com/air-quality-api
BREEZOMETER_API_KEY=your_breezometer_api_key

# Ambee - https://www.getambee.com/api
AMBEE_API_KEY=your_ambee_api_key

# CO2 Signal - https://docs.co2signal.com/
CO2_SIGNAL_API_KEY=your_co2_signal_key
```

---

## Earth Science (Free APIs)

Most earth science APIs are free and don't require API keys:

- **USGS Earthquake API** - https://earthquake.usgs.gov/fdsnws/event/1/
- **NOAA Tides & Currents** - https://api.tidesandcurrents.noaa.gov/
- **NDBC Buoy Data** - https://www.ndbc.noaa.gov/
- **USGS Water Services** - https://waterservices.usgs.gov/
- **IRIS Seismic Data** - https://service.iris.edu/

### Optional Keys
```env
# Marine Traffic AIS - https://www.marinetraffic.com/en/ais-api-services
MARINE_TRAFFIC_API_KEY=your_marine_traffic_key
```

---

## Financial Markets

### Cryptocurrency
```env
# CoinMarketCap - https://coinmarketcap.com/api/
COINMARKETCAP_API_KEY=your_cmc_api_key

# CoinGecko is free and doesn't require a key
```

### Stocks & Forex
```env
# Alpha Vantage - https://www.alphavantage.co/support/#api-key
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key

# Polygon.io - https://polygon.io/
POLYGON_API_KEY=your_polygon_api_key

# Finnhub - https://finnhub.io/
FINNHUB_API_KEY=your_finnhub_api_key

# Yahoo Finance (unofficial, use with caution)
# No API key required for basic data
```

---

## Analytics & Data Science

```env
# Amplitude - https://amplitude.com/
AMPLITUDE_API_KEY=your_amplitude_api_key
AMPLITUDE_SECRET_KEY=your_amplitude_secret

# Mixpanel - https://mixpanel.com/
MIXPANEL_TOKEN=your_mixpanel_token
MIXPANEL_API_SECRET=your_mixpanel_api_secret

# Segment - https://segment.com/
SEGMENT_WRITE_KEY=your_segment_write_key

# PostHog - https://posthog.com/
POSTHOG_API_KEY=your_posthog_api_key
POSTHOG_PROJECT_ID=your_posthog_project_id

# Wolfram Alpha - https://products.wolframalpha.com/api/
WOLFRAM_APP_ID=your_wolfram_app_id
```

---

## Automation Platforms

```env
# Zapier - Create a Zap with "Webhooks by Zapier" trigger
ZAPIER_WEBHOOK_URL=https://hooks.zapier.com/hooks/catch/xxxxx/xxxxx/

# IFTTT - https://ifttt.com/maker_webhooks
IFTTT_WEBHOOK_KEY=your_ifttt_maker_key

# Make (Integromat) - Create a scenario with Webhook trigger
MAKE_WEBHOOK_URL=https://hook.us1.make.com/xxxxx

# Pipedream - https://pipedream.com/
PIPEDREAM_API_KEY=your_pipedream_api_key
PIPEDREAM_ENDPOINT=your_endpoint_id

# Activepieces - Create a flow with Webhook trigger
ACTIVEPIECES_WEBHOOK_URL=https://cloud.activepieces.com/api/v1/webhooks/xxxxx
```

---

## AI & Voice

```env
# OpenAI / ChatGPT - https://platform.openai.com/api-keys
OPENAI_API_KEY=your_openai_api_key

# Anthropic Claude - https://console.anthropic.com/
ANTHROPIC_API_KEY=your_anthropic_api_key

# ElevenLabs - https://elevenlabs.io/
ELEVENLABS_API_KEY=your_elevenlabs_api_key
ELEVENLABS_VOICE_ID=your_voice_id
```

---

## Defense & Government (Restricted)

These integrations require proper authorization and clearance. Contact your security administrator.

```env
# Palantir Foundry (requires enterprise agreement)
PALANTIR_CLIENT_ID=your_palantir_client_id
PALANTIR_CLIENT_SECRET=your_palantir_client_secret
PALANTIR_FOUNDRY_URL=https://your-instance.palantirfoundry.com

# Anduril SDK (requires defense contractor access)
ANDURIL_API_KEY=your_anduril_api_key
ANDURIL_SDK_TOKEN=your_anduril_sdk_token

# Platform One (DoD) - Requires CAC authentication
PLATFORM_ONE_CLIENT_ID=your_p1_client_id
PLATFORM_ONE_CLIENT_SECRET=your_p1_client_secret
# Note: Platform One uses OAuth2 via https://login.dso.mil
```

---

## n8n Workflow Configuration

These environment variables configure the n8n workflow routing:

```env
# Workflow IDs (set after importing workflows to n8n)
WORKFLOW_ID_NATIVE_AI=1
WORKFLOW_ID_NATIVE_COMMS=2
WORKFLOW_ID_NATIVE_DATA=3
WORKFLOW_ID_NATIVE_DEVTOOLS=4
WORKFLOW_ID_NATIVE_PRODUCTIVITY=5
WORKFLOW_ID_NATIVE_FINANCE=6
WORKFLOW_ID_NATIVE_OPS=7
WORKFLOW_ID_NATIVE_SECURITY=8
WORKFLOW_ID_NATIVE_UTILITY=9
WORKFLOW_ID_NATIVE_SPACE_WEATHER=10
WORKFLOW_ID_NATIVE_ENVIRONMENTAL=11
WORKFLOW_ID_NATIVE_EARTH_SCIENCE=12
WORKFLOW_ID_NATIVE_ANALYTICS=13
WORKFLOW_ID_NATIVE_AUTOMATION=14
WORKFLOW_ID_GENERIC_CONNECTOR=15
WORKFLOW_ID_DEFENSE_CONNECTOR=16
AUDIT_LOGGER_WORKFLOW_ID=17
```

---

## API Key Resources

### Free Tier APIs
| Service | Free Tier | Sign Up |
|---------|-----------|---------|
| NASA | Unlimited (with key) | https://api.nasa.gov/ |
| OpenAQ | 10,000 req/day | https://openaq.org/ |
| CoinGecko | 30 req/min | No signup needed |
| USGS | Unlimited | No signup needed |
| NOAA | Unlimited | No signup needed |
| Alpha Vantage | 5 req/min | https://www.alphavantage.co/ |

### Paid APIs (with free tiers)
| Service | Free Tier | Paid From |
|---------|-----------|-----------|
| CoinMarketCap | 10,000 credits/month | $29/month |
| PurpleAir | 100,000 points/week | Contact sales |
| BreezoMeter | 1,000 calls/month | Custom pricing |
| Amplitude | 10M events/month | Custom pricing |

---

## Setup Checklist

1. [ ] Copy required variables to `.env`
2. [ ] Sign up for free tier APIs (NASA, Alpha Vantage, etc.)
3. [ ] Configure n8n workflow IDs after import
4. [ ] Set up automation platform webhooks (Zapier, IFTTT)
5. [ ] Test integrations with the health check endpoint
6. [ ] For defense integrations, contact security administrator

---

## Testing

Test your configuration by calling the health check endpoints:

```bash
# Test space weather
curl http://localhost:3000/api/mas/space-weather?action=solar_wind

# Test environmental
curl http://localhost:3000/api/mas/environmental?action=countries

# Test earth science
curl http://localhost:3000/api/mas/earth-science?action=earthquakes

# Test financial
curl http://localhost:3000/api/mas/financial?action=crypto_prices
```

---

## Support

For integration issues:
- Check the n8n workflow execution logs
- Verify API key format and permissions
- Check rate limits for the specific API
- Review the integration registry at `n8n/registry/integration_registry.json`
