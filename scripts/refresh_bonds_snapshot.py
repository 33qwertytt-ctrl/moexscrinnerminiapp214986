"""Manual refresh entrypoint for the local MOEX bond snapshot."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from application.services.bond_snapshot_service import BondSnapshotService
from config.settings import settings


async def _main() -> None:
    service = BondSnapshotService(settings)
    meta = await service.refresh(reason="manual_script")
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(_main())
