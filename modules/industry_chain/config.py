from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
MODULE_DIR = Path(__file__).resolve().parent

load_dotenv(ROOT / '.env')

NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687').strip()
NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j').strip()
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'neo4j2026').strip()
NEO4J_DATABASE = os.getenv('NEO4J_DATABASE', 'neo4j').strip()
INDUSTRY_CHAIN_DEFAULT_LIMIT = int(os.getenv('INDUSTRY_CHAIN_DEFAULT_LIMIT', '30'))
INDUSTRY_CHAIN_MAX_LIMIT = int(os.getenv('INDUSTRY_CHAIN_MAX_LIMIT', '100'))
