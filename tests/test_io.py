"""Tests for netpol.io: topiclayers output -> dict[layer_id, DiGraph]."""

import networkx as nx
import pytest

from netpol.io import load_layers, read_multilayer_gml


MULTILAYER_GML = """#TYPE
multiplex

#VERSION
3.0

#LAYERS
1.0,DIRECTED,LOOPS
2.0,DIRECTED,LOOPS

#ACTORS
a
b
c

#EDGES
a,b,1.0
a,c,2.0
"""


@pytest.fixture
def multilayer_gml(tmp_path):
    p = tmp_path / "cop22_retweet_network_ml.gml"
    p.write_text(MULTILAYER_GML)
    return p


@pytest.fixture
def projected_folder(tmp_path):
    prj = tmp_path / "networks" / "projected"
    prj.mkdir(parents=True)

    g1 = nx.DiGraph()
    g1.add_edge("a", "b")
    nx.write_gml(g1, prj / "cop22__prj_1.gml")

    g2 = nx.DiGraph()
    g2.add_edge("a", "c")
    nx.write_gml(g2, prj / "cop22__prj_2.gml")

    return tmp_path


def test_parses_layers_and_edges(multilayer_gml):
    layers = read_multilayer_gml(multilayer_gml)
    assert set(layers) == {1, 2}
    assert layers[1].number_of_edges() == 1
    assert layers[2].number_of_edges() == 1


def test_edge_direction_preserved(multilayer_gml):
    layers = read_multilayer_gml(multilayer_gml)
    assert layers[1].has_edge("a", "b")
    assert not layers[1].has_edge("b", "a")
    assert all(isinstance(g, nx.DiGraph) for g in layers.values())


def test_load_layers_from_gml_file(multilayer_gml):
    layers = load_layers(multilayer_gml)
    assert set(layers) == {1, 2}
    assert layers[1].has_edge("a", "b")


def test_load_layers_from_output_folder(projected_folder):
    layers = load_layers(projected_folder)
    assert set(layers) == {1, 2}
    assert layers[1].has_edge("a", "b")
    assert layers[2].has_edge("a", "c")


def test_load_layers_missing_projected_dir(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_layers(tmp_path)


def test_load_layers_empty_projected_dir(tmp_path):
    (tmp_path / "networks" / "projected").mkdir(parents=True)
    with pytest.raises(FileNotFoundError):
        load_layers(tmp_path)
