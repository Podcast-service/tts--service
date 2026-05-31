import logging
import os

logging.getLogger().setLevel(os.getenv("LOG_LEVEL", "INFO"))
