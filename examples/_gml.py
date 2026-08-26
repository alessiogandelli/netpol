"""Shared data-prep helpers for the COP examples.

Kept out of ``netpol/`` because these read the raw multiplex GML and topic
CSV produced by the ``topiclayers`` pipeline -- netpol itself only ever sees
plain networkx graphs.
"""

from __future__ import annotations

import glob
from pathlib import Path

import networkx as nx


def read_multilayer_gml(path: str) -> dict[int, nx.DiGraph]:
    """Parse a multiplex GML into ``dict[layer_id, DiGraph]``.

    The format is a flat list of layers, actors and ``source,target,layer``
    edge triples (``source -> target`` = "source retweets target").
    """
    section = None
    layers: dict[int, nx.DiGraph] = {}

    with open(path) as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            if line.startswith("#"):
                section = line[1:].strip()
                continue

            if section == "LAYERS":
                lid = int(float(line.split(",")[0]))
                layers[lid] = nx.DiGraph()
            elif section == "EDGES":
                src, tgt, lid = line.split(",")
                layers[int(float(lid))].add_edge(src, tgt)

    return layers


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
