from __future__ import annotations

import pandas as pd


def make_frame(rows: int, start: int = 0) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": list(range(start, start + rows)),
            "value": [f"v-{i}" for i in range(start, start + rows)],
        }
    )
