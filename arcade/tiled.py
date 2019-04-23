"""
Functions and classes for managing a map created in the "Tiled Map Editor"
"""

import xml.etree.ElementTree as etree
import base64
import gzip
import zlib

from typing import NamedTuple
from pathlib import Path

from arcade.isometric import isometric_grid_to_screen
from arcade import Sprite
from arcade import SpriteList


class EncodingError(Exception):
    """
    Tmx layer encoding is of an unknown type.
    """
    pass


class TileNotFoundError(Exception):
    """
    Tile not found in tileset.
    """
    pass


class ImageNotFoundError(Exception):
    """
    Image not found.
    """
    pass


# wrap the namedtuple in a class so that sphinx generates docs for it
class TiledMap(NamedTuple):
    """
    Namedtuple for a tiled mape, and tileset from the map
    Attributes:
        :parent_dir: The logical parent of the tmx_file.
        :global_tileset: Dict of tilesets used by tmx.
        :layers: Dict containing each layer.
        :version: The TMX format version.
        :orientation: Map orientation. Tiled supports “orthogonal”, \
        “isometric”, “staggered” and “hexagonal”.
        :renderorder: The order in which tiles on tile layers are \
        rendered.
        "width: The map width in tiles.
        "height: The map height in tiles.
        :tilewidth: The width of a tile.
        :tileheight: The height of a tile.
        :backgroundcolor: The background color of the map.
        :nextobjectid: Stores the next available ID for new objects.
    """
    parent_dir: str
    global_tileset: dict
    layers_int_data: dict
    version: str
    orientation: str
    renderorder: str
    width: int
    height: int
    tilewidth: int
    tileheight: int
    backgroundcolor: tuple
    nextobjectid: int


tile_fields = ("gid", "tilewidth", "tileheight", "source", "points")
# wrap the namedtuple in a class so that sphinx generates docs for it
class Tile(NamedTuple):
    """
    Namedtuple for an individual tile from a tilesetself.
    Attributes:
        :gid: Global ID number of tile. Garunteed to be unique within \
        a tmx file. More info: \
        https://doc.mapeditor.org/en/stable/reference/tmx-map-format/#data
        :tilewidth: Width of tile in pixels.
        :tileheight: Height of the tile in pixels.
        :source: Image source location of tile.
        :points: List of points to use for collision.
    """
    gid: int
    tilewidth: int
    tileheight: int
    source: str
    points: str


# namedtuple represents a location on the grid
grid_location_fields = ("tile", "center_x", "center_y")
# wrap the namedtuple in a class so that sphinx generates docs for it
class GridLocation(NamedTuple):
    """
    Namedtuple for an x/y location and the tile ID that is in it.
    Attributes:
        :tile: ID of the tile that occupies this GridLocation.
        :center_x: X coordinate of the center of this tile.
        :center_y: Y coordinate of the center of this tile.
    """
    tile: int = None
    center_x: int = None
    center_y: int = None


def _process_csv_encoding(data_text):
    layer_grid_ints = []
    lines = data_text.split("\n")
    for line in lines:
        line_list = line.split(",")
        while "" in line_list:
            line_list.remove("")
        line_list_int = [int(item) for item in line_list]
        layer_grid_ints.append(line_list_int)
    return layer_grid_ints


def _process_base64_encoding(data_text, compression, layer_width):
    layer_grid_ints = [[]]

    unencoded_data = base64.b64decode(data_text)
    if compression == "zlib":
        unzipped_data = zlib.decompress(unencoded_data)
    elif compression == "gzip":
        unzipped_data = gzip.decompress(unencoded_data)
    elif compression is None:
        unzipped_data = unencoded_data
    else:
        raise ValueError(f"Unsupported compression type '{compression}'.")

    # Turn bytes into 4-byte integers
    byte_count = 0
    int_count = 0
    int_value = 0
    row_count = 0
    for byte in unzipped_data:
        int_value += byte << (byte_count * 8)
        byte_count += 1
        if byte_count % 4 == 0:
            byte_count = 0
            int_count += 1
            layer_grid_ints[row_count].append(int_value)
            int_value = 0
            if int_count % layer_width == 0:
                row_count += 1
                layer_grid_ints.append([])
    layer_grid_ints.pop()
    return layer_grid_ints

def _decode_layer(data_tag, layer_width):
    # Unzip and unencode each layer
    data_text = data_tag.text.strip()
    encoding = data_tag.attrib['encoding']
    if 'compression' in data_tag.attrib:
        compression = data_tag.attrib['compression']
    else:
        compression = None

    if encoding == "csv":
        layer_grid_ints = _process_csv_encoding(data_text)
    elif encoding == "base64":
        layer_grid_ints = _process_base64_encoding(
            data_text, compression, layer_width)
    else:
        raise EncodingError(f"Error, unexpected encoding: {encoding}.")

    return layer_grid_ints


def _parse_points(point_text: str):
    result = []
    point_list = point_text.split(" ")
    for point in point_list:
        z = point.split(",")
        result.append([round(float(z[0])), round(float(z[1]))])
    return result


def _parse_tsx(parent_dir, tileset_tag_list, scaling=1):
    """
    Parse the tilesets and return a dict containing each one
    Args:
        parent_dir: path of parent directory of tmx file
    """
    global_tileset = {}
    # Loop through each tileset
    for tileset_tag in tileset_tag_list:
        firstgid = int(tileset_tag.attrib["firstgid"])
        if "source" in tileset_tag.attrib:
            source = tileset_tag.attrib["source"]
            try:
                tileset_tree = etree.parse(source)
            except FileNotFoundError:
                source = parent_dir / Path(source)
                tileset_tree = etree.parse(source)
            # Root node should be 'map'
            tileset_root = tileset_tree.getroot()
            tile_tag_list = tileset_root.findall("tile")
        else:
            # Grab each tile
            tile_tag_list = tileset_tag.findall("tile")

        # Loop through each tile
        for tile_tag in tile_tag_list:
            # Make a tile object
            image = tile_tag.find("image")
            id = tile_tag.attrib["id"]
            image_width = int(image.attrib["width"])
            image_height = int(image.attrib["height"])
            source = image.attrib["source"]
            key = str(int(id) + 1)
            firstgid += 1

            objectgroup = tile_tag.find("objectgroup")
            if objectgroup:
                my_object = objectgroup.find("object")
                if my_object:
                    offset_x = round(float(my_object.attrib['x']))
                    offset_y = round(float(my_object.attrib['y']))
                    polygon = my_object.find("polygon")
                    if polygon is not None:
                        point_list = _parse_points(polygon.attrib['points'])
                        for point in point_list:
                            point[0] += offset_x
                            point[1] += offset_y
                            point[1] = image_height - point[1]
                            point[0] -= image_width // 2
                            point[1] -= image_height // 2
                            point[0] *= scaling
                            point[1] *= scaling
                            point[0] = int(point[0])
                            point[1] = int(point[1])
                        points = point_list
                    else:
                        points = None
                else:
                    points = None
            else:
                points = None

            my_tile = Tile(id, image_width, image_height, source, points)
            global_tileset[key] = my_tile
    return global_tileset


def _get_background_color(map_tag):
    if "backgroundcolor" in map_tag.attrib:
        # Decode the background color string
        backgroundcolor_string = map_tag.attrib["backgroundcolor"]
        red_hex = "0x" + backgroundcolor_string[1:3]
        green_hex = "0x" + backgroundcolor_string[3:5]
        blue_hex = "0x" + backgroundcolor_string[5:7]
        red = int(red_hex, 16)
        green = int(green_hex, 16)
        blue = int(blue_hex, 16)
        return (red, green, blue)
    else:
        return None


def read_tiled_map(tmx_file: str, scaling) -> TiledMap:
    """
    Given a tmx_file, this will read in a tiled map, and return
    a TiledMap namedtuple.

    Important: Tiles must be a "collection" of images.

    Hitboxes can be drawn around tiles in the tileset editor,
    but only polygons are supported.
    (This is a great area for PR's to improve things.)

    Args:
        tmx_file (str): Location of tmx_file to be read
        scaling: factor by which to scale the hitbox for each tile \
        FIXME: that doesn't make any sense
    """
    parent_dir = Path(tmx_file).parent

    # Read in and parse the file
    tree = etree.parse(tmx_file)

    # Root node should be 'map'
    map_tag = tree.getroot()

    #FIXME: this does not work for multiple tilesets
    #FIXME: for loop should be outside of _parse_tsx
    #FIXME: xml support
    tileset_tag_list = map_tag.findall('./tileset')
    global_tileset = _parse_tsx(parent_dir, tileset_tag_list)

    layer_tag_list = map_tag.findall('./layer')
    layers_int_data = {}
    for layer_tag in layer_tag_list:
        layer_width = int(layer_tag.attrib['width'])
        data_tag = layer_tag.find("data")
        layer_grid_ints = _decode_layer(data_tag, layer_width)
        layers_int_data[layer_tag.attrib["name"]] = layer_grid_ints

        layer_grid_objs = []
        for row_index, row in enumerate(layer_grid_ints):
            layer_grid_objs.append([])

    return TiledMap(
        parent_dir=parent_dir,
        global_tileset=global_tileset,
        layers_int_data=layers_int_data,
        version=map_tag.attrib["version"],
        orientation=map_tag.attrib["orientation"],
        renderorder=map_tag.attrib["renderorder"],
        width=int(map_tag.attrib["width"]),
        height=int(map_tag.attrib["height"]),
        tilewidth=int(map_tag.attrib["tilewidth"]),
        tileheight=int(map_tag.attrib["tileheight"]),
        backgroundcolor=_get_background_color(map_tag),
        nextobjectid=map_tag.attrib["nextobjectid"],
    )

def generate_sprites(map_object, layer_name, scaling, base_directory=""):
    sprite_list = SpriteList()

    # it is an error to not be given a valid layer_name
    if layer_name not in map_object.layers_int_data:
        raise ValueError(f"Error, no layer named '{layer_name}'.")

    map_array = map_object.layers_int_data[layer_name]

    # Loop through the layer and add in the wall list
    for row_index, row in enumerate(map_array):
        for column_index, item in enumerate(row):
            if str(item) in map_object.global_tileset:
                tile_info = map_object.global_tileset[str(item)]
                image_file = base_directory + tile_info.source

                my_sprite = Sprite(image_file, scaling)
                my_sprite.right = column_index * (map_object.tilewidth * scaling)
                my_sprite.top = (map_object.height - row_index) * (map_object.tileheight * scaling)

                if tile_info.points is not None:
                    my_sprite.set_points(tile_info.points)
                sprite_list.append(my_sprite)
            elif item != 0:
                raise ImageNotFoundError(
                    f"Error, could not find {item} image to load.")

    return sprite_list
