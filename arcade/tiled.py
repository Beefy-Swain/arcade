"""
Functions and classes for managing a map created in the "Tiled Map Editor"
"""

import xml.etree.ElementTree as etree
import base64
import typing
import gzip
import zlib

from pathlib import Path
from collections import OrderedDict

from arcade.isometric import isometric_grid_to_screen
from arcade import Sprite
from arcade import SpriteList


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
        self.nextlayerid: int
        self.nextobjectid: int

        # tiled.py attributes
        self.tile_sets: typing.Dict[str, TileSet] = {}


class TileSetXML():
    """
    Object for storing a TSX with all associated collision data.

    Attributes:

    """
    def __init__(self):
        """
        Initialization for TileSetXML object.

        Attributes:
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
            :grid (dict[str, [str, int]]): Contains <grid> attributes. See \
            https://doc.mapeditor.org/en/stable/reference/tmx-map-format/#grid
        """
        # TSX spec attributes
        self.name: str
        self.tilewidth: int
        self.tileheight: int
        self.spacing: int
        self.margin: int
        self.tilecount: int
        self.columns: int
        self.grid: typing.Dict[str, typing.Union[str, int]]




class TileSet(typing.NamedTuple):
    """
    NamedTUple for an instance of a tile set used in a map.

    Attributes:
        :firstgid (str): The first global tile ID of this instance of this \
        tile set in this map.
        :tile_set (TileSetXML): The tile set.
    """
    firstgid: int
    tile_set: TileSetXML


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
        self.maps: OrderedDict[typing.
        [str, Path], TileMapXML]
        self.maps = OrderedDict()
        self.tile_sets: typing.Dict[str, TileSetXML] = {}

    def import_tmx(self, tmx_file: typing.
    [str, Path]) -> TileMapXML:
        """
        Imports a TMX file and returns a TileMapXML object

        In addition to importing and returning a tile map, it also adds
        the map to the maps dict and any tile sets to the tile_sets dict
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
                if source in self.tile_sets:
                    # tile set has been parsed, pass it to tile_map
                    tile_map.tile_sets[source] = TileSet(
                        firstgid, self.tile_sets[source])
                else:
                    # tile set is external but not yet parsed
                    tile_map.tile_sets[source] = TileSet(
                        firstgid, self._parse_external_tile_set(
                            tile_set_tag, parent_dir))



        self.maps[tmx_file] = tile_map
        return self.maps[tmx_file]


    def _parse_embedded_tile_set(
            self, tile_set_tag: etree.Element,) -> TileSetXML:
        """
        Parses a tile set that is embedded into a TMX.
        """
        tile_set = TileSetXML()

        tile_set.name = tile_set_tag.attrib['name']
        tile_set.tilewidth = int(tile_set_tag.attrib['tilewidth'])
        tile_set.tileheight = int(tile_set_tag.attrib['tileheight'])
        tile_set.tilecount = int(tile_set_tag.attrib['tilecount'])
        try:
            tile_set.spacing = tile_set_tag.attrib['spacing']
        except KeyError:
            pass
        try:
            tile_set.margin = tile_set_tag.attrib['margin']
        except KeyError:
            pass
        try:
            tile_set.name = tile_set_tag.attrib['name']
        except KeyError:
            pass
        try:
            tile_set.name = tile_set_tag.attrib['name']
        except KeyError:
            pass
        try:
            tile_set.name = tile_set_tag.attrib['name']
        except KeyError:
            pass
        try:
            tile_set.name = tile_set_tag.attrib['name']
        except KeyError:
            pass

        return tile_set

    def _parse_external_tile_set(
            self,
            tile_set_tag: etree.Element,
            parent_dir: typing.
            [Path]) -> TileSetXML:
        """
        Parses a tile set that is external of any TMX.
        """
        if parent_dir:
            source = tile_set_tag.attrib['source']

        tile_set = TileSetXML()

        if parent_dir:
            self.tile_sets[source] = tile_set
            return self.tile_sets[source]
        else:
            return tile_set



















#buffer
