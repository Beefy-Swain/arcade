import os

from pathlib import Path

import pytest

import arcade.tiled

print(os.path.dirname(os.path.abspath(__file__)))

os.chdir(os.path.dirname(os.path.abspath(__file__)))



def test_map_simple():
    """
    TMX with a very simple tileset and some properties.
    """
    map = arcade.tiled.TileMap(Path("../test_data/test_map_simple.tmx"))

    properties = {
        "bool property - false": False,
        "bool property - true": True,
        "color property": (0x49, 0xfc, 0xff, 0xff),
        "file property": Path("/var/log/syslog"),
        "float property": 1.23456789,
        "int property": 13,
        "string property": "Hello, World!!"
    }

    assert map.version == "1.2"
    assert map.tiledversion == "1.2.3"
    assert map.orientation == "orthogonal"
    assert map.renderorder == "right-down"
    assert map.width == 8
    assert map.height == 6
    assert map.tilewidth == 32
    assert map.tileheight == 32
    assert map.infinite == False
    assert map.hexsidelength == None
    assert map.staggeraxis == None
    assert map.staggerindex == None
    assert map.backgroundcolor == None
    assert map.nextlayerid == 2
    assert map.nextobjectid == 1
    assert map.properties == properties
    # assert map.tile_sets ==
    # assert map.layers ==
