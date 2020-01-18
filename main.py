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
    def __init__(self, screen, background_color = (212, 123, 88), text_color=(0, 0, 0)):
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
    # ЭТО ЭКСПЕРИМЕНТАЛЬНАЯ НАСТРОЙКА
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
        self.button_play = ButtonSprite((WIDTH / 2, HEIGHT / 3), 'button_play.png', 0.4, self.levels_screen, self.button_sprites)
        self.button_settings = ButtonSprite((WIDTH / 2, HEIGHT / 1.7), 'button_settings.png', 0.2, self.settings_screen, self.button_sprites)
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
        self.screen = parent.screen

        self.other_screens = []

        self.all_sprites = pygame.sprite.Group()
        self.start_screen_sprites = pygame.sprite.Group()
        self.perspective_sprites = pygame.sprite.Group()
        self.mouse_focused_sprites = pygame.sprite.Group()
        self.button_sprites = pygame.sprite.Group()
        self.debug_sprites = pygame.sprite.Group()
        self.projectile_sprites = pygame.sprite.Group()
        self.weapon_sprites = pygame.sprite.Group()
        self.player_sprites = pygame.sprite.Group()

        self.loading_screen = LoadingScreen(parent.screen)

        self.cursor = CursorSprite(self.mouse_focused_sprites)

        self.debug_screen = parent.debug_screen
        self.settings = parent.settings_screen
        self.levels = parent.levels

        self.game_field = GameField(self.loading_screen, "1.txt", (0, 0))
        self.player = Player(self, self.player_sprites, (300, 300), 4, 2)

        self.weapon = Weapon().Triangle_Blaster(self, self.weapon_sprites, self.projectile_sprites)

    def loop(self):
        vec = pygame.math.Vector2
        last_tick = time.time()
        tick_time = 0

        move_map = {pygame.K_w: (0, -1),
                    pygame.K_s: (0, 1),
                    pygame.K_a: (-1, 0),
                    pygame.K_d: (1, 0)}
        shooting = False

        while True:
            for event in pygame.event.get():
                if event.type == pygame.MOUSEMOTION:
                    self.cursor.rect = event.pos
                    self.weapon.angle = 90 - pygame.math.Vector2(self.player.rect.center[0] - event.pos[0],
                                                            self.player.rect.center[1] - event.pos[1]).as_polar()[1]

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        shooting = True

                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_SPACE:
                        shooting = False

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.projectile_sprites.update(None, event.pos)

            pressed = pygame.key.get_pressed()
            move = [move_map[key] for key in move_map if pressed[key]]
            move_vector = vec(0, 0)
            for i in move:
                move_vector += vec(*i)
            if move_vector != vec(0, 0):
                self.player.move_vector = move_vector.normalize()
                self.player.tick_time = tick_time

            if shooting:
                self.weapon.shoot()

            self.projectile_sprites.update(tick_time, None)
            self.weapon_sprites.update()
            self.player.update()
            particles.update(tick_time)

            self.screen.fill((212, 123, 88))
            self.game_field.draw(self.screen)
            self.projectile_sprites.draw(screen)
            self.weapon_sprites.draw(screen)
            self.player_sprites.draw(screen)
            particles.draw(screen)

            if pygame.mouse.get_focused():
                self.mouse_focused_sprites.draw(screen)

            if DEBUG_SCREEN:
                self.debug_screen.update_draw()

            if clock.get_fps() != 0:
                self.tps = clock.get_fps()

            pygame.display.flip()
            clock.tick()
            tick_time = time.time() - last_tick
            last_tick = time.time()
            #print(self.game_field.position)


class SettingsScreen():
    def __init__(self, parent):
        self.parent = parent
        print("settings init")

    def loop(self):
        print("settings screen")


class LevelsScreen():
    def __init__(self, parent):
        self.parent = parent
        print("levels init")

    def loop(self):
        print("levels screen")


class Player(pygame.sprite.Sprite):
    def __init__(self, parent, group, field_pos, velocity, jump_velocity):
        self.parent = parent
        super().__init__(group)

        self.velocity = velocity * self.parent.game_field.unit_size
        self.jump_velocity = jump_velocity
        self.move_vector = pygame.math.Vector2(0, 0)
        self.reset_jump_vel = False

        image = pygame.image.load(TEXTURE_PATH + "player.png")
        size = min(SIZE) // FOV * 0.7
        image = pygame.transform.smoothscale(image, (int(size), int(size))).convert_alpha()
        self.image = image

        self.rect = self.image.get_rect()
        self.rect.x, self.rect.y = field_pos
        self.move_counter_x, self.move_counter_y = 0, 0
        self.x = self.parent.game_field.x + self.rect.x
        self.y = self.parent.game_field.y + self.rect.y
        self.position = self.x, self.y

        rect_size = PLAYER_ONSCREEN_MOVEMENT_RECT
        border_pos = (WIDTH // rect_size, HEIGHT // rect_size)
        border_size = (WIDTH // rect_size * (rect_size - 2), HEIGHT // rect_size * (rect_size - 2))
        self.onscreen_move_border = pygame.Rect(border_pos, border_size)

        self.tick_time = 0

    def update(self, *args):
        vec = pygame.math.Vector2

        self.move(self.move_vector, self.tick_time)
        self.move_vector = vec(0, 0)


    def move(self, pos, tick_time=None):
        if pos == (0, 0):
            return
        vec = pygame.math.Vector2

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

        #check block collision
        block_pos = b_x, b_y = self.parent.game_field.get_block_pos(self.position)
        block_rect = self.parent.game_field.get_block_rect(self.position)

        get_name = self.parent.game_field.get_block_at_pos
        block_name = get_name(block_pos)
        print(block_rect, self.rect, block_pos, self.parent.game_field.is_air((b_x, b_y - 1)))

        if self.rect.top <= block_rect.top and not self.parent.game_field.is_air((b_x, b_y - 1)):
            move_y += block_rect.top - self.rect.top
            print("detected", move_y)
        #elif self.rect.bottom >= block_rect.bottom and not self.parent.game_field.is_air((b_x, b_y + 1)):
        #    move_y += block_rect.bottom - self.rect.bottom


        self_move_vec = vec(move_x, move_y)
        field_move_vec = vec(0, 0)

        #field
        if self.rect.top < self.onscreen_move_border.top:
            field_move_vec += vec(0, self.rect.top - self.onscreen_move_border.top)
        elif self.rect.bottom > self.onscreen_move_border.bottom:
            field_move_vec += vec(0, self.rect.bottom - self.onscreen_move_border.bottom)

        if self.rect.left < self.onscreen_move_border.left:
            field_move_vec += vec(self.rect.left - self.onscreen_move_border.left, 0)
        elif self.rect.right > self.onscreen_move_border.right:
            field_move_vec += vec(self.rect.right - self.onscreen_move_border.right, 0)

        self_move_vec -= field_move_vec
        print(self_move_vec, field_move_vec)

        self.rect.x += self_move_vec.x
        self.rect.y += self_move_vec.y
        self.parent.game_field.move(-field_move_vec)

        self.x = self.rect.x - self.parent.game_field.x
        self.y = self.rect.y - self.parent.game_field.y
        self.position = self.x, self.y



class Weapon():

    class Triangle_Blaster(pygame.sprite.Sprite):
        def __init__(self, parent, group, projectile_group):
            super().__init__(group)
            self.parent = parent
            self.projectile_group = projectile_group

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

            self.angle = 90

            self.image = pygame.transform.rotate(images[0], self.angle)
            self.rect = self.image.get_rect()
            self.rect.center = WIDTH // 2, HEIGHT // 2
            self.next_image_swap = time.time()

            self.state = 2 # 0 - unloaded, 1 - loading, 2 - loaded
            self.reloading_time = 2
            self.damage = 20
            self.penetration = 5 # how many entities it can fly through
            self.projectile_velocity = 4 # tiles/sec
            self.projectile_size = (min(SIZE) // FOV) // 3
            self.projectile_image = "triangle_blaster_projectile.png"
            self.projectile_max_distance = 10 # tiles

            self.next_shot_time = time.time() + self.reloading_time

            self.state_changed = True

        def set_state(self, state):
            self.state = state

        def shoot(self):
            if self.state == 2 and self.next_shot_time <= time.time():
                for i in range(-20, 40, 20):
                    Projectile(self.parent,
                               self.projectile_group,
                               self.rect.center,
                               self.projectile_image,
                               self.damage,
                               self.penetration,
                               self.projectile_velocity / (abs(i / 100) + 0.8),
                               self.angle + i,
                               self.projectile_size,
                               self.projectile_max_distance)
                self.state = 0
                self.index = 0
                self.next_shot_time = time.time() + self.reloading_time
                print("shoot")

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
                    self.index = 9
                else:
                    self.next_image_swap += self.reloading_time / len(self.i_loading)

            elif self.state == 2:
                if self.state_changed:
                    print("image = loaded")

            self.image = pygame.transform.rotate(self.images[self.index], self.angle)
            self.rect = self.image.get_rect()
            self.rect.center = self.parent.player.rect.center

            if prev_state != self.state:
                self.state_changed = True
            else:
                self.state_changed = False


class Mob(pygame.sprite.Sprite):
    def __init__(self, parent, group, images, damage, health, pos, speed, hostile=True):

        super().__init__(group)

        self.parent = parent

        self.images = images

        self.damage = damage
        self.health = health
        self.speed = speed

        self.rect.center = pos

class Projectile(pygame.sprite.Sprite):
    def __init__(self, parent, group, pos, image, damage, penetration, velocity, angle, size, max_distance):

        super().__init__(group)

        self.parent = parent

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

        self.damage = damage
        self.penetration = penetration
        self.velocity = velocity
        self.size = size
        self.angle = angle

        self.max_distance = max_distance * self.vector_scale
        self.current_distance = 0

        self.move((min(SIZE) // FOV) // 2)

        self.init_time = time.time()

        self.aim_limit = 1
        self.last_field_pos = self.parent.game_field.position

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

    def update(self, *args):
        if args[0] is not None:
            self.move(self.vector * self.velocity, True, args[0])

        if args[1] is not None:
            self.aim_at(args[1], 2)

        if self.current_distance > self.max_distance:
            self.kill()
            for _ in range(25):
                Particle().RocketThrust(self.parent, 10, self.rect.center, 5, 3, 0.15, 0.1)

        self.rect.x += self.parent.game_field.position[0] - self.last_field_pos[0]
        self.rect.y += self.parent.game_field.position[1] - self.last_field_pos[1]

        img = pygame.Surface((9, 9))
        pygame.draw.circle(img, (255, 0, 0), (5, 5), 4)

        self.last_field_pos = self.parent.game_field.position
        self.rotate(0)


class Particle():
    class RocketThrust(pygame.sprite.Sprite):
        images = pygame.image.load(TEXTURE_PATH + "explosion.png")
        images = crop_image(images, 10, 1)

        def __init__(self, parent, size, pos, speed, speed_offset, time_alive, time_alive_offset):
            super().__init__(particles)
            vec = pygame.math.Vector2

            self.parent = parent

            image = self.images[random.randint(1, len(self.images)) - 1]
            size = int(size * WIDTH / 900)
            print(size)
            image = pygame.transform.scale(image, (size, size))
            self.image = image

            self.rect = self.image.get_rect()
            self.rect.center = pos

            speed = speed + speed_offset * (random.random() - 0.5)

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


class GameField(pygame.sprite.Group):
    def __init__(self, loading_screen, level, pos=(0, 0)):
        super().__init__()
        self.all_sprites = pygame.sprite.Group()

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

        claster_map_size = x_cl, y_cl = x // CLASTER_SIZE + (1 if x % CLASTER_SIZE != 0 else 0),\
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


        print(x_cl, y_cl)
        print(claster_map)
        print(*txt_map, size, sep="\n")

        self.claster_map = claster_map
        self.sprite_map = sprite_map

        for row in sprite_map:
            for item in row:
                print(item.rect)

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

    def get_block_pos(self, pos):
        return pos[0] // self.unit_size, pos[1] // self.unit_size

    def get_block_at_pos(self, pos):
        if pos[0] < 0 or pos[1] < 0:
            return None
        try:
            unit_name = self.txt_map[pos[1]][pos[0]]
            return unit_name
        except:
            return None

    def is_air(self, pos):
        tmp = self.get_block_at_pos(pos)
        if tmp == "." or tmp is None:
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
        #self.rect = self.image.get_rect()

        self.rect = (pos_x - zoom / 2, pos_y - zoom * HEIGHT / WIDTH / 2)
        self.x = pos_x - zoom / 2
        self.y = pos_y - zoom / 2
        self.zoom = (WIDTH + zoom, HEIGHT + zoom * HEIGHT / WIDTH)

    def move_from_default_pos(self, x, y, distance):
        self.rect = (self.x + x / distance, self.y + y / distance + 40) #TODO fix getting out of border issue


class CursorSprite(pygame.sprite.Sprite):
    def __init__(self, group = None):
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