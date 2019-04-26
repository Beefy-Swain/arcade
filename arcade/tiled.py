"""
Functions and classes for managing a map created in the "Tiled Map Editor"
"""

import functools
import typing

from pathlib import Path
from collections import OrderedDict

import xml.etree.ElementTree as etree


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


class Image(typing.NamedTuple):
    """
    NamedTuple for image elements.

    This module does not support embedded data in image tags.

    Args:
        :source (Union[None, str]): The reference to the tileset image file. \
        Not that this is a relative path compared to FIXME
        :trans (Union[None, str]): Defines a specific color that is treated \
        as transparent.
        :width (Union[None, str]): The image width in pixels \
        (optional, used for tile index correction when the image changes).
        :height (Union[None, str]): The image height in pixels (optional).
    """
    source: typing.Union[None, str]
    trans:  typing.Union[None, Color]
    width: typing.Union[None, int]
    height: typing.Union[None, int]


class Properties(
        typing.Dict[str, typing.Union[str, int, float, bool, Color, Path]]):
    """
    Dict for storing custom properties.

    Custom 'add' method for converting property values to the type specified.

    Can be used as a child of the map, tileset, tile (when part of a \
    tileset), terrain, layer, objectgroup, object, imagelayer and group \
    elements.

    See \
    https://doc.mapeditor.org/en/stable/reference/tmx-map-format/#properties \
    for more info.
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


class Grid(typing.NamedTuple):
    """
    Contains info for isometric maps.

    This element is only used in case of isometric orientation, \
    and determines how tile overlays for terrain and collision \
    information are rendered.
    """
    orientation: str
    width: int
    height: int


class Terrain(typing.NamedTuple):
    """
    Terrain object.

    Args:
        :name (str): The name of the terrain type.
        :tile (int): The local tile-id of the tile that represents the \
        terrain visually.
    """
    name: str
    tile: int


class Frame(typing.NamedTuple):
    """
    Animation frame object.

    Args:
        :tileid (int): The local ID of a tile within the parent tile set \
        object.
        :duration (int): How long in milliseconds this frame should be \
        displayed before advancing to the next frame.
    """
    tileid: int
    duration: int


class TileTerrain(typing.NamedTuple):
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
    top_left: typing.Union[None, int] = None
    top_right: typing.Union[None, int] = None
    bottom_left: typing.Union[None, int] = None
    bottom_right: typing.Union[None, int] = None



class Tile(typing.NamedTuple):
    """
    Individual tile object.

    Args:
        :id (int): The local tile ID within its tileset.
        :type (str): The type of the tile. Refers to an object type and is \
        used by tile objects.
        :terrain (int): Defines the terrain type of each corner of the tile.
        :probability (float): A percentage indicating the probability that \
        this tile is chosen when it competes with others while editing with \
        the terrain tool.
        :animation (List[Frame]): Each tile can have exactly one animation \
        associated with it.
    """
    id: int
    type: str
    terrain: TileTerrain
    probability: float
    animation: typing.List[Frame]


class TileSet(typing.NamedTuple):
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
    """
    name: str
    tilewidth: int
    tileheight: int
    spacing: typing.Union[None, int]
    margin: typing.Union[None, int]
    tilecount: typing.Union[None, int]
    columns: typing.Union[None, int]
    tileoffset: typing.Union[None, typing.Tuple[int, int]]
    grid: typing.Union[None, Grid]
    properties: typing.Union[None, Properties]
    image: typing.Union[None, Image]
    terraintypes: typing.Union[None, typing.List[Terrain]]
    tiles: typing.Union[None, typing.List[Tile]]


class TileMapXML():
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
        self.tile_sets: OrderedDict[str, TileSet] = OrderedDict


def _parse_embedded_tile_set(tile_set_tag: etree.Element,) -> TileSet:
    """
    Parses a tile set that is embedded into a TMX.
    """

    # get all basic attributes
    name = tile_set_tag.attrib['name']
    tilewidth = int(tile_set_tag.attrib['tilewidth'])
    tileheight = int(tile_set_tag.attrib['tileheight'])

    spacing = None
    try:
        spacing = int(tile_set_tag.attrib['spacing'])
    except KeyError:
        pass

    margin = None
    try:
        margin = int(tile_set_tag.attrib['margin'])
    except KeyError:
        pass

    tilecount = None
    try:
        tilecount = int(tile_set_tag.attrib['tilecount'])
    except KeyError:
        pass

    columns = None
    try:
        columns = int(tile_set_tag.attrib['columns'])
    except KeyError:
        pass

    tileoffset: typing.Union[None, typing.Tuple[int, int]] = None
    try:
        tileoffset_tag = tile_set_tag.find('./tileoffset')
        assert tileoffset_tag is not None
    except AssertionError:
        pass
    else:
        tile_offset_x = int(tileoffset_tag.attrib['x'])
        tile_offset_y = int(tileoffset_tag.attrib['y'])
        tile_offset = (tile_offset_x, tile_offset_y)

    grid = None
    try:
        grid_tag = tile_set_tag.find('./grid')
        assert grid_tag is not None
    except AssertionError:
        pass
    else:
        grid_orientation = grid_tag.attrib['orientation']
        grid_width = int(grid_tag.attrib['width'])
        grid_height = int(grid_tag.attrib['height'])
        grid = Grid(grid_orientation, grid_width, grid_height)

    properties = None
    try:
        properties_tag = tile_set_tag.find('./properties')
        assert properties_tag is not None
    except AssertionError:
        pass
    else:
        properties = Properties()
        for property in properties_tag.findall('./property'):
            name = property.attrib['name']
            property_type = property.attrib['type']
            value = property.attrib['value']
            properties.add(name, property_type, value)

    terraintypes: typing.Union[None, typing.List[Terrain]] = None
    try:
        terraintypes_tag = tile_set_tag.find('./terraintypes')
        assert terraintypes_tag is not None
    except AssertionError:
        pass
    else:
        terraintypes = []
        for terrain in terraintypes_tag.findall('./terrain'):
            name = property.attrib['name']
            tile = int(property.attrib['tile'])
            terraintypes.append(Terrain(name, tile))

    image = None
    try:
        image_tag = tile_set_tag.find('./image')
        assert image_tag is not None
    except AssertionError:
        pass
    else:
        image_source = None
        try:
            image_source = image_tag.attrib['source']
        except KeyError:
            pass

        image_trans = None
        try:
            image_trans = Color(image_tag.attrib['trans'])
        except KeyError:
            pass

        image_width = None
        try:
            image_width = int(image_tag.attrib['width'])
        except KeyError:
            pass

        image_height = None
        try:
            image_height = int(image_tag.attrib['height'])
        except KeyError:
            pass

        image = Image(image_source, image_trans, image_width, image_height)


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

def _parse_external_tile_set(tile_set_tag: etree.Element,
                             parent_dir: typing.Union[Path]) -> TileSetXML:
    """
    Parses a tile set that is external of any TMX.
    """
    if parent_dir:
        source = tile_set_tag.attrib['source']

    tile_set = TileSetXML()

    self.external_tile_sets[source] = tile_set
    return self.external_tile_sets[source]


class Tiled():
    """
    Controller object for importing TMX files.

    Handles importing TMX files and resolving TSX files.

    Attributes:
        :maps (dict): Dict of all TileMapXML objects by key=tmx_file.
        :external_tile_sets (dict): Dict of all external TileSetXML objects. \
        This means tile sets that are not 'embedded' into the TMX file.
    """
    def __init__(self):
        """
        Init method for Tiled.
        """
        self.external_tile_sets: typing.Dict[str, TileSetXML] = {}

    def import_tmx(self, tmx_file: typing.Union[str, Path]) -> TileMapXML:
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

        tile_map = TileMapXML()

        map_tree = etree.parse(str(tmx_file))
        map_tag = map_tree.getroot()

        tile_set_tag_list = map_tag.findall('./tileset')
        for tile_set_tag in tile_set_tag_list:
            # tiled docs are ambiguous about the 'firstgid' attribute
            # current understanding is for the purposes of mapping the layer
            # data to the tile set data, add the 'firstgid' value to each
            # tile 'id'; this means that the 'firstgid' is specific to each,
            # tile set as they pertain to the map, not tile set specific as
            # the tiled docs can make it seem
            # 'firstgid' is saved beside each TileMapXML
            firstgid = int(tile_set_tag.attrib['firstgid'])
            try:
                # check if this controller has parsed this tileset yet
                source = tile_set_tag.attrib['source']
            except KeyError:
                # the tile set in embedded
                name = tile_set_tag.attrib['name']
                tile_map.tile_sets[name] = TileSet(
                    firstgid, self._parse_embedded_tile_set(tile_set_tag))
            else:
                if source in self.external_tile_sets:
                    # tile set has been parsed, pass it to tile_map
                    tile_map.tile_sets[source] = TileSet(
                        firstgid, self.external_tile_sets[source])
                else:
                    # tile set is external but not yet parsed
                    tile_map.tile_sets[source] = TileSet(
                        firstgid, self._parse_external_tile_set(
                            tile_set_tag, parent_dir))



        self.maps[tmx_file] = tile_map
        return self.maps[tmx_file]



















#buffer
