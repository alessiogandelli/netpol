"""Topic-label helper for the COP examples.

Network loading lives in netpol itself (``netpol.load_layers`` /
``netpol.read_multilayer_gml``); this module only maps topic ids to human
labels from the topiclayers topic CSV / legacy json.
"""

from __future__ import annotations

import glob
from pathlib import Path


def load_topic_labels(folder: Path, n_cop: int) -> dict[int, str]:
    """Topic id -> human label, from the legacy json or the topics CSV."""
    labels_path = folder / f"cache/labels_cop{n_cop}.json"
    if labels_path.exists():
        import json

        raw = json.loads(labels_path.read_text())
        return {int(k): v for k, v in raw.items()}

    for csv_path in glob.glob(
        str(folder / "cache" / "tm" / "*" / f"topics_cop{n_cop}.csv")
    ):
        import pandas as pd

        df = pd.read_csv(csv_path)
        return {
            int(row["Topic"]): str(row["Name"])
            for _, row in df.iterrows()
            if pd.notna(row["Topic"])
        }

    return {}
