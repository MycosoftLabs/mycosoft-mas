"""
Financial Markets Client

Provides access to financial market data from:
- CoinMarketCap (Cryptocurrency)
- Alpha Vantage (Stocks, Forex, Crypto)
- Polygon.io (Market Data)
- Finnhub (Stocks, News)
- Yahoo Finance (Stocks, Options)

Environment Variables:
    COINMARKETCAP_API_KEY: CoinMarketCap API key
    ALPHA_VANTAGE_API_KEY: Alpha Vantage API key
    POLYGON_API_KEY: Polygon.io API key
    FINNHUB_API_KEY: Finnhub API key
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)


class FinancialMarketsClient:
    """
    Client for financial market data APIs.
    
    Provides unified access to:
    - Cryptocurrency prices and market data
    - Stock quotes and historical data
    - Forex rates
    - Financial news
    - Market indicators
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the financial markets client."""
        self.config = config or {}
        self.timeout = self.config.get("timeout", 30)
        
        # API Keys
        self.coinmarketcap_key = self.config.get("coinmarketcap_key") or os.getenv("COINMARKETCAP_API_KEY", "")
        self.alpha_vantage_key = self.config.get("alpha_vantage_key") or os.getenv("ALPHA_VANTAGE_API_KEY", "")
        self.polygon_key = self.config.get("polygon_key") or os.getenv("POLYGON_API_KEY", "")
        self.finnhub_key = self.config.get("finnhub_key") or os.getenv("FINNHUB_API_KEY", "")
        
        self._client: Optional[httpx.AsyncClient] = None
        logger.info("Financial markets client initialized")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of financial APIs."""
        try:
            client = await self._get_client()
            # Check CoinGecko (free, no key needed)
            response = await client.get(
                "https://api.coingecko.com/api/v3/ping"
            )
            return {
                "status": "ok" if response.status_code == 200 else "degraded",
                "coingecko": response.status_code == 200,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    # CoinMarketCap APIs
    async def get_crypto_listings(
        self,
        start: int = 1,
        limit: int = 100,
        convert: str = "USD"
    ) -> Dict[str, Any]:
        """Get cryptocurrency listings from CoinMarketCap."""
        if not self.coinmarketcap_key:
            raise ValueError("COINMARKETCAP_API_KEY is required")
        
        client = await self._get_client()
        response = await client.get(
            "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest",
            params={"start": start, "limit": limit, "convert": convert},
            headers={"X-CMC_PRO_API_KEY": self.coinmarketcap_key}
        )
        response.raise_for_status()
        return response.json()
    
    async def get_crypto_quotes(
        self,
        symbols: List[str],
        convert: str = "USD"
    ) -> Dict[str, Any]:
        """Get cryptocurrency quotes from CoinMarketCap."""
        if not self.coinmarketcap_key:
            raise ValueError("COINMARKETCAP_API_KEY is required")
        
        client = await self._get_client()
        response = await client.get(
            "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest",
            params={"symbol": ",".join(symbols), "convert": convert},
            headers={"X-CMC_PRO_API_KEY": self.coinmarketcap_key}
        )
        response.raise_for_status()
        return response.json()
    
    async def get_crypto_info(
        self,
        symbols: List[str]
    ) -> Dict[str, Any]:
        """Get cryptocurrency metadata from CoinMarketCap."""
        if not self.coinmarketcap_key:
            raise ValueError("COINMARKETCAP_API_KEY is required")
        
        client = await self._get_client()
        response = await client.get(
            "https://pro-api.coinmarketcap.com/v1/cryptocurrency/info",
            params={"symbol": ",".join(symbols)},
            headers={"X-CMC_PRO_API_KEY": self.coinmarketcap_key}
        )
        response.raise_for_status()
        return response.json()
    
    # Alpha Vantage APIs
    async def get_stock_quote(
        self,
        symbol: str
    ) -> Dict[str, Any]:
        """Get stock quote from Alpha Vantage."""
        if not self.alpha_vantage_key:
            raise ValueError("ALPHA_VANTAGE_API_KEY is required")
        
        client = await self._get_client()
        response = await client.get(
            "https://www.alphavantage.co/query",
            params={
                "function": "GLOBAL_QUOTE",
                "symbol": symbol,
                "apikey": self.alpha_vantage_key
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def get_stock_daily(
        self,
        symbol: str,
        outputsize: str = "compact"
    ) -> Dict[str, Any]:
        """Get daily stock data from Alpha Vantage."""
        if not self.alpha_vantage_key:
            raise ValueError("ALPHA_VANTAGE_API_KEY is required")
        
        client = await self._get_client()
        response = await client.get(
            "https://www.alphavantage.co/query",
            params={
                "function": "TIME_SERIES_DAILY",
                "symbol": symbol,
                "outputsize": outputsize,
                "apikey": self.alpha_vantage_key
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def get_forex_rate(
        self,
        from_currency: str,
        to_currency: str
    ) -> Dict[str, Any]:
        """Get forex exchange rate from Alpha Vantage."""
        if not self.alpha_vantage_key:
            raise ValueError("ALPHA_VANTAGE_API_KEY is required")
        
        client = await self._get_client()
        response = await client.get(
            "https://www.alphavantage.co/query",
            params={
                "function": "CURRENCY_EXCHANGE_RATE",
                "from_currency": from_currency,
                "to_currency": to_currency,
                "apikey": self.alpha_vantage_key
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def search_symbols(
        self,
        keywords: str
    ) -> Dict[str, Any]:
        """Search for stock symbols from Alpha Vantage."""
        if not self.alpha_vantage_key:
            raise ValueError("ALPHA_VANTAGE_API_KEY is required")
        
        client = await self._get_client()
        response = await client.get(
            "https://www.alphavantage.co/query",
            params={
                "function": "SYMBOL_SEARCH",
                "keywords": keywords,
                "apikey": self.alpha_vantage_key
            }
        )
        response.raise_for_status()
        return response.json()
    
    # Polygon.io APIs
    async def get_polygon_quote(
        self,
        ticker: str
    ) -> Dict[str, Any]:
        """Get stock quote from Polygon.io."""
        if not self.polygon_key:
            raise ValueError("POLYGON_API_KEY is required")
        
        client = await self._get_client()
        response = await client.get(
            f"https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers/{ticker}",
            params={"apiKey": self.polygon_key}
        )
        response.raise_for_status()
        return response.json()
    
    async def get_polygon_aggregates(
        self,
        ticker: str,
        multiplier: int = 1,
        timespan: str = "day",
        from_date: str = None,
        to_date: str = None
    ) -> Dict[str, Any]:
        """Get aggregate bars from Polygon.io."""
        if not self.polygon_key:
            raise ValueError("POLYGON_API_KEY is required")
        
        client = await self._get_client()
        response = await client.get(
            f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from_date}/{to_date}",
            params={"apiKey": self.polygon_key}
        )
        response.raise_for_status()
        return response.json()
    
    # Finnhub APIs
    async def get_finnhub_quote(
        self,
        symbol: str
    ) -> Dict[str, Any]:
        """Get stock quote from Finnhub."""
        if not self.finnhub_key:
            raise ValueError("FINNHUB_API_KEY is required")
        
        client = await self._get_client()
        response = await client.get(
            "https://finnhub.io/api/v1/quote",
            params={"symbol": symbol, "token": self.finnhub_key}
        )
        response.raise_for_status()
        return response.json()
    
    async def get_company_news(
        self,
        symbol: str,
        from_date: str,
        to_date: str
    ) -> List[Dict[str, Any]]:
        """Get company news from Finnhub."""
        if not self.finnhub_key:
            raise ValueError("FINNHUB_API_KEY is required")
        
        client = await self._get_client()
        response = await client.get(
            "https://finnhub.io/api/v1/company-news",
            params={
                "symbol": symbol,
                "from": from_date,
                "to": to_date,
                "token": self.finnhub_key
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def get_market_news(
        self,
        category: str = "general"
    ) -> List[Dict[str, Any]]:
        """Get market news from Finnhub."""
        if not self.finnhub_key:
            raise ValueError("FINNHUB_API_KEY is required")
        
        client = await self._get_client()
        response = await client.get(
            "https://finnhub.io/api/v1/news",
            params={"category": category, "token": self.finnhub_key}
        )
        response.raise_for_status()
        return response.json()
    
    # CoinGecko (Free API)
    async def get_coingecko_prices(
        self,
        ids: List[str],
        vs_currencies: str = "usd"
    ) -> Dict[str, Any]:
        """Get cryptocurrency prices from CoinGecko (free)."""
        client = await self._get_client()
        response = await client.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={
                "ids": ",".join(ids),
                "vs_currencies": vs_currencies,
                "include_24hr_change": "true",
                "include_market_cap": "true"
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def get_coingecko_markets(
        self,
        vs_currency: str = "usd",
        order: str = "market_cap_desc",
        per_page: int = 100
    ) -> List[Dict[str, Any]]:
        """Get cryptocurrency market data from CoinGecko."""
        client = await self._get_client()
        response = await client.get(
            "https://api.coingecko.com/api/v3/coins/markets",
            params={
                "vs_currency": vs_currency,
                "order": order,
                "per_page": per_page,
                "sparkline": "false"
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
        logger.info("Financial markets client closed")
