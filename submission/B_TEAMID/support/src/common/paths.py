from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "raw" / "problem-B"
OUT_DIR = PROJECT_ROOT / "src" / "outputs"

REGIONS = [f"A{i}" for i in range(1, 9)]
MONTHS = [f"2025-{m:02d}" for m in range(1, 13)]
SOURCES = ["火电", "水电", "风电", "光伏"]
SECTORS = ["工业用电", "建筑服务用电", "交通用电", "居民用电"]
CHANNELS = [f"E{i:02d}" for i in range(1, 12)]
PLAN_YEARS = [2026, 2027, 2028, 2029, 2030]


def out_dir(sub: str) -> Path:
    d = OUT_DIR / sub
    d.mkdir(parents=True, exist_ok=True)
    return d
