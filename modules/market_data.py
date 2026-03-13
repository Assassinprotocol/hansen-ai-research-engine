import requests


class MarketData:

    def __init__(self):

        self.session = requests.Session()


    def get_all_prices(self):

        url = "https://fapi.binance.com/fapi/v1/ticker/price"

        try:

            response = self.session.get(url, timeout=10)

            if response.status_code != 200:
                return []

            data = response.json()

            if not isinstance(data, list):
                return []

            clean_data = []

            for item in data:

                symbol = item.get("symbol")
                price = item.get("price")

                if symbol and price:

                    try:

                        clean_data.append({
                            "symbol": symbol,
                            "price": float(price)
                        })

                    except:
                        continue

            return clean_data

        except Exception as e:

            print("Market API error:", e)

            return []

    def get_ticker_24h(self, symbol=None):
        """Get 24h ticker with price change percent. If symbol=None, return all."""
        try:
            if symbol:
                url = f"https://fapi.binance.com/fapi/v1/ticker/24hr?symbol={symbol}"
            else:
                url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                return [] if not symbol else None
            data = response.json()
            if symbol:
                return data if isinstance(data, dict) else None
            return data if isinstance(data, list) else []
        except Exception as e:
            print("Ticker 24h error:", e)
            return [] if not symbol else None

    def get_klines(self, symbol, interval="1h", limit=168):
        """Get kline/candlestick data for correlation calculation."""
        try:
            url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                return []
            data = response.json()
            return data if isinstance(data, list) else []
        except Exception as e:
            print("Klines error:", e)
            return []