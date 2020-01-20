import os
import sys
import time
import pygame
import random
from constants import *
import texture_ids

if FULLSCREEN:
    screen = pygame.display.set_mode(SIZE, pygame.FULLSCREEN | pygame.HWSURFACE | pygame.DOUBLEBUF)
else:
    screen = pygame.display.set_mode(SIZE, pygame.HWSURFACE | pygame.DOUBLEBUF)

clock = pygame.time.Clock()

all_sprites = pygame.sprite.Group()

start_screen_sprites = pygame.sprite.Group()
perspective_sprites = pygame.sprite.Group()
mouse_focused_sprites = pygame.sprite.Group()
button_sprites = pygame.sprite.Group()
debug_sprites = pygame.sprite.Group()
particles = pygame.sprite.Group()

sprites_group_list = [all_sprites,
                      perspective_sprites,
                      mouse_focused_sprites,
                      button_sprites,
                      debug_sprites]


def crop_image(image, x, y):
    rect = pygame.Rect(0, 0, image.get_width() // x,
                       image.get_height() // y)
    res = []
    for j in range(y):
        for i in range(x):
            frame_location = (rect.w * i, rect.h * j)
            res.append(image.subsurface(pygame.Rect(
                frame_location, rect.size)))
    return res


class LoadingScreen():
    def __init__(self, screen, background_color=(212, 123, 88), text_color=(0, 0, 0)):
        self.screen = screen

        self.font_size = 40
        self.font = pygame.font.Font(os.path.join('data', 'fonts', "RobotoSlab-Bold.ttf"), self.font_size)
        self.line = 0

        self.background_color = background_color
        self.text_color = text_color

        self.elements = []
        self.elements_rendered = []
        self.current_element = ["Loading loading screen", 0, 1]

    def set_element(self, text, count=1):
        self.update_element()
        previous_element_text = self.element_to_str(self.current_element)
        self.elements.append(previous_element_text)
        prv_elem_text_rendered = self.font.render(previous_element_text, 1, self.text_color)
        self.elements_rendered.append(prv_elem_text_rendered)
        self.current_element = [text, 0, count]

    def element_to_str(self, element):
        if element[2] == 1:
            res = element[0]
        else:
            try:
                res = element[0].format(str(element[1]), str(element[2]))
            except:
                res = element[0]
        return res

    def update_element(self):
        element = self.current_element
        if element[1] < element[2]:
            element[1] = element[1] + 1

    def draw(self, update=False):
        draw_y = 0
        self.screen.fill((212, 123, 88))
        for element in self.elements_rendered:
            self.screen.blit(element, (0, draw_y))
            draw_y += self.font_size * 0.8
        current_text = self.element_to_str(self.current_element) + "." * (self.current_element[1] % 4)
        text_rendered = self.font.render(current_text, 1, self.text_color)
        self.screen.blit(text_rendered, (0, draw_y))
        if update:
            self.update_element()
        pygame.display.flip()


class StartScreen():
    def __init__(self, screen):
        self.screen = screen
        self.other_screens = []

        self.start_screen_sprites = pygame.sprite.Group()
        self.perspective_sprites = pygame.sprite.Group()
        self.mouse_focused_sprites = pygame.sprite.Group()
        self.button_sprites = pygame.sprite.Group()
        self.debug_sprites = pygame.sprite.Group()

        self.loading_screen = LoadingScreen(self.screen)

        self.init_background()
        self.init_buttons()

        self.cursor = CursorSprite(self.mouse_focused_sprites)

        self.debug_screen = DebugScreen(self)
        self.settings = SettingsScreen(self)
        self.levels = LevelsScreen(self)

        self.tps = 0
        self.draw_queue = []

    def loop(self):
        self.running = True
        while self.running:
            screen.fill((212, 123, 88))
            self.calculate_sprites()
            # рисуем спрайты
            self.perspective_sprites.draw(self.screen)
            self.button_sprites.draw(self.screen)

            if pygame.mouse.get_focused():
                self.mouse_focused_sprites.draw(self.screen)

            if DEBUG_SCREEN:
                self.debug_screen.update_draw()

            if clock.get_fps() != 0:
                self.tps = 1 / clock.get_fps()
            pygame.display.flip()
            clock.tick(FPS)

    # в функции threaded_loop обработка спрайтов разделена на 2 независимые вещи:
    # обработку движений и отрисовку. Причем обработка находится в высшем приоритете т.к
    # от нее зависит соприкосновение спрайтов. Отрисовка же выполняется раздельно, с свободное
    # от обработки время. Если обработка будет занимать больше времени, чем надо, кадры
    # отрисовываться почти не будут. Это пришлось сделать из-за того, что pygame
    # не использует видеокарту и на слабых компьютерах отрисовка может вызвать
    # прохождение спрайтов друг через друга. Есть настройка, где FPS = TPS для
    # слабых компьютеров, где иначе игра работает плохо.
    #
    # ЭТО ЭКСПЕРИМЕНТАЛЬНЫЙ КОД, КОТОРЫЙ НЕ ИСПОЛЬЗУЕТСЯ
    def threaded_loop(self):
        self.running = True
        draw = True
        next_tick_time = time.time()
        next_frame_time = time.time()
        drawing_time_left = 0
        drawing_queue = []
        time_to_tick = 1 / TPS
        time_to_draw = 1 / FPS

        last_tick_time = 0
        first_tick_since_last_draw_time = time.time()
        tmp_sprites = pygame.sprite.Group()

        while self.running:
            loop_start_time = time.time()
            if next_tick_time < loop_start_time:
                next_tick_time = loop_start_time + time_to_tick
                self.calculate_sprites()
                if time.time() - loop_start_time != 0:
                    self.tps = 1 / (time.time() - last_tick_time)
                last_tick_time = time.time()

            drawing_time_left = time_to_tick - (time.time() - loop_start_time)

            if drawing_queue == [] and draw:
                next_frame_time = time.time() + time_to_draw
                groups_to_draw = [self.perspective_sprites,
                                  self.button_sprites]
                if pygame.mouse.get_focused():
                    groups_to_draw.append(self.mouse_focused_sprites)
                for group in groups_to_draw:
                    drawing_queue += list(group)
                self.screen.fill((212, 123, 88))

            while drawing_time_left > 0 and drawing_queue != [] and next_frame_time < time.time():
                tmp_sprites.add(drawing_queue.pop(0))
                tmp_sprites.draw(self.screen)
                tmp_sprites.empty()
                drawing_time_left = time_to_tick - (time.time() - loop_start_time)

            if DEBUG_SCREEN:
                self.debug_screen.update_draw()
            if drawing_queue == []:
                pygame.display.flip()
                clock.tick()
                if TPS_EQUALS_FPS and clock.get_fps() != 0:
                    time_to_tick = 1 / clock.get_fps()

    def calculate_sprites(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                terminate()

            if event.type == pygame.MOUSEBUTTONDOWN:
                # проверяем, нажимались ли кнопки
                if self.button_play.is_colliding(self.cursor):
                    self.button_play.click()
                if self.button_settings.is_colliding(self.cursor):
                    self.button_settings.click()
                if self.button_close.is_colliding(self.cursor):
                    self.button_close.click()

            if event.type == pygame.MOUSEMOTION:
                self.cursor.rect = event.pos
                distance = 100
                move_x = WIDTH / 2 - event.pos[0]
                move_y = HEIGHT / 2 - event.pos[1]

                # двигаем спрайты фона
                for sprite in self.perspective_sprites:
                    sprite.move_from_default_pos(move_x, move_y, distance)
                    if ADVANCED_GRAPHICS:
                        distance /= 1.3
                    else:
                        distance /= 1.3 ** 2

                # анимация кнопок
                for b in [self.button_play, self.button_settings, self.button_close]:
                    if b.is_colliding(self.cursor):
                        b.animate()
                    else:
                        b.animate(False)

    def init_background(self):
        if ADVANCED_GRAPHICS:
            perspective_sprites_names = ["start_menu_fog_1.png",
                                         "start_menu_landscape_1.png",
                                         "start_menu_fog_2.png",
                                         "start_menu_landscape_2.png",
                                         "start_menu_fog_3.png",
                                         "start_menu_landscape_3.png",
                                         "start_menu_fog_4.png",
                                         "start_menu_landscape_4.png",
                                         "start_menu_fog_5.png",
                                         "start_menu_landscape_5.png",
                                         "start_menu_fog_6.png",
                                         "start_menu_landscape_6.png",
                                         ]
        else:
            perspective_sprites_names = ["start_menu_landscape_1.png",
                                         "start_menu_landscape_2.png",
                                         "start_menu_landscape_3.png",
                                         "start_menu_landscape_4.png",
                                         "start_menu_landscape_5.png",
                                         "start_menu_landscape_6.png",
                                         ]

        ls = self.loading_screen
        ls.set_element("Loading textures {}/{}", len(perspective_sprites_names))

        for name in perspective_sprites_names[::-1]:
            image_name = os.path.join('data', name)
            image = pygame.image.load(image_name).convert_alpha()

            sprite = PerspectiveSprite(image, self.perspective_sprites, 0, 0, 200)

            # экран загрузки
            ls.draw(True)

    def init_buttons(self):
        ls = self.loading_screen
        ls.set_element("Loading buttons")
        self.button_play = ButtonSprite((WIDTH / 2, HEIGHT / 3), 'button_play.png', 0.4, self.levels_screen,
                                        self.button_sprites)
        self.button_settings = ButtonSprite((WIDTH / 2, HEIGHT / 1.7), 'button_settings.png', 0.2, self.settings_screen,
                                            self.button_sprites)
        self.button_close = ButtonSprite((WIDTH - 30, 30), 'button_close.png', 0.15, terminate, self.button_sprites)
        ls.draw(True)

    def levels_screen(self):
        self.running = False
        g = GameScreen(self, "")
        g.loop()
        self.levels.loop()

    def settings_screen(self):
        self.running = False
        self.settings.loop()

    def get_tps(self):
        return self.tps

    def name(self):
        return "start screen"


class GameScreen():
    def __init__(self, parent, level):
        self.parent = parent
        parent.running = False
        self.screen = parent.screen

        self.other_screens = []

        self.all_sprites = pygame.sprite.Group()
        self.start_screen_sprites = pygame.sprite.Group()
        self.perspective_sprites = pygame.sprite.Group()
        self.mouse_focused_sprites = pygame.sprite.Group()
        self.button_sprites = pygame.sprite.Group()
        self.debug_sprites = pygame.sprite.Group()
        self.projectile_sprites = pygame.sprite.Group()
        self.player_projectile_sprites = pygame.sprite.Group()
        self.player_sprites = pygame.sprite.Group()
        self.mob_sprites = pygame.sprite.Group()
        self.weapon_sprites = pygame.sprite.Group()
        self.gui_sprites = pygame.sprite.Group()
        self.spawner_sprites = pygame.sprite.Group()
        self.dead_sprites = pygame.sprite.Group()

        self.loading_screen = LoadingScreen(parent.screen)

        self.cursor = CursorSprite(self.mouse_focused_sprites)

        self.debug_screen = parent.debug_screen
        self.settings = parent.settings_screen
        self.levels = parent.levels

        self.game_field = GameField(self, self.loading_screen, "1.txt", (0, 0))
        self.game_field.init_spawners()

        self.player = Player(self, self.player_sprites, (300, 300), 3)
        self.player.set_weapon(TriangleBlaster(self, self.player,
                                               self.weapon_sprites, self.player_projectile_sprites))

        self.spawners = self.game_field.spawners

        self.healthbar = Healtbar(self.gui_sprites, 10, PLAYER_HEALTH, self.game_field.unit_size // 2, (0, 0))

        self.you_died = YouDiedScreen(self, 4)

    def loop(self):
        self.running = True
        break_reason = "died"
        vec = pygame.math.Vector2
        last_tick = time.time()
        tick_time = 0

        move_map = {pygame.K_w: (0, -1),
                    pygame.K_s: (0, 1),
                    pygame.K_a: (-1, 0),
                    pygame.K_d: (1, 0)}
        shooting = False

        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.MOUSEMOTION:
                    self.cursor.rect = event.pos
                    self.player.weapon.angle = 90 - pygame.math.Vector2(self.player.rect.center[0] - event.pos[0],
                                                                        self.player.rect.center[1] - event.pos[
                                                                            1]).as_polar()[1]

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        shooting = True

                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_SPACE:
                        shooting = False

                if event.type == pygame.MOUSEBUTTONDOWN:
                    self.player_projectile_sprites.update(None, event.pos)

                if event.type == pygame.QUIT:
                    pygame.quit()

            pressed = pygame.key.get_pressed()
            move = [move_map[key] for key in move_map if pressed[key]]
            move_vector = vec(0, 0)
            for i in move:
                move_vector += vec(*i)
            if move_vector != vec(0, 0):
                self.player.move_vector = move_vector.normalize()
                self.player.tick_time = tick_time

            if shooting:
                self.player.weapon.shoot()

            self.spawner_sprites.update()
            self.projectile_sprites.update(tick_time)
            self.player_projectile_sprites.update(tick_time)
            self.weapon_sprites.update()
            self.player.update()
            self.mob_sprites.update(tick_time)
            self.healthbar.update(self.player.health)
            self.dead_sprites.update()
            particles.update(tick_time)

            self.screen.fill((212, 123, 88))
            self.game_field.draw(self.screen)
            self.spawner_sprites.draw(screen)
            self.dead_sprites.draw(screen)
            self.weapon_sprites.draw(screen)
            self.player_sprites.draw(screen)
            self.mob_sprites.draw(screen)
            self.projectile_sprites.draw(screen)
            self.player_projectile_sprites.draw(screen)
            self.gui_sprites.draw(screen)
            particles.draw(screen)

            if pygame.mouse.get_focused():
                self.mouse_focused_sprites.draw(screen)

            if DEBUG_SCREEN:
                self.debug_screen.update_draw()

            if clock.get_fps() != 0:
                self.tps = clock.get_fps()

            if self.player.health <= 0:
                break_reason = "died"
                break

            pygame.display.flip()
            clock.tick()
            tick_time = time.time() - last_tick
            last_tick = time.time()
            # print(self.game_field.position)
        if break_reason == "died":
            self.you_died.loop()
            s.loop()


class YouDiedScreen():
    def __init__(self, parent, time_shown, animate=True):
        vec = pygame.math.Vector2

        self.group = pygame.sprite.Group()
        self.screen = parent.screen

        self.parent = parent
        self.player = pygame.sprite.Sprite(self.group)
        self.player_main_image = pygame.image.load(TEXTURE_PATH + "player.png")
        self.player.image = self.parent.player.image
        self.player.rect = self.parent.player.rect

        self.animate = animate
        self.time_shown = time_shown

        self.font_size = 20
        self.font = pygame.font.Font(os.path.join('data', 'fonts', "RobotoSlab-Bold.ttf"), self.font_size)
        string_rendered = self.font.render("YOU DIED", 1, pygame.Color('red'))
        self.text = pygame.sprite.Sprite(self.group)
        self.text.image = string_rendered
        self.text.rect = self.text.image.get_rect()
        self.text.rect.center = (WIDTH // 2, HEIGHT // 2)

        self.player_start_size = self.player.rect[2]
        self.player_end_size = WIDTH

        self.text_start_size = self.font_size
        self.text_end_size = 100

        self.start_time = time.time()

    def loop(self):
        vec = pygame.math.Vector2

        stop_time = time.time() + self.time_shown
        while True:
            size = (stop_time - time.time()) / self.time_shown
            img_size = int(self.player_start_size * size + self.player_end_size * (1 - size))
            text_size = int(self.text_start_size * size + self.text_end_size * (1 - size))

            print(size, img_size, text_size)
            text_pos = self.text.rect.center
            player_pos = self.player.rect.center

            self.player.image = pygame.transform.scale(self.player_main_image, (img_size, img_size))
            self.font = pygame.font.Font(os.path.join('data', 'fonts', "RobotoSlab-Bold.ttf"), text_size)
            string_rendered = self.font.render("YOU DIED", 1, pygame.Color('red'))
            self.text.image = string_rendered

            self.text.rect = self.text.image.get_rect()
            self.player.rect = self.player.image.get_rect()

            self.player.rect.center = player_pos
            self.text.rect.center = text_pos
            print(text_pos, player_pos)

            self.screen.fill((0, 0, 0))
            self.group.draw(screen)

            if time.time() >= stop_time:
                break

            pygame.display.flip()


class SettingsScreen():
    def __init__(self, parent):
        self.parent = parent
        print("settings init")

    def loop(self):
        print("settings screen")


class LevelsScreen():
    def __init__(self, parent):
        self.parent = parent
        self.screen = screen

        self.start_screen_sprites = pygame.sprite.Group()
        self.perspective_sprites = pygame.sprite.Group()
        self.mouse_focused_sprites = pygame.sprite.Group()
        self.button_sprites = pygame.sprite.Group()
        self.debug_sprites = pygame.sprite.Group()

        self.loading_screen = LoadingScreen(self.screen)



        self.running = True

    def loop(self):
        print("levels screen")

    def init_buttons(self):
        ls = self.loading_screen
        ls.set_element("Loading buttons")
        self.button_close = ButtonSprite((WIDTH - 30, 30),
                        'button_close.png', 0.15, terminate, self.button_sprites)
        ls.draw(True)

    def quit(self):
        self.running = False


#PLAYER AND MOBS
class Player(pygame.sprite.Sprite):
    img = pygame.image.load(TEXTURE_PATH + "player.png")
    size = min(SIZE) // FOV * 0.7
    img = pygame.transform.smoothscale(img, (int(size), int(size))).convert_alpha()

    def __init__(self, parent, group, field_pos, velocity):
        self.parent = parent
        super().__init__(group)

        self.health = PLAYER_HEALTH

        self.velocity = velocity * self.parent.game_field.unit_size
        self.move_vector = pygame.math.Vector2(0, 0)

        self.weapon = Weapon(self.parent, self,
                             self.parent.weapon_sprites, self.parent.projectile_sprites)

        self.image = self.img

        self.rect = self.image.get_rect()
        self.rect.x, self.rect.y = field_pos
        self.move_counter_x, self.move_counter_y = 0, 0
        self.x = self.rect.x - self.parent.game_field.x
        self.y = self.rect.y - self.parent.game_field.y
        self.position = self.x, self.y

        rect_size = PLAYER_ONSCREEN_MOVEMENT_RECT
        border_pos = (WIDTH // rect_size, HEIGHT // rect_size)
        border_size = (WIDTH // rect_size * (rect_size - 2), HEIGHT // rect_size * (rect_size - 2))
        self.onscreen_move_border = pygame.Rect(border_pos, border_size)

        self.tick_time = 0

    def update(self, *args):
        vec = pygame.math.Vector2

        self.move(self.move_vector, self.tick_time, True)
        self.move_vector = vec(0, 0)

        for sprite in pygame.sprite.spritecollide(self, self.parent.projectile_sprites, False):
            self.health -= sprite.hit()

        if self.health <= 0:
            self.kill()

    def move(self, pos, tick_time=None, move_field=False):
        if pos == (0, 0):
            return
        vec = pygame.math.Vector2
        gf = self.parent.game_field

        pos = vec(pos)
        pos *= self.velocity

        if tick_time is not None:
            self.move_counter_x += pos[0] * tick_time
            self.move_counter_y += pos[1] * tick_time
        else:
            self.move_counter_x += pos[0]
            self.move_counter_y += pos[1]
        move_x, move_y = 0, 0

        if abs(self.move_counter_x) >= 1:
            move_x = int(self.move_counter_x)
            self.move_counter_x -= move_x
        if abs(self.move_counter_y) >= 1:
            move_y = int(self.move_counter_y)
            self.move_counter_y -= move_y

        if (move_x, move_y) == (0, 0):
            return

        # check block collision
        pos = self.position
        block = gf.unit_size
        block_pos = b_x, b_y = gf.pos_to_block(self.rect.center)
        rect_vertical = gf.rect((block_pos[0], None), (1, None))
        rect_horizontal = gf.rect((None, block_pos[1]), (None, 1))

        air_top = (gf.is_air(self.rect.center[0], self.rect.bottom - block))
        air_bottom = (gf.is_air(self.rect.center[0], self.rect.top + block))
        air_right = (gf.is_air(self.rect.right + 0, self.rect.center[1]))
        air_left = (gf.is_air(self.rect.left - 0, self.rect.center[1]))

        if self.rect.bottom > rect_horizontal.bottom and not air_bottom:
            move_y = move_y - self.rect.bottom + rect_horizontal.bottom
        elif self.rect.top < rect_horizontal.top and not air_top:
            move_y = move_y - self.rect.top + rect_horizontal.top

        if self.rect.right > rect_vertical.right and not air_right:
            move_x = move_x - self.rect.right + rect_vertical.right
        elif self.rect.left < rect_vertical.left and not air_left:
            move_x = move_x - self.rect.left + rect_vertical.left

        self_move_vec = vec(move_x, move_y)
        field_move_vec = vec(0, 0)

        if move_field:
            # field
            if self.rect.top < self.onscreen_move_border.top:
                field_move_vec += vec(0, self.rect.top - self.onscreen_move_border.top)
            elif self.rect.bottom > self.onscreen_move_border.bottom:
                field_move_vec += vec(0, self.rect.bottom - self.onscreen_move_border.bottom)

            elif self.rect.left < self.onscreen_move_border.left:
                field_move_vec += vec(self.rect.left - self.onscreen_move_border.left, 0)
            elif self.rect.right > self.onscreen_move_border.right:
                field_move_vec += vec(self.rect.right - self.onscreen_move_border.right, 0)

            self_move_vec -= field_move_vec
            gf.move(-field_move_vec)

        self.rect.x += self_move_vec.x
        self.rect.y += self_move_vec.y

        self.x = self.rect.x - self.parent.game_field.x
        self.y = self.rect.y - self.parent.game_field.y
        self.position = self.x, self.y

    def kill(self):
        try:
            self.weapon.kill()
        except:
            pass
        super().kill()

    def set_weapon(self, weapon):
        self.weapon.kill()
        self.weapon = weapon


class Mob(Player):
    img = pygame.image.load(TEXTURE_PATH + "default_mob.png")
    size = min(SIZE) // FOV * 0.7
    img = pygame.transform.smoothscale(img, (int(size), int(size))).convert_alpha()

    def __init__(self, *args):
        vec = pygame.math.Vector2
        block = min(SIZE) // FOV

        super().__init__(*args)

        self.health = 50
        self.fov = 12 * block
        self.shoot_distance = 2.5 * block
        self.move_stop_distance = 2.3 * block
        self.go_away_distance = 1 * block

        self.image = self.img
        center = self.rect.center
        self.rect = self.image.get_rect()
        self.rect.center = center

        self.set_weapon(DefaultMobWeapon(self.parent, self, self.parent.weapon_sprites, self.parent.projectile_sprites))
        self.weapon.owner = self

        vector = vec(self.position) - vec(self.parent.player.position)
        self.vector = vector
        self.to_player = vector.length()
        self.direction = vector.normalize()

        self.last_field_pos = self.parent.game_field.position
        self.next_move_direction_change = time.time()
        self.move_direction = vec(0, 0)
        self.init_time = time.time()

    def update(self, tick_time):
        self.tick_time = tick_time
        vec = pygame.math.Vector2
        self.vector = vec(self.parent.player.position) - vec(self.position)
        self.to_player = self.vector.length()

        self.move_ai()

        for sprite in pygame.sprite.spritecollide(self, self.parent.player_projectile_sprites, False):
            self.health -= sprite.hit()

        if self.health <= 0:
            self.kill()

        self.rect.x += self.parent.game_field.position[0] - self.last_field_pos[0]
        self.rect.y += self.parent.game_field.position[1] - self.last_field_pos[1]
        self.last_field_pos = self.parent.game_field.position

        if self.init_time + MOB_LIFETIME < time.time():
            self.kill()

    def kill(self):
        self.weapon.kill()
        super().kill()

    def move_ai(self):
        vec = pygame.math.Vector2

        vector = vec(self.parent.player.position) - vec(self.position)

        try:
            self.direction = vector.normalize()
        except:
            pass
        if self.to_player < self.shoot_distance:
            self.weapon.angle = -self.direction.as_polar()[1] - 90
            self.weapon.shoot()

        if self.next_move_direction_change <= time.time():
            try:
                self.move_direction = vector.normalize()
            except:
                pass
        else:
            self.move(self.move_direction, self.tick_time)
            return

        if self.move_stop_distance < self.to_player < self.fov:
            self.move(self.move_direction, self.tick_time)

        elif self.go_away_distance < self.to_player < self.move_stop_distance:
            self.move_direction.rotate_ip(random.choice([-1, 1]) * 90)
            self.move(-self.move_direction, self.tick_time)
            self.next_move_direction_change = time.time() + 0.25 + random.random() * 0.5

        elif self.to_player < self.go_away_distance:
            self.move_direction.rotate_ip(random.randint(-30, 30))
            self.move(-self.move_direction, self.tick_time)
            self.next_move_direction_change = time.time() + 0.5


class Sniper(Mob):
    img = pygame.image.load(TEXTURE_PATH + "sniper_mob.png")
    size = min(SIZE) // FOV * 0.4
    img = pygame.transform.smoothscale(img, (int(size), int(size))).convert_alpha()

    def __init__(self, *args):
        block = min(SIZE) // FOV

        super().__init__(*args)

        self.image = self.img
        center = self.rect.center
        self.rect = self.image.get_rect()
        self.rect.center = center

        self.health = 25
        self.fov = 16 * block
        self.shoot_distance = 10 * block
        self.move_stop_distance = 8 * block
        self.go_away_distance = 6 * block

        self.set_weapon(MobSniperRiffle(self.parent, self,
                                        self.parent.weapon_sprites, self.parent.projectile_sprites))

        self.velocity //= 2


class Terrorist(Mob):
    img = pygame.image.load(TEXTURE_PATH + "terrorist_mob.png")
    size = min(SIZE) // FOV * 0.6
    img = pygame.transform.smoothscale(img, (int(size), int(size))).convert_alpha()

    def __init__(self, *args):
        block = min(SIZE) // FOV

        super().__init__(*args)

        self.image = self.img
        center = self.rect.center
        self.rect = self.image.get_rect()
        self.rect.center = center

        self.health = 75
        self.fov = 6 * block
        self.shoot_distance = 3 * block
        self.move_stop_distance = 2.7 * block
        self.go_away_distance = 2.6 * block

        self.set_weapon(MobMachineGun(self.parent, self,
                                      self.parent.weapon_sprites, self.parent.projectile_sprites))

        self.velocity *= 1.2


class Spawner(Player):
    def __init__(self, *args, **kwargs):
        vec = pygame.math.Vector2
        super().__init__(*args)

        image = pygame.image.load(TEXTURE_PATH + "spawner.png")
        size = min(SIZE) // FOV
        self.size = size
        image = pygame.transform.smoothscale(image, (int(size), int(size))).convert_alpha()
        self.image = image

        self.set_weapon(None)
        self.do_spawn = True

        self.spawn_rate = 5
        self.spawn_count = 2
        self.start_wave = 0
        self.spawn_mobs = (Mob, Sniper, Terrorist)
        self.health = 100
        self.heart_size = min(SIZE) // (FOV * 5)

        self.last_field_pos = self.parent.game_field.position
        self.next_spawn_time = time.time() + self.spawn_rate

        self.healthbar = Healtbar(self.parent.gui_sprites, 5, self.health, self.heart_size,
                                  (self.rect.topleft) + vec(0, -self.heart_size))
        self.last_field_pos = self.parent.game_field.position
        self.next_spawn_time = time.time() + self.spawn_rate

    def update(self, *args):
        vec = pygame.math.Vector2
        if self.health <= 0:
            self.kill()

        if time.time() > self.next_spawn_time:
            self.spawn()
            self.next_spawn_time = time.time() + self.spawn_rate

        for sprite in pygame.sprite.spritecollide(self, self.parent.player_projectile_sprites, False):
            self.health -= sprite.hit(False)

        self.healthbar.update(self.health)
        self.healthbar.move((self.rect.topleft) + vec(0, -self.heart_size))

        self.rect.x += self.parent.game_field.position[0] - self.last_field_pos[0]
        self.rect.y += self.parent.game_field.position[1] - self.last_field_pos[1]
        self.last_field_pos = self.parent.game_field.position

    def spawn(self):
        if not self.do_spawn:
            return
        vec = pygame.math.Vector2
        for mob in range(self.spawn_count):
            block = min(SIZE) // FOV
            position = vec(0, -block) + vec(0, -1) * random.random() * block
            for _ in range(5):
                vector = position.rotate(random.randint(0, 360))
                tmp_pos = self.rect.center + vector
                if self.parent.game_field.is_air(*tmp_pos):
                    break
            mob = random.choice(self.spawn_mobs)(self.parent, self.parent.mob_sprites, tmp_pos, 1)
        for _ in range(10):
            particle_offset = vec(random.randint(0, self.size), random.randint(0, self.size))
            Cloud(self.parent, self.size // 3, self.rect.topleft + particle_offset, 1, 1, 2, 1)

    def kill(self):
        tmp = BrokenSpawner(self.parent, self.parent.dead_sprites, self.rect.topleft)
        self.healthbar.kill()
        super().kill()


class BrokenSpawner(pygame.sprite.Sprite):
    def __init__(self, parent, group, pos):
        super().__init__(group)
        self.parent = parent

        image = pygame.image.load(TEXTURE_PATH + "broken_spawner.png")
        size = min(SIZE) // FOV
        self.size = size
        image = pygame.transform.smoothscale(image, (int(size), int(size))).convert_alpha()
        self.image = image
        self.rect = image.get_rect()

        self.rect.topleft = pos
        self.last_field_pos = self.parent.game_field.position

        self.particles_left = 10
        self.particles_interval = 0.3
        self.next_particle = time.time()

    def update(self):
        self.rect.x += self.parent.game_field.position[0] - self.last_field_pos[0]
        self.rect.y += self.parent.game_field.position[1] - self.last_field_pos[1]
        self.last_field_pos = self.parent.game_field.position

        if self.particles_left > 0 and self.next_particle <= time.time(): # death_animation
            for _ in range(self.particles_left):
                particle_offset = pygame.math.Vector2(random.randint(0, self.size), random.randint(0, self.size))
                Cloud(self.parent, int(self.size / 1.5), self.rect.topleft + particle_offset, 0.3, 0.1, 0.5, 0.5)
            for _ in range(self.particles_left * 3):
                particle_offset = pygame.math.Vector2(random.randint(0, self.size), random.randint(0, self.size))
                Explosion(self.parent, int(self.size / 3), self.rect.topleft + particle_offset, 0.4, 0.1, 0.6, 1)
            self.particles_left -= 1
            self.next_particle = time.time() + self.particles_interval


# WEAPONS
class Weapon(pygame.sprite.Sprite):
    def __init__(self, parent=None, owner=None, group=None, projectile_group=None):
        super().__init__(group)
        self.parent = parent
        self.owner = owner
        self.p_group = projectile_group

        self.angle = 90

        image = pygame.image.load(TEXTURE_PATH + "none.png")
        image = pygame.transform.scale(image, ((min(SIZE) // FOV) // 3, (min(SIZE) // FOV) // 3))
        self.image = image
        self.default_image = image

        self.rect = self.image.get_rect()

        self.reloading_time = 0.5  # second
        self.p_damage = 10
        self.p_penetration = 1  # how many entities it can fly through
        self.p_velocity = 1  # tiles/sec
        self.p_size = (min(SIZE) // FOV) // 3
        self.p_image = "none.png"
        self.p_distance = 5  # tiles

        self.p_damage_offset = 0
        self.p_penetration_offset = 0
        self.p_velocity_offset = 0
        self.p_size_offset = 0
        self.p_angle_offset = 0
        self.p_distance_offset = 0

        self.next_shot_time = time.time()

    def shoot(self):
        if self.next_shot_time <= time.time():
            Projectile(self.parent,
                       self.owner,
                       self.p_group,
                       self.rect.center,
                       self.p_image,
                       self.p_damage + + (random.random() - 0.5) * self.p_damage_offset,
                       self.p_penetration + (random.random() - 0.5) * self.p_penetration_offset,
                       self.p_velocity + (random.random() - 0.5) * self.p_velocity_offset,
                       self.angle + (random.random() - 0.5) * self.p_angle_offset,
                       self.p_size + int((random.random() - 0.5) * self.p_size_offset),
                       self.p_distance + (random.random() - 0.5) * self.p_distance_offset,
                       True)
            self.next_shot_time = time.time() + self.reloading_time

    def update(self, *args):
        self.image = pygame.transform.rotate(self.default_image, self.angle)
        self.rect = self.image.get_rect()
        self.rect.center = self.owner.rect.center

    def kill(self):
        self.next_shot_time = time.time() + 10000
        super().kill()


class TriangleBlaster(Weapon):
    def __init__(self, *args):
        super().__init__(*args)

        x_crop, y_crop = 10, 1
        image_scale = 0.6

        image = pygame.image.load(TEXTURE_PATH + "triangle_blaster.png")
        image = pygame.transform.smoothscale(image, (int((min(SIZE) // FOV) * x_crop * image_scale),
                                                     int((min(SIZE) // FOV) * y_crop * 2 * image_scale)))

        images = crop_image(image, x_crop, y_crop)
        self.i_unloaded = images[0]
        self.i_loaded = images[-1]
        self.i_loading = images[1:]

        self.images = images
        self.index = 9

        self.image = pygame.transform.rotate(images[0], self.angle)
        self.rect = self.image.get_rect()
        self.rect.center = WIDTH // 2, HEIGHT // 2
        self.next_image_swap = time.time()

        self.state = 2  # 0 - unloaded, 1 - loading, 2 - loaded
        self.reloading_time = 2  # second
        self.p_damage = 20
        self.p_penetration = 8  # how many entities it can fly through
        self.p_velocity = 4  # tiles/sec
        self.p_size = (min(SIZE) // FOV) // 3
        self.p_image = "triangle_blaster_projectile.png"
        self.p_distance = 10  # tiles
        self.p_penetration_timing = 0.1

        self.state_changed = True

    def shoot(self):
        if self.state == 2 and self.next_shot_time <= time.time():
            for i in range(-20, 40, 20):
                Projectile(self.parent,
                           self.owner,
                           self.p_group,
                           self.rect.center,
                           self.p_image,
                           self.p_damage,
                           self.p_penetration,
                           self.p_velocity / (abs(i / 100) + 0.8),
                           self.angle + i,
                           self.p_size,
                           self.p_distance,
                           self.p_penetration_timing,
                           True)
            self.state = 0
            self.index = 0
            self.next_shot_time = time.time() + self.reloading_time

    def update(self):
        prev_state = self.state

        if self.state == 0:
            self.state = 1
            self.index = 0
            self.next_image_swap = time.time()

        elif self.state == 1 and self.next_image_swap <= time.time():
            if self.index < 9:
                self.index += 1
            if self.index == 9 or self.next_shot_time <= time.time():
                self.state = 2
            else:
                self.next_image_swap += self.reloading_time / len(self.i_loading)

        self.image = pygame.transform.rotate(self.images[self.index], self.angle)
        self.rect = self.image.get_rect()
        self.rect.center = self.owner.rect.center

        if prev_state != self.state:
            self.state_changed = True
        else:
            self.state_changed = False


class DefaultMobWeapon(Weapon):
    def __init__(self, *args):
        super().__init__(*args)

        image = pygame.image.load(TEXTURE_PATH + "default_mob_weapon.png")
        image = pygame.transform.scale(image, (int((min(SIZE) // FOV) / 2.5), (min(SIZE) // FOV)))
        self.image = image
        self.default_image = image

        self.reloading_time = 0.7
        self.p_damage = 2.5
        self.p_penetration = 1
        self.p_velocity = 3
        self.p_size = (min(SIZE) // FOV) // 3
        self.p_image = "default_mob_projectile.png"
        self.p_distance = 6

        self.p_angle_offset = 30
        self.p_distance_offset = 2


class MachineGun(Weapon):
    def __init__(self, *args):
        super().__init__(*args)

        image = pygame.image.load(TEXTURE_PATH + "machine_gun.png")
        image = pygame.transform.scale(image, (int((min(SIZE) // FOV) / 3), (min(SIZE) // FOV)))
        self.image = image
        self.default_image = image

        self.reloading_time = 0.03
        self.p_damage = 1
        self.p_penetration = 2
        self.p_velocity = 3
        self.p_size = (min(SIZE) // FOV) // 7
        self.p_image = "machine_gun_projectile.png"
        self.p_distance = 6

        self.p_velocity_offset = 1.2
        self.p_distance_offset = 2
        self.p_size_offset = (min(SIZE) // FOV) // 16
        self.p_angle_offset = 30

    def shoot(self):
        if self.next_shot_time <= time.time():
            Projectile(self.parent,
                       self.owner,
                       self.p_group,
                       self.rect.center,
                       self.p_image,
                       self.p_damage,
                       self.p_penetration,
                       self.p_velocity + (random.random() - 0.5) * self.p_velocity_offset,
                       self.angle + (random.random() - 0.5) * self.p_angle_offset,
                       self.p_size + int((random.random() - 0.5) * self.p_size_offset),
                       self.p_distance + (random.random() - 0.5) * self.p_distance_offset)
            self.next_shot_time = time.time() + self.reloading_time


class MobMachineGun(MachineGun):
    def __init__(self, *args):
        super().__init__(*args)

        self.reloading_time = 0.05
        self.p_damage = 0.3
        self.p_penetration = 2
        self.p_velocity = 3.5
        self.p_size = (min(SIZE) // FOV) // 8
        self.p_image = "machine_gun_projectile.png"
        self.p_distance = 5

        self.p_velocity_offset = 1.2
        self.p_distance_offset = 2
        self.p_size_offset = (min(SIZE) // FOV) // 20
        self.p_angle_offset = 40


class SniperRiffle(Weapon):
    def __init__(self, *args):
        super().__init__(*args)

        image = pygame.image.load(TEXTURE_PATH + "sniper_riffle.png")
        image = pygame.transform.scale(image, (int((min(SIZE) // FOV) / 3), (min(SIZE) // FOV)))
        self.image = image
        self.default_image = image

        self.reloading_time = 0.7
        self.p_damage = 10
        self.p_penetration = 20
        self.p_velocity = 7
        self.p_size = (min(SIZE) // FOV) // 3
        self.p_image = "sniper_riffle_projectile.png"
        self.p_distance = 16
        self.p_penetration_timing = 0.01

        self.p_velocity_offset = 0.5
        self.p_distance_offset = 2
        self.p_angle_offset = 2

    def shoot(self):
        if self.next_shot_time <= time.time():
            SniperProjectile(self.parent,
                             self.owner,
                             self.p_group,
                             self.rect.center,
                             self.p_image,
                             self.p_damage,
                             self.p_penetration,
                             self.p_velocity + (random.random() - 0.5) * self.p_velocity_offset,
                             self.angle + (random.random() - 0.5) * self.p_angle_offset,
                             self.p_size,
                             self.p_distance + (random.random() - 0.5) * self.p_distance_offset,
                             self.p_penetration_timing,
                             False,
                             False)
            self.next_shot_time = time.time() + self.reloading_time
            for _ in range(20):
                ShootParticle(self.parent, 5, self.rect.center, 6, 5, 0.2, 0.15, angle=self.angle)


class MobSniperRiffle(SniperRiffle):
    def __init__(self, *args):
        super().__init__(*args)

        self.reloading_time = 1.5
        self.p_damage = 1
        self.p_penetration = 17
        self.p_velocity = 5
        self.p_size = (min(SIZE) // FOV) // 4
        self.p_image = "sniper_riffle_projectile.png"
        self.p_distance = 16
        self.p_penetration_timing = 0.015

        self.p_velocity_offset = 0.5
        self.p_distance_offset = 2
        self.p_angle_offset = 3


class LollyBomb(Weapon):
    def __init__(self, *args):
        super().__init__(*args)

        self.reloading_time = 5
        self.p_damage = 800
        self.p_penetration = 10
        self.p_velocity = 6
        self.p_size = (min(SIZE) // FOV) // 2
        self.p_image = "lolly_bomb_projectile.png"
        self.p_distance = 1.5
        self.p_penetration_timing = 0

        self.p_velocity_offset = 4
        self.p_distance_offset = 1

    def shoot(self):
        if self.next_shot_time <= time.time():
            for i in range(0, 360, 20):
                LollyBombProjectile(self.parent,
                                    self.owner,
                                    self.p_group,
                                    self.parent.cursor.rect,
                                    self.p_image,
                                    self.p_damage + + (random.random() - 0.5) * self.p_damage_offset,
                                    self.p_penetration + (random.random() - 0.5) * self.p_penetration_offset,
                                    self.p_velocity + (random.random() - 0.5) * self.p_velocity_offset,
                                    self.angle + i,
                                    self.p_size + int((random.random() - 0.5) * self.p_size_offset),
                                    self.p_distance + (random.random() - 0.5) * self.p_distance_offset,
                                    True)
                for _ in range(25):
                    Explosion(self.parent, 15, self.parent.cursor.rect, 2, 4, 0.25, 0.5)
            self.next_shot_time = time.time() + self.reloading_time


#PROJECTILES
class Projectile(pygame.sprite.Sprite):
    def __init__(self, parent, owner, group, pos, image, damage,
                 penetration, velocity, angle, size, max_distance, penetration_timing=0.1,
                 aim_at_update=False, check_wall_collision=True):

        super().__init__(group)

        self.parent = parent
        self.owner = owner

        self.main_image = pygame.image.load(TEXTURE_PATH + image)
        self.main_image = pygame.transform.scale(self.main_image, (size, size))

        vec = pygame.math.Vector2

        self.image = self.main_image
        self.rect = self.image.get_rect()
        self.rect.center = pos

        self.start_field_pos = self.parent.game_field.position

        self.vector_scale = min(SIZE) // FOV
        self.vector = vec(0, -1) * self.vector_scale
        self.rotate(angle)

        self.move_counter_x, self.move_counter_y = 0, 0

        self.init_damage = damage
        self.damage = damage
        self.init_penetration = penetration
        self.penetration = penetration
        self.velocity = velocity
        self.size = size
        self.angle = angle

        self.max_distance = max_distance * self.vector_scale
        self.current_distance = 0

        self.penetration_timing = penetration_timing

        self.aim_at_update = aim_at_update if self.parent.player == self.owner else False
        self.check_blocks = check_wall_collision

        self.move((min(SIZE) // FOV) // 2)

        self.init_time = time.time()

        self.aim_limit = 1
        self.last_field_pos = self.parent.game_field.position
        self.next_hit_time = time.time()

    def set_vector(self, vector):
        self.vector = vector.normalize()
        self.vector *= self.vector_scale

    def set(self, weapon):
        self.weapon = weapon

    def rotate(self, angle, rotate_image=True):
        self.vector.rotate_ip(-angle)
        r_angle = self.vector.as_polar()[1]
        if rotate_image:
            center = self.rect.center
            self.image = pygame.transform.rotate(self.main_image, -r_angle - 90)
            self.rect.center = center

    def aim_at(self, pos, vel_multiplier, bypass_limit=False):
        if bypass_limit or self.aim_limit > 0:
            vec = pygame.math.Vector2
            aim_pos = vec(pos) - self.rect.center + self.rect[0:2]
            vector = aim_pos - self.rect[0:2]
            if vector == vec(0, 0):
                return
            self.vector = vector.normalize() * self.vector_scale

            self.aim_limit -= 1

            self.max_distance = vector.length() + self.vector_scale * 1
            self.current_distance = 0

            self.velocity *= vel_multiplier

    def set_angle(self, angle, rotate_image):
        self.vector = vec(0, -1)
        self.rotate(angle, rotate_image)
        self.angle = angle

    def move(self, pos=(0, 0), timed=False, tick_time=(1 / FPS)):
        vec = pygame.math.Vector2

        if type(pos) == int or type(pos) == float:
            tmp_pos = vec(0, 1)
            tmp_pos.rotate_ip(-self.angle)
            tmp_pos *= -pos
            pos = tmp_pos

        if timed:
            self.move_counter_x += pos[0] * tick_time
            self.move_counter_y += pos[1] * tick_time

        else:
            self.move_counter_x += pos[0]
            self.move_counter_y += pos[1]

        move_x, move_y = 0, 0

        if abs(self.move_counter_x) >= 1:
            move_x += int(self.move_counter_x)
            self.move_counter_x -= move_x
        if abs(self.move_counter_y) >= 1:
            move_y += int(self.move_counter_y)
            self.move_counter_y -= move_y

        if (move_x, move_y) != (0, 0):
            vector = vec(move_x, move_y)
            self.rect.center += vector
            self.current_distance += vector.length()

    def hit(self, particle=True):
        if time.time() >= self.next_hit_time:
            vec = pygame.math.Vector2
            rtrn = self.damage
            ratio = self.penetration / self.init_penetration
            self.penetration -= 1
            self.damage = self.init_damage * ratio
            self.max_distance -= (self.max_distance - self.current_distance) * (1 / self.init_penetration)
            self.next_hit_time = time.time() + self.penetration_timing

            particle_offset = vec((random.randint(-10, 10), random.randint(-10, 10)))
            if particle:
                for _ in range(10):
                    Blood(self.parent, 10, vec(self.rect.center) + particle_offset,
                          0.2, 0.15, 1.5, 1.8)
            return self.damage
        return 0

    def update(self, tick_time=None, aim_at=None):
        if tick_time is not None:
            self.move(self.vector * self.velocity, True, tick_time)

        if aim_at is not None and self.aim_at_update:
            self.aim_at(aim_at, 2)

        if self.current_distance > self.max_distance or self.penetration <= 0 \
                or (self.colliding_block() and self.check_blocks):
            self.kill()
            ratio = self.penetration / self.init_penetration
            if ratio <= 0:
                ratio = 0
            for _ in range(25):
                Explosion(self.parent, 7 * ratio, self.rect.center, 3 * ratio, 1.5 * ratio, 0.15, 0.1)

        self.rect.x += self.parent.game_field.position[0] - self.last_field_pos[0]
        self.rect.y += self.parent.game_field.position[1] - self.last_field_pos[1]

        self.last_field_pos = self.parent.game_field.position
        self.rotate(0)

    def colliding_block(self):
        return not self.parent.game_field.is_air(*self.rect.center)


class SniperProjectile(Projectile):
    def update(self, *args):
        super().update(*args)

        if self.colliding_block():
            self.hit(False)


class LollyBombProjectile(Projectile):
    next_particle_time = time.time() + 0.1
    particle_count = 100

    def update(self, *args):
        super().update(*args)


#PARTICLES
class Particle(pygame.sprite.Sprite):
    images = pygame.image.load(TEXTURE_PATH + "none_particle.png")
    images = crop_image(images, 10, 1)

    def __init__(self, parent, size, pos, speed, speed_offset, time_alive, time_alive_offset):
        super().__init__(particles)
        vec = pygame.math.Vector2

        self.parent = parent

        image = self.images[random.randint(1, len(self.images)) - 1]
        size = int(size * WIDTH / 900)
        image = pygame.transform.scale(image, (size, size))
        self.image = image

        self.rect = self.image.get_rect()
        self.rect.center = pos

        speed = speed + speed_offset * (random.random() - 0.5)
        self.speed = speed

        self.vector = vec(1, 0) * speed * (min(SIZE) // FOV)
        self.vector.rotate_ip(random.randint(0, 360))

        self.init_time = time.time()
        self.time_alive = time_alive + time_alive_offset * (random.random() - 0.5)

        self.move_counter_x = 0
        self.move_counter_y = 0

        self.last_field_pos = self.parent.game_field.position

    def move(self, pos):
        self.move_counter_x += pos[0]
        self.move_counter_y += pos[1]

        move_x, move_y = 0, 0

        if abs(self.move_counter_x) >= 1:
            move_x = int(self.move_counter_x)
            self.move_counter_x -= move_x
        if abs(self.move_counter_y) >= 1:
            move_y = int(self.move_counter_y)
            self.move_counter_y -= move_y

        if (move_x, move_y) != (0, 0):
            vector = pygame.math.Vector2(move_x, move_y)
            self.rect.center += vector

    def update(self, tick_time):
        time_since_init = time.time() - self.init_time

        self.move(self.vector * tick_time)
        self.image.set_alpha(0.1)

        self.rect.x += self.parent.game_field.position[0] - self.last_field_pos[0]
        self.rect.y += self.parent.game_field.position[1] - self.last_field_pos[1]

        if self.time_alive < time_since_init:
            self.kill()

        self.last_field_pos = self.parent.game_field.position


class Explosion(Particle):
    images = pygame.image.load(TEXTURE_PATH + "explosion.png")
    images = crop_image(images, 10, 1)


class ShootParticle(Particle):
    images = pygame.image.load(TEXTURE_PATH + "explosion.png")
    images = crop_image(images, 10, 1)

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.vector = pygame.math.Vector2(0, -1) * self.speed * (min(SIZE) // FOV)
        self.vector.rotate_ip(random.randint(-20, 20) - kwargs["angle"])

        self.move(self.vector.normalize() * (min(SIZE) // FOV) / 3)


class Blood(Particle):
    images = pygame.image.load(TEXTURE_PATH + "blood.png")
    images = crop_image(images, 10, 1)


class Cloud(Particle):
    images = pygame.image.load(TEXTURE_PATH + "clouds.png")
    images = crop_image(images, 10, 1)


class SpawnCountdown():
    def __init__(self, pos, size, time_left):
        self.time = time_left
        self.next_particle = False

        self.pos = pos
        self.size = size

    def update(self, time_left):
        if int(self.time) > int(time_left):
            self.time = time_left
            self.next_particle = True


# // TODO

class Healtbar():
    def __init__(self, group, heart_count, max_health, size, pos):
        vec = pygame.math.Vector2

        self.group = group
        self.max_health = max_health
        self.heart_count = heart_count
        self.size = size
        self.position = self.x, self.y = pos
        self.heart_health = max_health / heart_count

        heart_image = pygame.image.load(TEXTURE_PATH + "heart.png")
        self.heart_image = pygame.transform.scale(heart_image, (size, size))
        half_heart_image = pygame.image.load(TEXTURE_PATH + "half_heart.png")
        self.half_heart_image = pygame.transform.scale(half_heart_image, (size, size))
        self.nothing_image = pygame.image.load(TEXTURE_PATH + "air.png")

        self.hearts = []
        for i in range(heart_count):
            sprite = pygame.sprite.Sprite(group)
            sprite.image = self.heart_image
            sprite.rect = sprite.image.get_rect()
            sprite.rect.topleft = vec(pos) + vec((size * i, 0))
            self.hearts.append(sprite)

    def update(self, health):
        for i in range(len(self.hearts)):
            if health > i * self.heart_health:
                if health - i * self.heart_health < self.heart_health / 2:
                    self.hearts[i].image = self.half_heart_image
                else:
                    self.hearts[i].image = self.heart_image
            else:
                self.hearts[i].image = self.nothing_image

    def move(self, pos):
        vec = pygame.math.Vector2
        for i in range(len(self.hearts)):
            self.hearts[i].rect.topleft = vec(pos) + vec((self.size * i, 0))

    def kill(self):
        for sprite in self.hearts:
            sprite.kill()


class GameField(pygame.sprite.Group):
    def __init__(self, parent, loading_screen, level, pos=(0, 0)):
        super().__init__()
        self.all_sprites = pygame.sprite.Group()

        self.parent = parent

        ls = loading_screen

        with open(LEVEL_PATH + level, "rt") as file:
            self.level_txt = file.read()

        text = self.level_txt.split("params:")[0]
        txt_map = text.strip().split("\n")
        self.txt_map = txt_map

        self.position = self.x, self.y = pos
        self.move_counter_x, self.move_counter_y = 0, 0

        unit_size = min(SIZE) // FOV
        self.unit_size = unit_size
        size = x, y = len(txt_map[0]), len(txt_map)

        claster_map_size = x_cl, y_cl = x // CLASTER_SIZE + (1 if x % CLASTER_SIZE != 0 else 0), \
                                        y // CLASTER_SIZE + (1 if y % CLASTER_SIZE != 0 else 0)
        claster_size = (CLASTER_SIZE * unit_size, CLASTER_SIZE * unit_size)
        claster_map = [[[]] * x_cl for _ in range(y_cl)]
        sprite_map = [[[]] * x_cl for _ in range(y_cl)]

        ls.set_element("Loading map {}/{}", x_cl * y_cl)

        for j in range(y_cl):
            for i in range(x_cl):
                sur = pygame.Surface(claster_size)
                sur.set_colorkey((0, 0, 0))

                for yy in range(CLASTER_SIZE):
                    for xx in range(CLASTER_SIZE):
                        char_x, char_y = i * CLASTER_SIZE + xx, j * CLASTER_SIZE + yy
                        if char_x >= x or char_y >= y:
                            char = "#"
                        else:
                            char = txt_map[char_y][char_x]

                        try:
                            name = texture_ids.map_textures[ord(char)]
                            image = pygame.image.load(TEXTURE_PATH + name)
                        except:
                            image = pygame.image.load(TEXTURE_PATH + "none.png")
                        image = pygame.transform.scale(image, (unit_size, unit_size))

                        sur.blit(image, (xx * unit_size, yy * unit_size))

                claster_map[j][i] = sur

                sprite = pygame.sprite.Sprite(self, self.all_sprites)
                sprite.image = sur

                sprite.rect = sprite.image.get_rect()
                sprite.rect.x = i * CLASTER_SIZE * unit_size + self.x
                sprite.rect.y = j * CLASTER_SIZE * unit_size + self.y

                sprite_map[j][i] = sprite

                ls.draw(True)

        self.claster_map = claster_map
        self.sprite_map = sprite_map

    def init_spawners(self):
        spawners = []
        text = self.level_txt.split("spawners:")[1]
        for line in text.split(";"):
            try:
                l = dict()
                exec(line, {}, l)
                pos = l["pos"]
                x = pos[0] * self.unit_size
                y = pos[1] * self.unit_size
                spawner = Spawner(self.parent, self.parent.spawner_sprites, (x, y), 0)
                spawners.append(spawner)
            except:
                pass

        self.spawners = spawners

    def move(self, pos=(0, 0)):
        self.move_counter_x += pos[0]
        self.move_counter_y += pos[1]
        move_x, move_y = 0, 0

        if abs(self.move_counter_x) >= 1:
            move_x = int(self.move_counter_x)
            self.move_counter_x -= move_x
        if abs(self.move_counter_y) >= 1:
            move_y = int(self.move_counter_y)
            self.move_counter_y -= move_y

        if (move_x, move_y) != (0, 0):
            for row in self.sprite_map:
                for item in row:
                    item.rect.x += move_x
                    item.rect.y += move_y
            self.x, self.y = self.sprite_map[0][0].rect.x, self.sprite_map[0][0].rect.y
            self.position = self.x, self.y

    def draw(self, screen):
        draw_group = pygame.sprite.Group()

        y_crop_min = (-self.unit_size * CLASTER_SIZE - self.y) // (CLASTER_SIZE * self.unit_size)
        if y_crop_min < 0:
            y_crop_min = 0
        y_crop_max = (-self.unit_size * CLASTER_SIZE - self.y + HEIGHT) // (CLASTER_SIZE * self.unit_size) + 2
        if y_crop_max > len(self.sprite_map):
            y_crop_max = len(self.sprite_map)
        elif y_crop_max < 0:
            y_crop_max = 0
        cropped_y = self.sprite_map[int(y_crop_min):int(y_crop_max)]

        x_crop_min = (-self.unit_size * CLASTER_SIZE - self.x) // (CLASTER_SIZE * self.unit_size)
        if x_crop_min < 0:
            x_crop_min = 0
        x_crop_max = (-self.unit_size * CLASTER_SIZE - self.x + WIDTH) // (CLASTER_SIZE * self.unit_size) + 2
        if x_crop_max > len(self.sprite_map[0]):
            x_crop_max = len(self.sprite_map[0])
        elif x_crop_max < 0:
            x_crop_max = 0

        cropped = []
        for row in cropped_y:
            cropped.append(row[int(x_crop_min):int(x_crop_max)])

        for row in cropped:
            for item in row:
                draw_group.add(item)

        draw_group.draw(screen)
        draw_group.empty()

    def update(self):
        pass

    def get_sprite_rect_list(self):
        for row in self.sprite_map:
            for item in row:
                print(item.rect, end=" ")
            print()

    def get_block_at_pos(self, pos):
        if pos[0] < 0 or pos[1] < 0:
            return None
        try:
            unit_name = self.txt_map[pos[1]][pos[0]]
            return unit_name
        except:
            return None

    def pos_to_field(self, pos):
        x = pos[0] - self.x
        y = pos[1] - self.y
        return x, y

    def pos_to_block(self, pos):
        return [i // self.unit_size for i in self.pos_to_field(pos)]

    def rect(self, pos, size):
        x = (0 if pos[0] is None else pos[0] * self.unit_size + self.x)
        y = (0 if pos[1] is None else pos[1] * self.unit_size + self.y)
        s_x = (WIDTH if size[0] is None else size[0] * self.unit_size)
        s_y = (HEIGHT if size[1] is None else size[1] * self.unit_size)
        return pygame.Rect(x, y, s_x, s_y)

    def is_air(self, x, y, block_pos=False):
        if not block_pos:
            x, y = self.pos_to_block((x, y))
        tmp = self.get_block_at_pos((x, y))
        if tmp is None: return True
        if tmp in ".A":
            return True
        else:
            return False

    def get_block_rect(self, pos):
        size = self.unit_size
        x = pos[0] // size * size + self.x
        y = pos[1] // size * size + self.y

        return pygame.Rect(x, y, size, size)


class PerspectiveSprite(pygame.sprite.Sprite):
    def __init__(self, image, group, pos_x=0, pos_y=0, zoom=0):
        super().__init__(group)
        self.image = pygame.transform.scale(image, (WIDTH + zoom, int(HEIGHT + zoom * HEIGHT / WIDTH)))
        # self.rect = self.image.get_rect()

        self.rect = (pos_x - zoom / 2, pos_y - zoom * HEIGHT / WIDTH / 2)
        self.x = pos_x - zoom / 2
        self.y = pos_y - zoom / 2
        self.zoom = (WIDTH + zoom, HEIGHT + zoom * HEIGHT / WIDTH)

    def move_from_default_pos(self, x, y, distance):
        self.rect = (self.x + x / distance, self.y + y / distance + 40)  # TODO fix getting out of border issue


class CursorSprite(pygame.sprite.Sprite):
    def __init__(self, group=None):
        if group is None:
            super().__init__(mouse_focused_sprites)
        else:
            super().__init__(group)
        cursor_image = pygame.image.load(os.path.join('data', "cursor2.png")).convert_alpha()
        self.image = pygame.transform.smoothscale(cursor_image, (40, 40))
        self.rect = self.image.get_rect()
        self.mask = pygame.mask.from_surface(pygame.image.load(os.path.join('data', "cursor_hitbox.png")))
        pygame.mouse.set_visible(False)


class ButtonSprite(pygame.sprite.Sprite):
    def __init__(self, pos=(0, 0), image_name="none.png", size=1, function=None, group=None, cursor=None):
        if group is None:
            super().__init__(button_sprites)
        else:
            super().__init__(group)
        print(group)

        try:
            image = pygame.image.load(TEXTURE_PATH + image_name).convert_alpha()
        except:
            print('Something is wrong with image or path')
            return

        self.size = size
        self.raw_size = size
        x_size = int(image.get_rect()[2] * size)
        y_size = int(image.get_rect()[3] * size)
        self.raw_image = image
        self.image = pygame.transform.smoothscale(image, (x_size, y_size))

        pos_x = pos[0]
        pos_y = pos[1]
        self.rect = self.image.get_rect()
        self.rect.x = pos_x - x_size / 2
        self.rect.y = pos_y - y_size / 2
        self.function = function

        self.mask = pygame.mask.from_surface(self.image)

        self.cursor = cursor

    def connect(self, function):
        self.function = function

    def click(self):
        if self.function is not None:
            self.function()
        else:
            print("button is not connected")

    def set_size(self, size):
        pos_x = self.rect.x + self.image.get_rect()[2] / 2
        pos_y = self.rect.y + self.image.get_rect()[3] / 2

        self.size = size
        x_size = int(self.raw_image.get_rect()[2] * size)
        y_size = int(self.raw_image.get_rect()[3] * size)
        self.image = pygame.transform.smoothscale(self.raw_image, (x_size, y_size))

        self.rect = self.image.get_rect()
        self.rect.x = pos_x - x_size / 2
        self.rect.y = pos_y - y_size / 2

        self.mask = pygame.mask.from_surface(self.image)

    def is_colliding(self, cursor=None):
        return pygame.sprite.collide_mask(cursor, self)

    def animate(self, state=True):
        if state:
            self.set_size(self.raw_size * 1.1)
        else:
            self.set_size(self.raw_size)


class DebugScreen():
    def __init__(self, parent):
        self.parent = parent

        self.lines = ["FPS: {}", "TPS: {}", "{}x{}"]

        self.font = pygame.font.Font(os.path.join('data', 'fonts', "RobotoSlab-Bold.ttf"), 20)

        self.sprite = pygame.sprite.Sprite(debug_sprites)

    def update_draw(self):
        lines = ["FPS: {}".format(round(clock.get_fps(), 2)),
                 "TPS: {}".format(round(self.parent.get_tps(), 2)),
                 "{}x{}".format(WIDTH, HEIGHT)]
        text_y = 0
        for line in lines:
            string_rendered = self.font.render(line, 1, pygame.Color('white'))
            string_rect = string_rendered.get_rect()
            string_rect.top = text_y
            string_rect.x = 0
            text_y += string_rect.height - 10
            screen.blit(string_rendered, string_rect)

        self.sprite.image = screen
        self.sprite.rect = self.sprite.image.get_size()
        self.sprite.update()

        debug_sprites.draw(screen)


def terminate():
    pygame.quit()
    sys.exit()


def clear_sprites():
    for group in sprites_group_list:
        group.empty()
    screen.fill((212, 123, 88))
    pygame.display.flip()


pygame.init()

s = StartScreen(screen)
s.loop()
terminate()
