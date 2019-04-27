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

    assert map.tile_sets[1].name == "tile_set_image"
    assert map.tile_sets[1].tilewidth == 32
    assert map.tile_sets[1].tileheight == 32
    assert map.tile_sets[1].spacing == 1
    assert map.tile_sets[1].margin == 1
    assert map.tile_sets[1].tilecount == 48
    assert map.tile_sets[1].columns == 8
    assert map.tile_sets[1].tileoffset == None
    assert map.tile_sets[1].grid == None
    assert map.tile_sets[1].properties == None
    assert map.tile_sets[1].terraintypes == None
    assert map.tile_sets[1].tiles == {}

    # unsure how to get paths to compare propperly
    assert str(map.tile_sets[1].image.source) == "images/tmw_desert_spacing.png"
    assert map.tile_sets[1].image.trans == None
    assert map.tile_sets[1].image.width == 265
    assert map.tile_sets[1].image.height == 199

    # assert map.layers ==


@pytest.mark.parametrize(
    "test_input,expected", [
        ("#001122", (0x00, 0x11, 0x22, 0xff)),
        ("001122", (0x00, 0x11, 0x22, 0xff)),
        ("#FF001122", (0x00, 0x11, 0x22, 0xff)),
        ("FF001122", (0x00, 0x11, 0x22, 0xff)),
        ("FF001122", (0x00, 0x11, 0x22, 0xff)),
    ]
)
def test_color_parsing(test_input, expected):
    """
    Tiled has a few different types of color representations.
    """
    assert arcade.tiled._parse_color(test_input) == expected
