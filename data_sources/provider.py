import os
from abc import ABC, abstractmethod
from typing import Optional


class MarketDataProvider(ABC):
    """
    Abstract interface for market data ingestion (IHSG OHLC, FX, commodities, foreign flow).
    Enforces licensing boundaries between personal/research scrapers and licensed vendor feeds.
    """
    personal_use_only: bool = True
    provider_name: str = "BaseProvider"

    @abstractmethod
    def get_ihsg_ohlc(self, target_date: Optional[str] = None) -> dict:
        """Fetch IHSG OHLC snapshot. Returns structured dictionary with close, change_pct, etc."""
        pass

    @abstractmethod
    def get_usdidr_rate(self, target_date: Optional[str] = None) -> dict:
        """Fetch USD/IDR currency snapshot."""
        pass

    @abstractmethod
    def get_all_commodities(self) -> dict:
        """Fetch all tracked commodities snapshot."""
        pass

    @abstractmethod
    def get_foreign_flow(self, target_date: Optional[str] = None) -> dict:
        """Fetch IDX foreign flow snapshot."""
        pass


class YahooMarketDataProvider(MarketDataProvider):
    """
    Yahoo Finance & yfinance provider.
    Flagged as personal/research use only per Yahoo Finance terms of service.
    Refuses execution when NEXUS_PUBLIC_MODE is enabled.
    """
    personal_use_only = True
    provider_name = "YahooFinance"

    def _check_public_mode_guard(self):
        public_mode = os.getenv("NEXUS_PUBLIC_MODE", "false").lower() in ("true", "1", "yes")
        if public_mode:
            raise RuntimeError(
                "YahooMarketDataProvider is restricted to personal/research use only. "
                "NEXUS_PUBLIC_MODE is active, which requires a licensed market data provider. "
                "Configure a licensed data provider via NEXUS_MARKET_DATA_PROVIDER or set NEXUS_PUBLIC_MODE=false."
            )

    def get_ihsg_ohlc(self, target_date: Optional[str] = None) -> dict:
        self._check_public_mode_guard()
        from data_sources.market_data import fetch_ihsg_snapshot
        return fetch_ihsg_snapshot(target_date=target_date)

    def get_usdidr_rate(self, target_date: Optional[str] = None) -> dict:
        self._check_public_mode_guard()
        from data_sources.market_data import fetch_usdidr_snapshot
        return fetch_usdidr_snapshot(target_date=target_date)

    def get_all_commodities(self) -> dict:
        self._check_public_mode_guard()
        from data_sources.market_data import fetch_all_commodities
        return fetch_all_commodities()

    def get_foreign_flow(self, target_date: Optional[str] = None) -> dict:
        self._check_public_mode_guard()
        from data_sources.market_data import fetch_foreign_flow_snapshot
        return fetch_foreign_flow_snapshot(target_date=target_date)


class LicensedMarketDataProvider(MarketDataProvider):
    """
    Placeholder adapter for enterprise / licensed exchange feeds
    (e.g., IDX direct data feed, Refinitiv/LSEG, Bloomberg, Twelve Data).
    """
    personal_use_only = False
    provider_name = "LicensedEnterpriseFeed"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("LICENSED_DATA_API_KEY")

    def get_ihsg_ohlc(self, target_date: Optional[str] = None) -> dict:
        if not self.api_key:
            return {
                "close": None,
                "change_pct": None,
                "source": "licensed_feed_unconfigured",
                "error": "Licensed data provider API key not configured"
            }
        # In a fully configured environment, dispatch to licensed REST API
        raise NotImplementedError("Licensed feed integration endpoint to be specified with vendor credentials.")

    def get_usdidr_rate(self, target_date: Optional[str] = None) -> dict:
        if not self.api_key:
            return {"usdidr": None, "source": "licensed_feed_unconfigured", "error": "API key missing"}
        raise NotImplementedError("Licensed FX feed not yet configured.")

    def get_all_commodities(self) -> dict:
        return {}

    def get_foreign_flow(self, target_date: Optional[str] = None) -> dict:
        return {"foreign_net_val": None, "source": "licensed_feed_unconfigured"}


def get_market_data_provider() -> MarketDataProvider:
    """
    Factory function returning the active market data provider based on environment settings.
    """
    provider_type = os.getenv("NEXUS_MARKET_DATA_PROVIDER", "yahoo").strip().lower()
    if provider_type == "licensed":
        return LicensedMarketDataProvider()
    return YahooMarketDataProvider()
