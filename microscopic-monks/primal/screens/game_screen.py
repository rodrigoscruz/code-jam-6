import random

from primal.engine.screen import Screen
from primal.engine.camera import OrthographicCamera
from primal.engine.sprite import Player, ColorSprite
from primal.engine.world import World
from primal.engine import keys
from primal.screens.death_screen import DeathScreen

from primal.gui.health import HealthBar
from primal.gui.inventory import Inventory


class GameScreen(Screen):
    VP_WIDTH = 1280
    VP_HEIGHT = 720

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.remove = 1

        self.dividend = 10

        self.clicked_features = dict()
        self.last_clicked = 0.0

        self.camera = OrthographicCamera(self.canvas, self.VP_WIDTH, self.VP_HEIGHT)
        self.camera.start_region()

        self.zoom = 1.0

        self.world = World((0, 0))
        self.world.draw(self.canvas)

        self.player = Player('player.png', (0, 0), (40, 80), 0)
        self.player.draw(self.canvas)

        self.world.draw_top(self.canvas)

        self.camera.end_region()

        # render gui
        self.gui_camera = OrthographicCamera(self.canvas, self.VP_WIDTH, self.VP_HEIGHT)
        self.gui_camera.start_region()

        self.overlay = ColorSprite('overlay.png', (0, 0),
                                   (self.VP_WIDTH, self.VP_HEIGHT), (1, 1, 1, .3))
        self.overlay.draw(self.canvas)

        self.health_bar = HealthBar((20, 680), (250, 20), 100.0)
        self.health_bar.draw(self.canvas)

        self.inventory = Inventory((20, 20))
        self.inventory.draw(self.canvas)
        self.gui_camera.end_region()
        self.timer = 0
        self.timerValue = 0

        self.update_sected_item()

    def update(self, delta: float):
        if self.disable:
            return

        # Maybe move it to player update?
        pos_x, pos_y = self.player.get_position()
        dx, dy = 0, 0

        if self.is_key_pressed(keys.KEY_LEFT):
            dx -= Player.SPEED * delta
        if self.is_key_pressed(keys.KEY_RIGHT):
            dx += Player.SPEED * delta

        if self.is_key_pressed(keys.KEY_UP):
            dy += Player.SPEED * delta
        if self.is_key_pressed(keys.KEY_DOWN):
            dy -= Player.SPEED * delta

        if dx != 0.0 or dy != 0.0:
            px, py = self.player.get_center()
            dx, dy = self.process_player_position_deltas(px, py, dx, dy, delta)

        # Check for clicked features
        self.last_clicked -= delta
        if self.last_clicked < 0:
            self.last_clicked = 0

        if dx != 0.0 or dy != 0.0:
            self.player.walk(delta)
        else:
            self.player.stop()

        self.player.set_position((pos_x + dx, pos_y + dy))
        self.player.set_rotation(self.get_mouse_position())

        cx, cy = self.player.get_center()
        self.process_player_nearby(cx, cy, delta)

        if self.last_clicked == 0:
            if 'left' in self.engine.mouse_keys:
                self.process_click()
                self.last_clicked = 0.03
            if 'right' in self.engine.mouse_keys:
                self.process_left_click()
                self.last_clicked = 0.03

        self.timer += delta
        while self.timer > 1:
            self.timer -= 1
            self.timerValue += 1
            self.health_drop()

        if 'scrolldown' in self.engine.mouse_keys:
            self.zoom += delta * 3
            self.zoom = min(1.6, self.zoom)
        elif 'scrollup' in self.engine.mouse_keys:
            self.zoom -= delta * 3
            self.zoom = max(0.68, self.zoom)

        new_clicked_features = dict()

        for feature, value in self.clicked_features.items():
            new_value = value - delta
            if new_value < 0:
                continue
            if new_value < 1:
                feature.set_alpha(new_value)
            new_clicked_features[feature] = new_value

        self.clicked_features = new_clicked_features
        self.engine.mouse_keys = set()

        self.update_inventory()

        self.world.update(self.player.get_center())

        self.camera.set_zoom(self.zoom)
        self.camera.set_position(*self.player.get_center())  # Updates the position
        self.camera.update()

        if self.health_bar.get_health() <= 0:
            self.engine.set_overlay(DeathScreen())

    def process_player_nearby(self, px, py, delta):
        chunk = self.world.get_chunk_from_coords((px, py))
        for feature in chunk.get_features():
            if feature.does_collide() and feature.type == 'cacti':
                dst = 40 + feature.get_size()[0]
                dst = (dst * dst) / 4
                if feature.distance_to((px, py)) <= dst + 2_000:
                    self.health_bar.set_health(self.health_bar.get_health() - delta * 9)
                    return

    def process_player_position_deltas(self, px, py, dx, dy, delta):
        chunk = self.world.get_chunk_from_coords((px + dx, py + dy))
        for feature in chunk.get_features():
            if feature.does_collide():
                dst = 40 + feature.get_size()[0]
                dst = (dst * dst) / 4
                if feature.distance_to((px, py + dy)) <= dst:
                    dy = 0

                if feature.distance_to((px + dx, py)) <= dst:
                    dx = 0

                if dy == 0 and dx == 0:
                    return 0.0, 0.0
        return dx, dy

    def update_sected_item(self):
        selected = self.inventory.get_active()
        if len(selected) != 0:
            sprite = self.inventory.get_sprite(selected[0])
            self.player.change_item(sprite)
        else:
            self.player.change_item(None)

    def update_inventory(self):
        for i in range(len(keys.NUMERIC_KEYS)):
            if self.is_key_just_pressed(keys.NUMERIC_KEYS[i]):
                self.inventory.set_ative(i)
                self.update_sected_item()
                return

    def process_left_click(self):
        active = self.inventory.get_active()

        if len(active) == 0:
            return

        can_eat = ['bushBB', 'bushBO', 'bushBP', 'bushBR', 'bushBY']
        if active[0] in can_eat:
            self.inventory.remove_item(active[0], 1)
            self.health_bar.set_health(self.health_bar.get_health() + 5)
            self.update_sected_item()

    def process_click(self):
        mx, my = self.engine.mouse_position
        ww, wh = self.engine.window_size

        mx = self.VP_WIDTH - self.VP_WIDTH * mx / ww
        my = self.VP_HEIGHT - self.VP_HEIGHT * my / wh
        mx, my = self.camera.get_position_projection((mx, my))

        pos_x, pos_y = self.player.get_center()

        for chunk in self.world.get_chunk_in_range(1):
            features = chunk.get_features()
            clicked = False
            remove_features = set()

            for feature in features:
                dst = 40 + feature.get_size()[0]
                dst = (dst * dst) / 4
                dst += 12_000

                if feature.distance_to((pos_x, pos_y)) < dst \
                        and feature.collide_with((mx, my), (1, 1)):

                    item = self.inventory.get_active()
                    damage = 1
                    if len(item) != 0 and item[0] in ['shovel', 'spear']:
                        damage = 2

                    feature.hit(damage)
                    if feature.get_health() == 0:
                        remove_features.add(feature)

                        if random.randint(0, 15) == 0:
                            which_weapon = random.randint(0, 1)
                            if which_weapon == 1:
                                self.inventory.add_item('shovel')
                            else:
                                self.inventory.add_item('spear')
                        else:
                            self.inventory.add_item(feature.type)

                        self.update_sected_item()
                        if feature in self.clicked_features:
                            del self.clicked_features[feature]
                    else:
                        self.clicked_features[feature] = 3.5
                    clicked = True
                    break

            for feature in remove_features:
                chunk.remove_feature(feature)

            if len(remove_features) != 0:
                self.world.render_chunk(chunk)

            if clicked:
                return

    def health_drop(self):
        if self.timerValue % 9 == 0:
            self.remove += 1
            self.health_bar.set_health(self.health_bar.get_health() - self.remove)
        elif self.timerValue % 10 == 0:
            self.health_bar.set_health(self.health_bar.get_health() - 1)
