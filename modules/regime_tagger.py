import time
from modules.market_regime import MarketRegimeDetector


# ================================
# REGIME TAGGER
# ================================

class RegimeTagger:

    def __init__(self):

        self.detector = MarketRegimeDetector()

    # ================================
    # TAG SNAPSHOT DATA
    # ================================
    def tag_snapshot(self, snapshot_data):

        if not snapshot_data:
            return snapshot_data

        regime_info = self.detector.market_regime()

        regime = regime_info.get("regime", "unknown")
        breakdown = regime_info.get("breakdown", {})

        for item in snapshot_data:

            try:

                symbol = item.get("symbol", "")

                symbol_regime = breakdown.get(symbol, regime)

                item["regime"] = symbol_regime
                item["market_regime"] = regime

            except:
                continue

        return snapshot_data

    # ================================
    # TAG SINGLE RECORD
    # ================================
    def tag_record(self, record):

        try:

            regime_info = self.detector.market_regime()

            record["market_regime"] = regime_info.get("regime", "unknown")

        except:

            record["market_regime"] = "unknown"

        return record

    # ================================
    # GET CURRENT TAG
    # ================================
    def current_tag(self):

        regime_info = self.detector.market_regime()

        return regime_info.get("regime", "unknown")