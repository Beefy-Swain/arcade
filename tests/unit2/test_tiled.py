import os
import arcade
import arcade.tiled

import pytest

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

SPRITE_SCALING = 1
GRAVITY = 1.1

class BasicTestWindow(arcade.Window):

    def __init__(self, width, height, title, map_name):
        super().__init__(width, height, title)
        file_path = os.path.dirname(os.path.abspath(__file__))
        os.chdir(file_path)

        self.layers = []
        my_map = arcade.tiled.read_tiled_map(map_name, 1)
        for layer in my_map.layers:
            self.layers.append(arcade.tiled.generate_sprites(
                my_map, layer, 1, "../../arcade/examples/"))

    def on_draw(self):
        arcade.start_render()
        for layer in self.layers:
            layer.draw()


class CollisionTestWindow(BasicTestWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.player_list = arcade.SpriteList()
        self.player_sprite = arcade.Sprite(
            "../../arcade/examples/images/character.png", SPRITE_SCALING)
        self.player_sprite.center_x = 400
        self.player_sprite.center_y = 800
        self.player_list.append(self.player_sprite)

        self.physics_engine = arcade.PhysicsEnginePlatformer(
            self.player_sprite, self.layers[0], gravity_constant=GRAVITY)

    def on_draw(self):
        super().on_draw()
        self.player_list.draw()

    def update(self, delta_time):
        self.physics_engine.update()


## embedded multi-file tilesets ##
def test_map_csv():
    """
    tmx saved with csv formatted layer data
    """
    window = BasicTestWindow(
        SCREEN_WIDTH,
        SCREEN_HEIGHT,
        "Test Text",
        "../../arcade/examples/map_csv.tmx"
    )
    window.test()
    window.close()

# no current support for XML map format
@pytest.mark.xfail
def test_map_xml():
    """
    tmx saved with xml formatted layer data
    """
    window = BasicTestWindow(
        SCREEN_WIDTH,
        SCREEN_HEIGHT,
        "Test Text",
        "../../arcade/examples/map_xml.tmx"
    )
    window.test()
    window.close()

def test_map_base64():
    """
    tmx saved with base64 encoded layer data
    """
    window = BasicTestWindow(
        SCREEN_WIDTH,
        SCREEN_HEIGHT,
        "Test Text",
        "../../arcade/examples/map_base64.tmx"
    )
    window.test()
    window.close()

def test_map_base64_gzip():
    """
    tmx saved with gzip compressed base64 encoded layer data
    """
    window = BasicTestWindow(
        SCREEN_WIDTH,
        SCREEN_HEIGHT,
        "Test Text",
        "../../arcade/examples/map_base64_gzip.tmx"
    )
    window.test()
    window.close()

def test_map_base64_zlib():
    """
    tmx saved with zlib compressed base64 encoded layer data
    """
    window = BasicTestWindow(
        SCREEN_WIDTH,
        SCREEN_HEIGHT,
        "Test Text",
        "../../arcade/examples/map_base64_zlib.tmx"
    )
    window.test()
    window.close()

## external multi-file tilesets ##
def test_map_external_tileset():
    """
    tmx using external tileset
    """
    window = BasicTestWindow(
        SCREEN_WIDTH,
        SCREEN_HEIGHT,
        "Test Text",
        "../../arcade/examples/map_external_tileset.tmx"
    )
    window.test()
    window.close()

# rotation is not supported yet
# https://doc.mapeditor.org/en/stable/reference/tmx-map-format/#tile-flipping
@pytest.mark.xfail
def test_map_rotation():
    """
    tmx with rotated tiles in it's layers
    """
    window = BasicTestWindow(
        SCREEN_WIDTH,
        SCREEN_HEIGHT,
        "Test Text",
        "../../arcade/examples/map_rotation.tmx"
    )
    window.test()
    window.close()

def test_map_polygon_collision():
    """
    tmx with polygon collision
    window.player_sprite should collide at Y 575
    """
    window = CollisionTestWindow(
        SCREEN_WIDTH,
        SCREEN_HEIGHT,
        "Test Text",
        "../../arcade/examples/map_polygon_collision.tmx"
    )
    window.test(frames=20)
    assert (window.player_sprite.center_y == 575), "Did not collide correctly"
    window.close()

@pytest.mark.xfail
def test_map_rectangle_collision():
    """
    tmx with polygon collision
    window.player_sprite should collide at Y 575
    """
    window = CollisionTestWindow(
        SCREEN_WIDTH,
        SCREEN_HEIGHT,
        "Test Text",
        "../../arcade/examples/map_rectangle_collision.tmx"
    )
    window.test(frames=20)
    assert (window.player_sprite.center_y == 575), "Did not collide correctly"
    window.close()
