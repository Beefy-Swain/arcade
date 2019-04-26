"""
Functions and classes for managing a map created in the "Tiled Map Editor"
"""

import functools
import re

from pathlib import Path
from collections import OrderedDict

import xml.etree.ElementTree as etree

from typing import *


class EncodingError(Exception):
    """
    Tmx layer encoding is of an unknown type.
    """


class TileNotFoundError(Exception):
    """
    Tile not found in tileset.
    """


class ImageNotFoundError(Exception):
    """
    Image not found.
    """


class Color:
    """
    NamedTuple representing a color with alpha.

    FIXME: idk wtf I'm doing here
    """
    def __init__(self, value: str):
        pass


class Image:
    """
    Image object.

    This module does not support embedded data in image elements.

    Attributes:
        :source (Union[None, str]): The reference to the tileset image file. \
        Not that this is a relative path compared to FIXME
        :trans (Union[None, str]): Defines a specific color that is treated \
        as transparent.
        :width (Union[None, str]): The image width in pixels \
        (optional, used for tile index correction when the image changes).
        :height (Union[None, str]): The image height in pixels (optional).
    """
    def __init__(self, image_element: Union[None, etree.Element] = None):
        """
        Initializes Image object and parses image element if given.

        Args:
            :image_element (etree.Element): Image element to be parsed.
        """
        self.source: Union[None, str]
        self.trans: Union[None, Color]
        self.width: Union[None, int]
        self.height: Union[None, int]

        if image_element:
            self.parse_image_element(image_element)


    def parse_image_element(self, image_element: etree.Element):
        """
        Parse image element given.
        """
        self.source = None
        try:
            self.image_source = image_element.attrib['source']
        except KeyError:
            pass

        self.trans = None
        try:
            self.trans = Color(image_element.attrib['trans'])
        except KeyError:
            pass

        self.width = None
        try:
            self.width = int(image_element.attrib['width'])
        except KeyError:
            pass

        self.height = None
        try:
            self.height = int(image_element.attrib['height'])
        except KeyError:
            pass


class Properties(Dict[str, Union[str, int, float, bool, Color, Path]]):
    """
    Dict for storing custom properties.

    Can be used as a child of the map, tileset, tile (when part of a \
    tileset), terrain, layer, objectgroup, object, imagelayer and group \
    elements.

    See \
    https://doc.mapeditor.org/en/stable/reference/tmx-map-format/#properties \
    for more info.
    """
    def __init__(self, properties_element: Union[None, etree.Element] = None):
        """
        Initializes Properties Object and parses proprties element if given.

        Args:
            :properties_element (etree.Element): Properties element to be \
            parsed.
        """

    def add(self, name: str, property_type: str, value: str):
        """
        Adds Tiled property to Properties dict.

        Args:
            :name (str): Name of property.
            :property_type (str): Type of property. Can be string, int, \
            float, bool, color or file. Defaults to string.
            :value (str): The value of the property.
        """
        types = ['string', 'float', 'bool', 'color', 'file']
        assert property_type in types, f"Invalid type for property {name}"

        if property_type == 'float':
            self[name] = float(value)
        elif property_type == 'color':
            self[name] = Color(value)
        elif property_type == 'file':
            self[name] = Path(value)
        elif property_type == 'bool':
            if value == 'true':
                self[name] = True
            else:
                self[name] = False
        else:
            self[name] = value


    def parse_properties(self, properties_element):
        for property in properties_element.findall('./property'):
            name = property.attrib['name']
            property_type = property.attrib['type']
            value = property.attrib['value']
            properties.add(name, property_type, value)


class Grid(NamedTuple):
    """
    Contains info for isometric maps.

    This element is only used in case of isometric orientation, \
    and determines how tile overlays for terrain and collision \
    information are rendered.
    """
    orientation: str
    width: int
    height: int


class Terrain(NamedTuple):
    """
    Terrain object.

    Args:
        :name (str): The name of the terrain type.
        :tile (int): The local tile-id of the tile that represents the \
        terrain visually.
    """
    name: str
    tile: int


class Frame(NamedTuple):
    """
    Animation Frame object.

    This is only used as a part of an animation for Tile objects.

    Args:
        :tileid (int): The local ID of a tile within the parent tile set \
        object.
        :duration (int): How long in milliseconds this frame should be \
        displayed before advancing to the next frame.
    """
    tileid: int
    duration: int


class Object(NamedTuple):
    """
    ObjectGroup Object.

    See: \
    https://doc.mapeditor.org/en/stable/reference/tmx-map-format/#object

    Args:
        :id (int): Unique ID of the object. Each object that is placed on a \
        map gets a unique id. Even if an object was deleted, no object gets \
        the same ID.
        :name (Union[None, str]): The name of the object.
        :type (Union[None, str]): The type of the object.
        :x (int): The x coordinate of the object in pixels.
        :y (int): The y coordinate of the object in pixels.
        :width (int): The width of the object in pixels (defaults to 0).
        :height (int): The height of the object in pixels (defaults to 0).
        :rotation (int): The rotation of the object in degrees clockwise \
        (defaults to 0).
        :gid (Union[None, int]): A reference to a tile.
        :visible (bool): Whether the object is shown (True) or hidden \
        (False). Defaults to True.
        :template Union[None, Template]: A reference to a Template \
        object FIXME
    """
    id: int
    name: Union[None, str]
    type: Union[None, str]
    x: int
    y: int
    width: int
    height: int
    gid: Union[None, int]
    visible: bool
    template: Union[None, Template]


class ObjectGroup:
    """
    Object Group Object.

    The object group is in fact a map layer, and is hence called \
    “object layer” in Tiled.

    See: \
    https://doc.mapeditor.org/en/stable/reference/tmx-map-format/#objectgroup

    Args:
        :id (Union[None, int):] Unique ID of the layer. Each layer that \
        added to a map gets a unique id. Even if a layer is deleted, no \
        layer ever gets the same ID.
        :name (Union[None, str):] The name of the object group.
        :color (Union[None, Color]): The color used to display the objects \
        in this group.
        :opacity (int): The opacity of the layer as a percentage.
        :visible (bool): Whether the layer is shown (True) or hidden \
        (False). Defaults to True.
        :offsetx (int): Rendering offset for this object group in pixels. \
        Defaults to 0.
        :offsety (int): Rendering offset for this object group in pixels. \
        Defaults to 0.
        :draworder (str): Whether the objects are drawn according to the \
        order of appearance ('index') or sorted by their y-coordinate \
        ('topdown'). Defaults to 'topdown'.
        :properties (Union[None, Properties]): Properties object for \
        ObjectGroup.
        :objects (Dict[int, Object]): Dict Object objects by \
        Object.id.
    """
    def __init__(
            self, object_group_element: Union[None, etree.Element] = None):
        """
        Initializes image object and parses object group element if given.

        Args:
            :object_group_element (etree.Element): Object group element to \
            be parsed.
        """
        self.id: Union[None, int]
        self.name: Union[None, str]
        self.color: Union[None, Color]
        self.opacity: int
        self.visible: bool
        self.offsetx: int
        self.offsety: int
        self.draworder: str
        self.properties: Union[None, Properties]
        self.objects: Dict[int, Object]

        if object_group_element:
            self.parse_object_group_element(object_group_element)


    def parse_object_group_element(self, object_group_element: etree.Element):
        """
        Parse object group element given.
        """
        self.id = None
        try:
            self.id = int(object_group_element.attrib['id'])
        except KeyError:
            pass

        self.name = None
        try:
            self.name = object_group_element.attrib['name']
        except KeyError:
            pass

        self.color = None
        try:
            self.color = Color(object_group_element.attrib['color'])
        except KeyError:
            pass

        self.opacity = 100
        try:
            self.opacity = int(object_group_element.attrib['opacity'])
        except KeyError:
            pass

        self.visible = True
        try:
            self.visible = bool(int(object_group_element.attrib['visible']))
        except KeyError:
            pass

        self.offsetx = 0
        try:
            self.offsetx = int(object_group_element.attrib['offsetx'])
        except KeyError:
            pass

        self.offsety = 0
        try:
            self.offsety = int(object_group_element.attrib['offsety'])
        except KeyError:
            pass

        self.draworder = 'topdown'
        try:
            self.draworder = object_group_element.attrib['draworder']
        except KeyError:
            pass

        self.properties = None
        self.objects = {}


class TileTerrain(NamedTuple):
    """
    Defines each corner of a tile by Terrain index in \
    'TileSetXML.terraintypes'.

    Defaults to 'None'. 'None' means that corner has no terrain.

    Args:
        :top_left (Union[None, int]): Top left terrain type.
        :top_right (Union[None, int]): Top right terrain type.
        :bottom_left (Union[None, int]): Bottom left terrain type.
        :bottom_right (Union[None, int]): Bottom right terrain type.
    """
    top_left: Union[None, int] = None
    top_right: Union[None, int] = None
    bottom_left: Union[None, int] = None
    bottom_right: Union[None, int] = None


class Tile(NamedTuple):
    """
    Individual tile object.

    Args:
        :id (int): The local tile ID within its tileset.
        :type (str): The type of the tile. Refers to an object type and is \
        used by tile objects.
        :terrain (int): Defines the terrain type of each corner of the tile.
        :animation (List[Frame]): Each tile can have exactly one animation \
        associated with it.
    """
    id: int
    type: Union[None, str]
    terrain: Union[None, TileTerrain]
    animation: Union[None, List[Frame]]
    image: Union[Image, None]


class TileSet(NamedTuple):
    """
    Object for storing a TSX with all associated collision data.

    Args:
        :name (str): The name of this tileset.
        :tilewidth (int): The (maximum) width of the tiles in this \
        tileset.
        :tileheight (int): The (maximum) height of the tiles in this \
        tileset.
        :spacing (int): The spacing in pixels between the tiles in this \
        tileset (applies to the tileset image).
        :margin (int): The margin around the tiles in this tileset \
        (applies to the tileset image).
        :tilecount (int): The number of tiles in this tileset.
        :columns (int): The number of tile columns in the tileset. \
        For image collection tilesets it is editable and is used when \
        displaying the tileset.
        :grid (Grid): Only used in case of isometric orientation, \
        and determines how tile overlays for terrain and collision \
        information are rendered.
        :tileoffset (dict[str, int]): Used to specify an offset in \
        pixels when drawing a tile from the tileset. When not present, \
        no offset is applied.
        :image (Image): Used for spritesheet tile sets.
        :terraintypes (Dict[str, int]): List of of terrain types which \
        can be referenced from the terrain attribute of the tile object. \
        Ordered according to the terrain element's appearance in the \
        TSX file.
        :tiles (Union[None, Dict[int, Tile]]): Dict of Tile objects by \
        Tile.id.
    """
    name: str
    tilewidth: int
    tileheight: int
    spacing: Union[None, int]
    margin: Union[None, int]
    tilecount: Union[None, int]
    columns: Union[None, int]
    tileoffset: Union[None, Tuple[int, int]]
    grid: Union[None, Grid]
    properties: Union[None, Properties]
    image: Union[None, Image]
    terraintypes: Union[None, List[Terrain]]
    tiles: Union[None, Dict[int, Tile]]


class TileMap():
    """
    Object for storing a TMX with all associated layers and properties.

    The attributes below are nearly identical to the TMX spec as per\
    https://doc.mapeditor.org/en/stable/reference/tmx-map-format/#map
    Tiled Attributes:
        :version (str): The TMX format version.
        :tiledversion (str): The Tiled version used to save the file. May be \
        a date (for snapshot builds).
        :orientation (str): Map orientation. Tiled supports “orthogonal”, \
        “isometric”, “staggered” and “hexagonal”
        :renderorder (str): The order in which tiles on tile layers are \
        rendered. Valid values are right-down, right-up, left-down and \
        left-up. In all cases, the map is drawn row-by-row. (only supported \
        for orthogonal maps at the moment)
        :width (int): The map width in tiles.
        :height (int): The map height in tiles.
        :tilewidth (int): The width of a tile.
        :tileheight (int): The height of a tile.
        :hexsidelength (int): Only for hexagonal maps. Determines the width \
        or height (depending on the staggered axis) of the tile’s edge, in \
        pixels.
        :staggeraxis (str): For staggered and hexagonal maps, determines \
        which axis (“x” or “y”) is staggered.
        :staggerindex (str): For staggered and hexagonal maps, determines \
        whether the “even” or “odd” indexes along the staggered axis are \
        shifted.
        :backgroundcolor (##FIXME##): The background color of the map.
        :nextlayerid (int): Stores the next available ID for new layers.
        :nextobjectid (int): Stores the next available ID for new objects.

    These attributes are in addition to the TMX specified attributes.
    Attributes:
        :tile_sets (dict[str, TileSet]): Dict of tile sets used \
        in this map. Key is the source for external tile sets or the name \
        for embedded ones. The value is a TileSet object.
        :layers (dict[str, ##FIXME##]): Dict of layers.
    """
    def __init__(self):
        """
        Initialization for TileMapXML object.
        """
        # TMX spec attributes
        self.version: str
        self.tiledversion: str
        self.orientation: str
        self.renderorder: str
        self.width: int
        self.height: int
        self.tilewidth: int
        self.tileheight: int
        self.hexsidelength: int
        self.staggeraxis: int
        self.staggerindex: int
        self.backgroundcolor: str
        self.nextlayerid: int
        self.nextobjectid: int

        # tiled.py attributes
        self.tile_sets: OrderedDict[int, TileSet] = OrderedDict


def _parse_tiles(tile_element_list: List[etree.Element]) -> Dict[int, Tile]:
    tiles: Dict[int, Tile] = {}
    for tile_element in tile_element_list:
        # id is not optional
        id = int(tile_element.attrib['id'])

        # optional attributes
        type = None
        try:
            type = tile_element.attrib['type']
        except KeyError:
            pass

        tile_terrain = None
        try:
            tile_terrain_attrib = tile_element.attrib['terrain']
        except KeyError:
            pass
        else:
            # https://doc.mapeditor.org/en/stable/reference/tmx-map-format/#tile
            # an attempt to explain how terrains are handled is below.
            # 'terrain' attribute is a comma seperated list of 4 values,
            # each is either an integer or blank

            # convert to list of values
            terrain_list_attrib = re.split(',', tile_terrain_attrib)
            # terrain_list is list of indexes of Tileset.terraintypes
            terrain_list: List[Union[None, int]] = []
            # each index in terrain_list_attrib reffers to a corner
            for corner in terrain_list_attrib:
                if corner == '':
                    terrain_list.append(None)
                else:
                    terrain_list.append(int(corner))
            tile_terrain = TileTerrain(*terrain_list)

        # tile element optional sub-elements
        animation: Union[None, List[Frame]] = None
        try:
            tile_animation_element = tile_element.find('./animation')
            assert tile_animation_element is not None
        except AssertionError:
            pass
        else:
            animation = []
            frames = tile_animation_element.findall('./frame')
            for frame in frames:
                # tileid reffers to the Tile.id of the animation frame
                tileid = int(frame.attrib['tileid'])
                # duration is in MS. Should perhaps be converted to seconds.
                # FIXME: make decision
                duration = int(frame.attrib['duration'])
                animation.append(Frame(tileid, duration))

        # if this is None, then the Tile is part of a spritesheet
        tile_image = None
        try:
            tile_image_element = tile_element.find('./image')
            assert tile_image_element is not None
        except AssertionError:
            pass
        else:
            tile_image = Image(tile_image_element)

        tiles[id] = Tile(id, type, tile_terrain, animation, tile_image)

    return tiles


def _parse_tile_set(tile_set_element: etree.Element) -> TileSet:
    """
    Parses a tile set that is embedded into a TMX.
    """

    # get all basic attributes
    name = tile_set_element.attrib['name']
    tilewidth = int(tile_set_element.attrib['tilewidth'])
    tileheight = int(tile_set_element.attrib['tileheight'])

    spacing = None
    try:
        spacing = int(tile_set_element.attrib['spacing'])
    except KeyError:
        pass

    margin = None
    try:
        margin = int(tile_set_element.attrib['margin'])
    except KeyError:
        pass

    tilecount = None
    try:
        tilecount = int(tile_set_element.attrib['tilecount'])
    except KeyError:
        pass

    columns = None
    try:
        columns = int(tile_set_element.attrib['columns'])
    except KeyError:
        pass

    tileoffset: Union[None, Tuple[int, int]] = None
    try:
        tileoffset_element = tile_set_element.find('./tileoffset')
        assert tileoffset_element is not None
    except AssertionError:
        pass
    else:
        tile_offset_x = int(tileoffset_element.attrib['x'])
        tile_offset_y = int(tileoffset_element.attrib['y'])
        tile_offset = (tile_offset_x, tile_offset_y)

    grid = None
    try:
        grid_element = tile_set_element.find('./grid')
        assert grid_element is not None
    except AssertionError:
        pass
    else:
        grid_orientation = grid_element.attrib['orientation']
        grid_width = int(grid_element.attrib['width'])
        grid_height = int(grid_element.attrib['height'])
        grid = Grid(grid_orientation, grid_width, grid_height)

    properties = None
    try:
        properties_element = tile_set_element.find('./properties')
        assert properties_element is not None
    except AssertionError:
        pass
    else:
        properties = Properties()
        for property in properties_element.findall('./property'):
            name = property.attrib['name']
            property_type = property.attrib['type']
            value = property.attrib['value']
            properties.add(name, property_type, value)

    terraintypes: Union[None, List[Terrain]] = None
    try:
        terraintypes_element = tile_set_element.find('./terraintypes')
        assert terraintypes_element is not None
    except AssertionError:
        pass
    else:
        terraintypes = []
        for terrain in terraintypes_element.findall('./terrain'):
            name = terrain.attrib['name']
            terrain_tile = int(terrain.attrib['tile'])
            terraintypes.append(Terrain(name, terrain_tile))

    image = None
    try:
        image_element = tile_set_element.find('./image')
        assert image_element is not None
    except AssertionError:
        pass
    else:
        image = Image(image_element)

    tile_element_list = tile_set_element.findall('./tile')
    tiles = _parse_tiles(tile_element_list)

    return TileSet(
        name,
        tilewidth,
        tileheight,
        spacing,
        margin,
        tilecount,
        columns,
        tileoffset,
        grid,
        properties,
        image,
        terraintypes,
        tiles,
    )


@functools.lru_cache()
def _parse_external_tile_set(
        parent_dir: Path, tile_set_element: etree.Element) -> TileSet:
    source = Path(tile_set_element.attrib['source'])
    tile_set_tree = etree.parse(str(parent_dir / Path(source))).getroot()

    return _parse_tile_set(tile_set_tree)


class Tiled():
    """
    Controller object for importing TMX files.

    Handles importing TMX files and resolving TSX files.
    """
    def import_tmx(self, tmx_file: Union[str, Path]) -> TileMap:
        """
        Imports a TMX file and returns a TileMapXML object

        In addition to importing and returning a tile map, it also adds
        the map to the maps dict and any tile sets to the external_tile_sets dict
        to be re-used by any other maps that specify them.

        Args:
            :tmx_file (str, Path): Path of the TMX file to import.

        Returns:
            :TileMapXML: Returns TileMapXML object.
        """
        # for finding relative paths of TSX and image files
        parent_dir = Path(tmx_file).parent

        map_tree = etree.parse(str(tmx_file))
        map_element = map_tree.getroot()

        tile_set_element_list = map_element.findall('./tileset')

        tile_map = TileMap()
        tile_map.tile_sets = OrderedDict()

        for tile_set_element in tile_set_element_list:
            # tiled docs are ambiguous about the 'firstgid' attribute
            # current understanding is for the purposes of mapping the layer
            # data to the tile set data, add the 'firstgid' value to each
            # tile 'id'; this means that the 'firstgid' is specific to each,
            # tile set as they pertain to the map, not tile set specific as
            # the tiled docs can make it seem
            # 'firstgid' is saved beside each TileMapXML
            firstgid = int(tile_set_element.attrib['firstgid'])
            try:
                # check if is an external TSX
                source = tile_set_element.attrib['source']
            except KeyError:
                # the tile set in embedded
                name = tile_set_element.attrib['name']
                tile_map.tile_sets[firstgid] = _parse_tile_set(tile_set_element)
            else:
                # tile set is external
                tile_map.tile_sets[firstgid] = _parse_external_tile_set(
                    parent_dir, tile_set_element)

        return tile_map



'''
[22:16] <__m4ch1n3__> i would "[i for i in int_list if i < littler_then_value]"
[22:16] <__m4ch1n3__> it returns a list of integers below "littler_then_value"
[22:17] <__m4ch1n3__> !py3 [i for i in [1,2,3,4,1,2,3,4] if i < 3]
[22:17] <codebot> __m4ch1n3__: [1, 2, 1, 2]
[22:17] <__m4ch1n3__> !py3 [i for i in [1,2,3,4,1,2,3,4] if i < 4]
[22:17] <codebot> __m4ch1n3__: [1, 2, 3, 1, 2, 3]
[22:22] <__m4ch1n3__> !py3 max([i for i in [1,2,3,4,1,2,3,4] if i < 4])
[22:22] <codebot> __m4ch1n3__: 3
[22:22] <__m4ch1n3__> max(...) would return the maximum of resulting list
[22:23] <__m4ch1n3__> !py3 max([i for i in  [1, 10, 100] if i < 20])
[22:23] <codebot> __m4ch1n3__: 10
[22:23] <__m4ch1n3__> !py3 max([i for i in  [1, 10, 100] if i < 242])
[22:23] <codebot> __m4ch1n3__: 100
[22:23] == markb1 [~mbiggers@45.36.35.206] has quit [Ping timeout: 245 seconds]
[22:23] <__m4ch1n3__> !py3 max(i for i in  [1, 10, 100] if i < 242)
'''




#buffer
