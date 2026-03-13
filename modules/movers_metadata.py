import time
from modules.top_movers import TopMoversDetector


# ================================
# TOP MOVERS METADATA
# ================================

class MoversMetadata:

    def __init__(self):

        self.detector = TopMoversDetector()

    # ================================
    # GENERATE MOVERS SNAPSHOT
    # ================================
    def generate(self, minutes=60):

        gainers = self.detector.gainers(10, minutes)
        losers = self.detector.losers(10, minutes)

        return {
            "timestamp": time.time(),
            "minutes": minutes,
            "top_gainers": gainers,
            "top_losers": losers
        }

    # ================================
    # ATTACH TO SNAPSHOT METADATA
    # ================================
    def attach(self, metadata, minutes=60):

        movers = self.generate(minutes)

        metadata["top_movers"] = movers

        return metadata