from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_DIR = Path(__file__).resolve().parent
DATA_DIR = MODULE_DIR / 'data'
MOCK_DIR = MODULE_DIR / 'mock'
COMPANY_INFO_DIR = ROOT / 'company-info'
COMPANY_SUMMARY_DIR = Path('/data/company-summary')
