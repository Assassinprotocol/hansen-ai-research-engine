import os

# =============================
# SYSTEM INFO
# =============================

SYSTEM_NAME = "Hansen AI"
SYSTEM_VERSION = "1.0"
SYSTEM_STAGE = "Core Engine Prototype"

# =============================
# LLM PROVIDER
# =============================

LLM_PROVIDER = "local_llama"

# =============================
# PATHS
# =============================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data")

METRICS_FILE_PATH = os.path.join(DATA_DIR, "metrics.json")

# =============================
# AUTO CREATE DATA DIR
# =============================

os.makedirs(DATA_DIR, exist_ok=True)