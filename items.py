import os
import sys
import time
import pygame
import random

#hearts
half_heart = {"image":"half_heart.png",
              "health":5}
heart = {"image":"heart.png",
         "health":10}
broken_heart = {"image":"broken_heart.png",
                "health":-10}

#guns
triangle_blaster = {"image":"triangle_blaster.png",
                    "damage":25,
                    "reload":1,}

