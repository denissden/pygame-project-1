import os

SIZE_FROM_RATIO = False
RATIO = 16 / 9

SIZE = WIDTH, HEIGHT = 800, 600
if SIZE_FROM_RATIO:
    SIZE = WIDTH, HEIGHT = int(HEIGHT * RATIO), HEIGHT

FPS = 144
TPS = 64
TPS_EQUALS_FPS = False
FULLSCREEN = False
ADVANCED_GRAPHICS = False

DEBUG_SCREEN = True
TEXTURE_PATH = 'data/'
LEVELS = ["1.txt"]
LEVEL_PATH = 'data/levels/'
CLASTER_SIZE = 4

FOV = 15
PLAYER_ONSCREEN_MOVEMENT_RECT = 8 # 3 or more
PENETRATION_DELAY = 0.1
PLAYER_HEALTH = 100
MOB_LIFETIME = 10

screen_rect = (0, 0, WIDTH, HEIGHT)