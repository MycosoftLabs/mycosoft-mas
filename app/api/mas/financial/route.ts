import { NextRequest, NextResponse } from "next/server";

const COINMARKETCAP_KEY = process.env.COINMARKETCAP_API_KEY || "";
const ALPHA_VANTAGE_KEY = process.env.ALPHA_VANTAGE_API_KEY || "";
const FINNHUB_KEY = process.env.FINNHUB_API_KEY || "";

interface FinancialRequest {
  action: string;
  params?: {
    symbols?: string[];
    symbol?: string;
    ids?: string[];
    limit?: number;
    convert?: string;
    from_currency?: string;
    to_currency?: string;
    from_date?: string;
    to_date?: string;
  };
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const action = searchParams.get("action") || "crypto_prices";
  const ids = searchParams.get("ids")?.split(",") || ["bitcoin", "ethereum"];

  try {
    let data;

    switch (action) {
      case "crypto_prices":
        data = await fetchCoinGeckoPrices(ids);
        break;
      case "crypto_markets":
        data = await fetchCoinGeckoMarkets();
        break;
      default:
        data = await fetchCoinGeckoPrices(ids);
    }

    return NextResponse.json({
      success: true,
      action,
      data,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body: FinancialRequest = await request.json();
    const { action, params } = body;

    let data;

    switch (action) {
      case "crypto_listings":
        if (!COINMARKETCAP_KEY) {
          return NextResponse.json(
            { success: false, error: "COINMARKETCAP_API_KEY not configured" },
            { status: 500 }
          );
        }
        data = await fetchCMCListings(params?.limit || 100);
        break;

      case "crypto_quotes":
        if (!COINMARKETCAP_KEY) {
          return NextResponse.json(
            { success: false, error: "COINMARKETCAP_API_KEY not configured" },
            { status: 500 }
          );
        }
        if (!params?.symbols?.length) {
          return NextResponse.json(
            { success: false, error: "symbols required" },
            { status: 400 }
          );
        }
        data = await fetchCMCQuotes(params.symbols, params.convert || "USD");
        break;

      case "stock_quote":
        if (!ALPHA_VANTAGE_KEY) {
          return NextResponse.json(
            { success: false, error: "ALPHA_VANTAGE_API_KEY not configured" },
            { status: 500 }
          );
        }
        if (!params?.symbol) {
          return NextResponse.json(
            { success: false, error: "symbol required" },
            { status: 400 }
          );
        }
        data = await fetchAlphaVantageQuote(params.symbol);
        break;

      case "forex_rate":
        if (!ALPHA_VANTAGE_KEY) {
          return NextResponse.json(
            { success: false, error: "ALPHA_VANTAGE_API_KEY not configured" },
            { status: 500 }
          );
        }
        if (!params?.from_currency || !params?.to_currency) {
          return NextResponse.json(
            { success: false, error: "from_currency and to_currency required" },
            { status: 400 }
          );
        }
        data = await fetchForexRate(params.from_currency, params.to_currency);
        break;

      case "finnhub_quote":
        if (!FINNHUB_KEY) {
          return NextResponse.json(
            { success: false, error: "FINNHUB_API_KEY not configured" },
            { status: 500 }
          );
        }
        if (!params?.symbol) {
          return NextResponse.json(
            { success: false, error: "symbol required" },
            { status: 400 }
          );
        }
        data = await fetchFinnhubQuote(params.symbol);
        break;

      case "market_news":
        if (!FINNHUB_KEY) {
          return NextResponse.json(
            { success: false, error: "FINNHUB_API_KEY not configured" },
            { status: 500 }
          );
        }
        data = await fetchMarketNews();
        break;

      default:
        return NextResponse.json(
          { success: false, error: `Unknown action: ${action}` },
          { status: 400 }
        );
    }

    return NextResponse.json({
      success: true,
      action,
      data,
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
        timestamp: new Date().toISOString(),
      },
      { status: 500 }
    );
  }
}

// CoinGecko (Free API)
async function fetchCoinGeckoPrices(ids: string[]) {
  const url = new URL("https://api.coingecko.com/api/v3/simple/price");
  url.searchParams.set("ids", ids.join(","));
  url.searchParams.set("vs_currencies", "usd");
  url.searchParams.set("include_24hr_change", "true");
  url.searchParams.set("include_market_cap", "true");

  const response = await fetch(url.toString());
  if (!response.ok) throw new Error(`CoinGecko API error: ${response.status}`);
  return response.json();
}

async function fetchCoinGeckoMarkets() {
  const url = new URL("https://api.coingecko.com/api/v3/coins/markets");
  url.searchParams.set("vs_currency", "usd");
  url.searchParams.set("order", "market_cap_desc");
  url.searchParams.set("per_page", "100");
  url.searchParams.set("sparkline", "false");

  const response = await fetch(url.toString());
  if (!response.ok) throw new Error(`CoinGecko API error: ${response.status}`);
  return response.json();
}

// CoinMarketCap
async function fetchCMCListings(limit: number) {
  const url = new URL(
    "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
  );
  url.searchParams.set("limit", limit.toString());
  url.searchParams.set("convert", "USD");

  const response = await fetch(url.toString(), {
    headers: { "X-CMC_PRO_API_KEY": COINMARKETCAP_KEY },
  });
  if (!response.ok) throw new Error(`CMC API error: ${response.status}`);
  return response.json();
}

async function fetchCMCQuotes(symbols: string[], convert: string) {
  const url = new URL(
    "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
  );
  url.searchParams.set("symbol", symbols.join(","));
  url.searchParams.set("convert", convert);

  const response = await fetch(url.toString(), {
    headers: { "X-CMC_PRO_API_KEY": COINMARKETCAP_KEY },
  });
  if (!response.ok) throw new Error(`CMC API error: ${response.status}`);
  return response.json();
}

// Alpha Vantage
async function fetchAlphaVantageQuote(symbol: string) {
  const url = new URL("https://www.alphavantage.co/query");
  url.searchParams.set("function", "GLOBAL_QUOTE");
  url.searchParams.set("symbol", symbol);
  url.searchParams.set("apikey", ALPHA_VANTAGE_KEY);

  const response = await fetch(url.toString());
  if (!response.ok)
    throw new Error(`Alpha Vantage API error: ${response.status}`);
  return response.json();
}

async function fetchForexRate(fromCurrency: string, toCurrency: string) {
  const url = new URL("https://www.alphavantage.co/query");
  url.searchParams.set("function", "CURRENCY_EXCHANGE_RATE");
  url.searchParams.set("from_currency", fromCurrency);
  url.searchParams.set("to_currency", toCurrency);
  url.searchParams.set("apikey", ALPHA_VANTAGE_KEY);

  const response = await fetch(url.toString());
  if (!response.ok)
    throw new Error(`Alpha Vantage API error: ${response.status}`);
  return response.json();
}

// Finnhub
async function fetchFinnhubQuote(symbol: string) {
  const url = new URL("https://finnhub.io/api/v1/quote");
  url.searchParams.set("symbol", symbol);
  url.searchParams.set("token", FINNHUB_KEY);

  const response = await fetch(url.toString());
  if (!response.ok) throw new Error(`Finnhub API error: ${response.status}`);
  return response.json();
}

async function fetchMarketNews() {
  const url = new URL("https://finnhub.io/api/v1/news");
  url.searchParams.set("category", "general");
  url.searchParams.set("token", FINNHUB_KEY);

  const response = await fetch(url.toString());
  if (!response.ok) throw new Error(`Finnhub API error: ${response.status}`);
  return response.json();
}
