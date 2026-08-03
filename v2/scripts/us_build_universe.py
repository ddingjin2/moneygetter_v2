from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from v2.data.us_market_dataset import save_us_universe  # noqa: E402
from v2.data.us_providers import provider_from_config  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Build US universe cache.")
    parser.add_argument("--config", default="config/us_market_data.example.json")
    parser.add_argument("--universe-key", default=None)
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    universe_key = args.universe_key or config.get("universe_key", "sp500")
    provider = provider_from_config(config)
    universe = provider.fetch_universe()
    path = save_us_universe(universe, universe_key=universe_key)
    print(json.dumps({"path": str(path), "universe_key": universe_key, "symbols": int(len(universe)), "source": str(universe["source"].iloc[0])}, indent=2))


if __name__ == "__main__":
    main()
