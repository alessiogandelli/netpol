"""I/O helpers: load topiclayers output into netpol's graph format.

topiclayers writes networks in two shapes:

* a single multilayer GML (``*_retweet_network_ml.gml``), produced by
  ``uunet.multinet`` -- a flat list of ``LAYERS``, ``ACTORS`` and
  ``EDGES`` sections with ``source,target,layer`` edge triples;
* one plain networkx GML per topic under ``networks/projected/``.

``load_layers`` accepts either and returns the ``dict[layer_id, DiGraph]``
that ``netpol.pipeline.analyze_layers`` consumes; ``load_network`` loads a
single plain GML into the ``DiGraph`` that ``analyze_network`` consumes.
"""

from __future__ import annotations

from pathlib import Path

import networkx as nx

from netpol.types import Layers


def _read_projected_gml(path: str | Path) -> nx.DiGraph:
    """Read a plain networkx GML and guarantee a directed simple graph."""
    graph = nx.read_gml(path)
    if isinstance(graph, nx.MultiDiGraph):
        raise TypeError("MultiDiGraph is not supported")
    if not isinstance(graph, nx.DiGraph):
        graph = graph.to_directed()
    return nx.DiGraph(graph)


def load_network(path: str | Path) -> nx.DiGraph:
    """Load a single plain (projected) networkx GML as a directed graph.

    Args:
        path: Path to a GML file written by ``nx.write_gml`` (e.g. a
            topiclayers ``networks/projected/*__prj_*.gml``).

    Returns:
        A ``DiGraph`` suitable for :func:`netpol.analyze_network`.
    """
    return _read_projected_gml(path)


def read_multilayer_gml(path: str | Path) -> dict[int, nx.DiGraph]:
    """Parse a topiclayers multilayer GML into ``dict[layer_id, DiGraph]``.

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


def load_layers(path: str | Path) -> Layers:
    """Load layers from a topiclayers output path.

    Args:
        path: Either a multilayer ``.gml`` file, or a topiclayers output
            folder (in which case ``networks/projected/*__prj_*.gml`` is
            loaded via ``nx.read_gml``).

    Returns:
        Mapping ``layer_id -> DiGraph``.
    """
    p = Path(path)

    if p.is_file():
        return read_multilayer_gml(p)

    projected = p / "networks" / "projected" if p.is_dir() else p / "projected"
    if not projected.is_dir():
        raise FileNotFoundError(
            f"expected a multilayer .gml file or a folder containing "
            f"'networks/projected/', got: {p}"
        )

    layers: dict[int, nx.DiGraph] = {}
    for gml_path in sorted(projected.glob("*__prj_*.gml")):
        topic = gml_path.stem.split("__prj_")[1]
        lid = int(float(topic))
        graph = _read_projected_gml(gml_path)
        layers[lid] = graph

    if not layers:
        raise FileNotFoundError(f"no projected topic GMLs found in: {projected}")

    return layers
