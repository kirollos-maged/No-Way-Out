import pygame
import sys
import json
import random
import os
import math
import array
from collections import deque

pygame.init()

WIDTH, HEIGHT = 960, 720
ROWS, COLS = 12, 16
TILE_SIZE = 40
FPS = 60

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("No Way Out")
clock = pygame.time.Clock()

font = pygame.font.SysFont(None, 24)
title_font = pygame.font.SysFont(None, 80)
menu_font = pygame.font.SysFont(None, 48)
go_font = pygame.font.SysFont(None, 72)
small_font = pygame.font.SysFont(None, 20)
tiny_font = pygame.font.SysFont(None, 16)
card_font = pygame.font.SysFont(None, 34)

THEME = {
    "bg_top": (10, 14, 25),
    "bg_bottom": (19, 24, 39),
    "panel": (19, 27, 43),
    "panel_2": (29, 38, 58),
    "accent": (94, 201, 180),
    "accent_2": (96, 176, 255),
    "success": (96, 226, 154),
    "warning": (239, 184, 82),
    "danger": (235, 84, 98),
    "muted": (156, 167, 190),
    "text": (238, 242, 249),
    "text_dark": (13, 18, 27),
    "line": (66, 80, 110),
}

WALL = "wall"
PATH = "path"
MUD = "mud"
ICE = "ice"
DOOR = "door"

SPEED_BOOST = "speed"
FREEZE_TRAP = "freeze"
DECOY = "decoy"

COLORS = {
    WALL: (35, 40, 56),
    PATH: (226, 231, 242),
    MUD: (123, 83, 51),
    ICE: (142, 221, 242),
    DOOR: (245, 151, 63)
}

ITEM_COLORS = {
    SPEED_BOOST: (239, 184, 82),
    FREEZE_TRAP: (96, 176, 255),
    DECOY: (164, 119, 255)
}

COSTS = {WALL: float('inf'), PATH: 1, MUD: 3, ICE: 0.5, DOOR: 1}

LEVEL_CONFIGS = [
    # 1-3: 1 Easy
    {"zombies": 1, "zombie_type": "greedy", "walls": 15, "mud": 5, "ice": 8, "doors": 10, "z_speed": 600, "items": 3},
    {"zombies": 1, "zombie_type": "greedy", "walls": 18, "mud": 6, "ice": 7, "doors": 10, "z_speed": 600, "items": 3},
    {"zombies": 1, "zombie_type": "greedy", "walls": 20, "mud": 6, "ice": 6, "doors": 12, "z_speed": 600, "items": 3},
    # 4-5: 2 Easy
    {"zombies": 2, "zombie_type": "greedy", "walls": 22, "mud": 7, "ice": 6, "doors": 12, "z_speed": 600, "items": 3},
    {"zombies": 2, "zombie_type": "greedy", "walls": 24, "mud": 8, "ice": 5, "doors": 13, "z_speed": 600, "items": 3},
    # 6-7: 1 Medium
    {"zombies": 1, "zombie_type": "bfs", "walls": 26, "mud": 9, "ice": 5, "doors": 13, "z_speed": 400, "items": 2},
    {"zombies": 1, "zombie_type": "bfs", "walls": 28, "mud": 9, "ice": 4, "doors": 14, "z_speed": 400, "items": 2},
    # 8-10: 2 Medium
    {"zombies": 2, "zombie_type": "bfs", "walls": 30, "mud": 10, "ice": 4, "doors": 14, "z_speed": 400, "items": 2},
    {"zombies": 2, "zombie_type": "bfs", "walls": 32, "mud": 10, "ice": 3, "doors": 15, "z_speed": 400, "items": 2},
    {"zombies": 2, "zombie_type": "bfs", "walls": 34, "mud": 11, "ice": 3, "doors": 15, "z_speed": 400, "items": 2},
    # 11-13: 2 Hard
    {"zombies": 2, "zombie_type": "astar", "walls": 36, "mud": 12, "ice": 2, "doors": 16, "z_speed": 250, "items": 2},
    {"zombies": 2, "zombie_type": "astar", "walls": 38, "mud": 12, "ice": 2, "doors": 16, "z_speed": 250, "items": 2},
    {"zombies": 2, "zombie_type": "astar", "walls": 40, "mud": 13, "ice": 1, "doors": 17, "z_speed": 250, "items": 2},
    # 14-15: 3 Hard
    {"zombies": 3, "zombie_type": "astar", "walls": 42, "mud": 13, "ice": 1, "doors": 17, "z_speed": 250, "items": 1},
    {"zombies": 3, "zombie_type": "astar", "walls": 44, "mud": 14, "ice": 0, "doors": 18, "z_speed": 250, "items": 1},
]

class Node:
    def __init__(self, position, parent=None):
        self.position = position
        self.parent = parent
        self.g = 0
        self.h = 0
        self.f = 0
    def __eq__(self, other): return self.position == other.position
    def __lt__(self, other): return self.f < other.f

class Zombie:
    def __init__(self, pos, z_type, speed_ms):
        self.pos = list(pos)
        self.z_type = z_type
        self.speed_ms = speed_ms
        self.last_move = pygame.time.get_ticks()
        self.path = []
        if z_type == "greedy":
            self.color = (255, 255, 0) # Yellow Easy
        elif z_type == "bfs":
            self.color = (0, 255, 0) # Green Medium
        else:
            self.color = (0, 0, 255) # Blue Hard

class SoundManager:
    """Small built-in sound system.

    The game still runs silently if the computer has no audio device.
    Sounds are generated at runtime, so the project needs no external assets.
    """
    def __init__(self):
        self.enabled = False
        self.sounds = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
            self.enabled = True
            self.sounds = {
                "click": self._tone(520, 45, 0.18),
                "step": self._tone(210, 35, 0.10),
                "wall": self._tone(120, 80, 0.16),
                "item": self._tone(760, 90, 0.22),
                "power": self._tone(980, 120, 0.20),
                "win": self._tone(880, 180, 0.24),
                "lose": self._tone(95, 240, 0.22),
            }
        except pygame.error:
            self.enabled = False

    def _tone(self, frequency, duration_ms, volume):
        sample_rate = 44100
        sample_count = int(sample_rate * duration_ms / 1000)
        amplitude = int(32767 * volume)
        buf = array.array("h")
        for i in range(sample_count):
            fade = 1 - (i / max(1, sample_count))
            sample = int(amplitude * fade * math.sin(2 * math.pi * frequency * i / sample_rate))
            buf.append(sample)
        return pygame.mixer.Sound(buffer=buf.tobytes())

    def play(self, name):
        if self.enabled and name in self.sounds:
            try:
                self.sounds[name].play()
            except pygame.error:
                pass

class Game:
    def __init__(self):
        self.state = "MAIN_MENU"
        self.load_progress()
        self.sound = SoundManager()
        self.path_cache = {}
        self.path_cache_revision = 0
        self.pending_path_recalc = False
        self.last_path_goal = None
        
        self.current_level_idx = 0
        self.player_moving = False
        self.play_mode = "campaign"
        self.editor_message = "Validate your map before playing."
        self.base_move_duration = 180
        self.grid_x_offset = (WIDTH - COLS * TILE_SIZE) // 2
        self.grid_y_offset = (HEIGHT - ROWS * TILE_SIZE) // 2
        
        # GUI-only cosmetic player skins. These do not change gameplay stats.
        self.selected_skin = "zex"
        self.pause_return_state = "GAME"
        self.player_skins = {
            "zex": {
                "name": "zex", "gender": "female", "role": "Neon Runner", "style": "zex",
                "accent": (234, 102, 154), "hair": (43, 32, 50), "shirt": (150, 70, 118), "skin": (232, 184, 145)
            },
            "ninja": {
                "name": "ninja", "gender": "male", "role": "Silent Shadow", "style": "ninja",
                "accent": (94, 201, 180), "hair": (18, 22, 30), "shirt": (29, 35, 47), "skin": (214, 166, 128)
            },
            "0xbp7": {
                "name": "0xBP7", "gender": "male", "role": "Cyber Operator", "style": "cyber",
                "accent": (96, 176, 255), "hair": (22, 31, 45), "shirt": (42, 76, 112), "skin": (222, 176, 136)
            },
            "rook": {
                "name": "Romman", "gender": "male", "role": "Street Defender", "style": "rook",
                "accent": (239, 184, 82), "hair": (40, 32, 28), "shirt": (86, 78, 58), "skin": (226, 176, 132)
            },
            "kade": {
                "name": "Kade", "gender": "male", "role": "Maze Scout", "style": "kade",
                "accent": (96, 226, 154), "hair": (42, 47, 39), "shirt": (57, 107, 78), "skin": (224, 173, 132)
            },
        }
        self.skin_order = ["zex", "ninja", "0xbp7", "rook", "kade"]
        
        # Editor specific
        self.editor_grid = [[PATH for _ in range(COLS)] for _ in range(ROWS)]
        self.editor_player_start = [1, 1]
        self.editor_win_point = [ROWS-2, COLS-2]
        self.editor_zombie_spawns = []
        self.editor_current_tool = WALL
        self.editor_zombie_diff = "greedy"
        self.editor_valid = False

    def load_progress(self):
        self.progress_file = "progress.json"
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    data = json.load(f)
                    self.unlocked_levels = data.get("unlocked_levels", 1)
            except:
                self.unlocked_levels = 1
        else:
            self.unlocked_levels = 1

    def save_progress(self):
        with open(self.progress_file, 'w') as f:
            json.dump({"unlocked_levels": self.unlocked_levels}, f)

    def get_reachable_tiles(self, start, grid=None):
        if grid is None: grid = self.grid
        queue = deque([start])
        visited = set([start])
        
        while queue:
            curr = queue.popleft()
            for dr, dc in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                nr, nc = curr[0] + dr, curr[1] + dc
                if 0 <= nr < ROWS and 0 <= nc < COLS:
                    if grid[nr][nc] != WALL and (nr, nc) not in visited:
                        visited.add((nr, nc))
                        queue.append((nr, nc))
        return visited

    def a_star(self, start, end, grid=None):
        if grid is None: grid = self.grid
        open_list, closed_list = [], []
        start_node = Node(start)
        end_node = Node(end)
        open_list.append(start_node)

        while open_list:
            open_list.sort()
            current_node = open_list.pop(0)
            closed_list.append(current_node)

            if current_node == end_node:
                path = []
                current = current_node
                while current is not None:
                    path.append(current.position)
                    current = current.parent
                return path[::-1]

            for new_pos in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                nr, nc = current_node.position[0] + new_pos[0], current_node.position[1] + new_pos[1]
                if 0 <= nr < ROWS and 0 <= nc < COLS and grid[nr][nc] != WALL:
                    new_node = Node((nr, nc), current_node)
                    
                    if any(child == new_node for child in closed_list):
                        continue

                    move_cost = COSTS.get(grid[nr][nc], 1)
                    new_node.g = current_node.g + move_cost
                    new_node.h = abs(nr - end_node.position[0]) + abs(nc - end_node.position[1])
                    new_node.f = new_node.g + new_node.h

                    in_open = False
                    for i, open_node in enumerate(open_list):
                        if new_node == open_node:
                            in_open = True
                            if new_node.g < open_node.g:
                                open_list[i] = new_node
                            break
                    if not in_open:
                        open_list.append(new_node)
        return []

    def bfs(self, start, end, grid=None):
        if grid is None: grid = self.grid
        queue = deque([[start]])
        visited = set([start])

        while queue:
            path = queue.popleft()
            current = path[-1]

            if current == end: return path

            for dr, dc in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                nr, nc = current[0] + dr, current[1] + dc
                if 0 <= nr < ROWS and 0 <= nc < COLS and grid[nr][nc] != WALL:
                    if (nr, nc) not in visited:
                        visited.add((nr, nc))
                        queue.append(path + [(nr, nc)])
        return []

    def greedy_search(self, start, end, grid=None):
        if grid is None: grid = self.grid
        open_list, closed_list = [], []
        start_node = Node(start)
        end_node = Node(end)
        open_list.append(start_node)

        while open_list:
            open_list.sort() # sort by f which is just h here
            current_node = open_list.pop(0)
            closed_list.append(current_node)

            if current_node == end_node:
                path = []
                current = current_node
                while current is not None:
                    path.append(current.position)
                    current = current.parent
                return path[::-1]

            for new_pos in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                nr, nc = current_node.position[0] + new_pos[0], current_node.position[1] + new_pos[1]
                if 0 <= nr < ROWS and 0 <= nc < COLS and grid[nr][nc] != WALL:
                    new_node = Node((nr, nc), current_node)
                    
                    if any(child == new_node for child in closed_list):
                        continue

                    new_node.g = 0
                    new_node.h = abs(nr - end_node.position[0]) + abs(nc - end_node.position[1])
                    new_node.f = new_node.h

                    if not any(child == new_node for child in open_list):
                        open_list.append(new_node)
        return []

    def start_level(self, level_idx):
        self.play_mode = "campaign"
        self.current_level_idx = level_idx
        self.config = LEVEL_CONFIGS[level_idx]
        self.player = [1, 1]
        self.doors = []
        self.last_toggle = pygame.time.get_ticks()
        
        self.generate_campaign_map()
        self.setup_game_state()
        self.spawn_zombies()
        self.invalidate_path_cache()
        self.recalculate_paths()
        self.state = "GAME"

    def setup_game_state(self):
        self.inventory = {SPEED_BOOST: 0, FREEZE_TRAP: 0, DECOY: 0}
        self.spawn_items()
        self.player_pos = [self.player[1] * TILE_SIZE + TILE_SIZE//2, self.player[0] * TILE_SIZE + TILE_SIZE//2]
        self.player_start = list(self.player)
        self.player_target = None
        self.player_moving = False
        self.player_move_start = 0
        self.player_speed_multiplier = 1.0
        self.speed_boost_until = 0
        self.freeze_until = 0
        self.decoy_position = None
        self.decoy_until = 0
        self.score = 0
        self.game_won = False

    def generate_campaign_map(self):
        while True:
            self.grid = [[PATH for _ in range(COLS)] for _ in range(ROWS)]
            self.doors.clear()
            
            for r in range(ROWS):
                for c in range(COLS):
                    if r == 0 or c == 0 or r == ROWS-1 or c == COLS-1:
                        self.grid[r][c] = WALL
            
            for _ in range(self.config["walls"]):
                r, c = random.randint(1, ROWS-2), random.randint(1, COLS-2)
                if [r, c] not in [[1, 1], [ROWS-2, COLS-2], [ROWS-2, 1], [1, COLS-2]]:
                    self.grid[r][c] = WALL

            # Keep small safe pockets around the player and zombie spawn corners.
            # This reduces unfair instant-death maps without making later levels easy.
            safe_centers = [(1, 1), (ROWS-2, COLS-2), (ROWS-2, 1), (1, COLS-2)]
            for sr, sc in safe_centers:
                for rr in range(max(1, sr-1), min(ROWS-1, sr+2)):
                    for cc in range(max(1, sc-1), min(COLS-1, sc+2)):
                        if abs(rr - sr) + abs(cc - sc) <= 1:
                            self.grid[rr][cc] = PATH

            reachable = self.get_reachable_tiles((1, 1))
            if (ROWS-2, COLS-2) in reachable and (ROWS-2, 1) in reachable and (1, COLS-2) in reachable:
                if len(reachable) > 85:
                    far_tiles = []
                    for pos in reachable:
                        distance = abs(pos[0]-1) + abs(pos[1]-1)
                        route = self.bfs((1, 1), pos)
                        if distance >= 15 and len(route) >= 20:
                            far_tiles.append(pos)
                    if far_tiles:
                        self.win_point = list(random.choice(far_tiles))
                        break

        path_tiles = [(r, c) for r in range(1, ROWS-1) for c in range(1, COLS-1) if self.grid[r][c] == PATH]
        random.shuffle(path_tiles)

        mud_c, ice_c, door_c = self.config["mud"], self.config["ice"], self.config["doors"]
        
        for r, c in path_tiles:
            if [r, c] in [[1, 1], self.win_point, [ROWS-2, 1], [1, COLS-2]]: continue
                
            if mud_c > 0:
                self.grid[r][c] = MUD; mud_c -= 1
            elif ice_c > 0:
                self.grid[r][c] = ICE; ice_c -= 1
            elif door_c > 0:
                self.grid[r][c] = DOOR
                self.doors.append((r, c))
                door_c -= 1
            else: break

    def spawn_items(self):
        self.items = []
        free_tiles = [
            (r, c) for r in range(1, ROWS-1) for c in range(1, COLS-1)
            if self.grid[r][c] in (PATH, MUD, ICE)
            and [r, c] not in ([1, 1], self.win_point)
            and abs(r - 1) + abs(c - 1) >= 3
            and abs(r - self.win_point[0]) + abs(c - self.win_point[1]) >= 2
        ]
        random.shuffle(free_tiles)
        item_types = [SPEED_BOOST, FREEZE_TRAP, DECOY]
        
        for i in range(self.config.get("items", 3)):
            if free_tiles:
                self.items.append({'type': item_types[i % 3], 'pos': free_tiles.pop()})

    def spawn_zombies(self):
        self.zombies = []
        spawns = [[ROWS-2, COLS-2], [ROWS-2, 1], [1, COLS-2]]
        for i in range(self.config["zombies"]):
            if i < len(spawns):
                z = Zombie(spawns[i], self.config["zombie_type"], self.config["z_speed"])
                self.zombies.append(z)

    def start_editor_level(self):
        self.play_mode = "editor"
        self.grid = [row[:] for row in self.editor_grid]
        self.player = list(self.editor_player_start)
        self.win_point = list(self.editor_win_point)
        self.doors = [(r, c) for r in range(ROWS) for c in range(COLS) if self.grid[r][c] == DOOR]
        self.last_toggle = pygame.time.get_ticks()

        # The editor needs config before setup_game_state(), because setup_game_state() spawns items.
        self.config = {"items": 3}
        self.setup_game_state()

        self.zombies = []
        speed = 250 if self.editor_zombie_diff == "astar" else (400 if self.editor_zombie_diff == "bfs" else 600)
        for pos in self.editor_zombie_spawns:
            self.zombies.append(Zombie(pos, self.editor_zombie_diff, speed))

        self.invalidate_path_cache()
        self.recalculate_paths()
        self.state = "EDITOR_PLAY"

    def get_current_goal(self):
        if self.decoy_position and pygame.time.get_ticks() < self.decoy_until:
            return tuple(self.decoy_position)
        return tuple(self.player)

    def invalidate_path_cache(self):
        # Door toggles and new maps change walkability/costs, so cached routes must be dropped.
        self.path_cache.clear()
        self.path_cache_revision += 1

    def request_path_recalculation(self, clear_cache=False):
        if clear_cache:
            self.invalidate_path_cache()
        self.pending_path_recalc = True

    def get_cached_path(self, zombie, goal):
        start = tuple(zombie.pos)
        key = (zombie.z_type, start, goal, self.path_cache_revision)
        cached = self.path_cache.get(key)
        if cached is not None:
            return cached[:]
        if zombie.z_type == "astar":
            path = self.a_star(start, goal)
        elif zombie.z_type == "bfs":
            path = self.bfs(start, goal)
        else:
            path = self.greedy_search(start, goal)
        self.path_cache[key] = path[:]
        return path

    def recalculate_paths(self):
        goal = self.get_current_goal()
        for z in self.zombies:
            z.path = self.get_cached_path(z, goal)
        self.pending_path_recalc = False
        self.last_path_goal = goal

    def can_move_to(self, r, c):
        if 0 <= r < ROWS and 0 <= c < COLS:
            return self.grid[r][c] != WALL
        return False

    def update_timers(self):
        now = pygame.time.get_ticks()
        if self.speed_boost_until and now >= self.speed_boost_until:
            self.speed_boost_until = 0
            self.player_speed_multiplier = 1.0

        if self.freeze_until and now >= self.freeze_until:
            self.freeze_until = 0
            self.request_path_recalculation()

        if self.decoy_until and now >= self.decoy_until:
            self.decoy_until = 0
            self.decoy_position = None
            self.request_path_recalculation()

    def use_item(self, item_type):
        if self.inventory.get(item_type, 0) > 0:
            self.inventory[item_type] -= 1
            self.sound.play("power")
            if item_type == SPEED_BOOST:
                self.speed_boost_until = pygame.time.get_ticks() + 5000
                self.player_speed_multiplier = 2.0
            elif item_type == FREEZE_TRAP:
                self.freeze_until = pygame.time.get_ticks() + 4000
            elif item_type == DECOY:
                self.decoy_position = tuple(self.player) # drop at feet
                self.decoy_until = pygame.time.get_ticks() + 5000
                self.request_path_recalculation()

    def collect_item(self, pos):
        for item in self.items:
            if item['pos'] == pos:
                self.inventory[item['type']] += 1
                self.score += 10
                self.sound.play("item")
                self.items.remove(item)
                break

    def move_player(self, dx, dy):
        if self.player_moving: return
        nr, nc = self.player[0] + dy, self.player[1] + dx
        if self.can_move_to(nr, nc):
            self.sound.play("step")
            self.player_target = [nr, nc]
            self.player_start = list(self.player)
            self.player_move_start = pygame.time.get_ticks()
            self.player_moving = True
            
            # Apply tile speed effects (Mud slows down, Ice speeds up)
            tile_type = self.grid[nr][nc]
            self.current_tile_duration = self.base_move_duration
            if tile_type == MUD: self.current_tile_duration *= 2
            elif tile_type == ICE: self.current_tile_duration *= 0.5
            
            if not self.freeze_until:
                self.request_path_recalculation()
        else:
            self.sound.play("wall")

    def update_player_movement(self):
        if not self.player_moving: return
        
        now = pygame.time.get_ticks()
        duration = max(50, int(self.current_tile_duration / self.player_speed_multiplier))
        elapsed = now - self.player_move_start
        progress = min(1.0, elapsed / duration)

        spx = [self.player_start[1] * TILE_SIZE + TILE_SIZE//2, self.player_start[0] * TILE_SIZE + TILE_SIZE//2]
        tpx = [self.player_target[1] * TILE_SIZE + TILE_SIZE//2, self.player_target[0] * TILE_SIZE + TILE_SIZE//2]
        
        self.player_pos = [spx[0] + (tpx[0]-spx[0])*progress, spx[1] + (tpx[1]-spx[1])*progress]

        if progress >= 1.0:
            self.player_moving = False
            self.player = list(self.player_target)
            self.player_target = None
            self.player_pos = tpx
            self.collect_item(tuple(self.player))
            if not self.freeze_until:
                self.request_path_recalculation()

            if self.player == self.win_point:
                self.game_won = True
                self.sound.play("win")
                if self.state == "GAME" and self.current_level_idx + 1 == self.unlocked_levels:
                    self.unlocked_levels = min(15, self.unlocked_levels + 1)
                    self.save_progress()
                self.state = "WIN_SCREEN"
                return

            if any(z.pos == self.player for z in self.zombies):
                self.sound.play("lose")
                self.state = "LOSE_SCREEN"
                return

    def update_zombies(self):
        if self.freeze_until: return
        now = pygame.time.get_ticks()
        if self.pending_path_recalc or self.get_current_goal() != self.last_path_goal:
            self.recalculate_paths()
        
        for z in self.zombies:
            if now - z.last_move > z.speed_ms:
                z.last_move = now
                if z.path and len(z.path) > 1:
                    z.pos = list(z.path[1])
                    z.path = z.path[1:]
                
                if z.pos == self.player:
                    self.sound.play("lose")
                    self.state = "LOSE_SCREEN"
                    return

    def toggle_doors(self):
        now = pygame.time.get_ticks()
        if now - self.last_toggle > 800:
            self.last_toggle = now
            if self.doors:
                r, c = random.choice(self.doors)
                self.grid[r][c] = WALL if self.grid[r][c] == DOOR else DOOR
                if not self.freeze_until:
                    self.request_path_recalculation(clear_cache=True)


    def draw_gradient_background(self, top=None, bottom=None):
        top = top or (10, 14, 26)
        bottom = bottom or (27, 22, 42)
        for y in range(HEIGHT):
            t = y / HEIGHT
            color = tuple(int(top[i] * (1 - t) + bottom[i] * t) for i in range(3))
            pygame.draw.line(screen, color, (0, y), (WIDTH, y))
        self.draw_background_decor()

    def draw_background_decor(self):
        now = pygame.time.get_ticks() / 1000
        fog = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        for i in range(9):
            x = int((i * 143 + now * 18) % (WIDTH + 140) - 70)
            y = 80 + (i * 71) % 560
            pygame.draw.circle(fog, (100, 150, 170, 18), (x, y), 70 + (i % 3) * 18)
        screen.blit(fog, (0, 0))
        for x in range(-40, WIDTH, 80):
            pygame.draw.line(screen, (255, 255, 255, 7), (x, 0), (x + 240, HEIGHT), 1)
        for y in range(40, HEIGHT, 90):
            pygame.draw.line(screen, (70, 95, 140), (0, y), (WIDTH, y), 1)

    def draw_text(self, text, font_obj, color, center=None, topleft=None, midleft=None, shadow=False):
        # Text shadows were intentionally removed for a cleaner GUI.
        # The shadow parameter stays for compatibility with existing draw calls.
        surf = font_obj.render(text, True, color)
        rect = surf.get_rect()
        if center:
            rect.center = center
        elif topleft:
            rect.topleft = topleft
        elif midleft:
            rect.midleft = midleft
        screen.blit(surf, rect)
        return rect

    def draw_panel(self, rect, color=None, border_color=None, radius=18, shadow=True, glow=False):
        color = color or (22, 27, 44)
        border_color = border_color or (77, 93, 128)
        if shadow:
            pygame.draw.rect(screen, (2, 4, 11), rect.move(0, 8), border_radius=radius)
        if glow:
            glow_surf = pygame.Surface((rect.w + 26, rect.h + 26), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, (*border_color, 35), glow_surf.get_rect(), border_radius=radius + 14)
            screen.blit(glow_surf, (rect.x - 13, rect.y - 13))
        pygame.draw.rect(screen, color, rect, border_radius=radius)
        pygame.draw.rect(screen, border_color, rect, 2, border_radius=radius)
        pygame.draw.line(screen, (255, 255, 255, 28), (rect.x + radius, rect.y + 3), (rect.right - radius, rect.y + 3), 1)

    def draw_button(self, rect, text, color, hover_color=None, font_obj=None, text_color=None, disabled=False):
        font_obj = font_obj or font
        text_color = text_color or THEME["text"]
        mouse = pygame.mouse.get_pos()
        is_hovered = rect.collidepoint(mouse) and not disabled
        draw_rect = rect.inflate(7, 5) if is_hovered else rect
        if disabled:
            color = (58, 63, 80)
            text_color = (135, 142, 158)
        elif is_hovered and hover_color:
            color = hover_color
        self.draw_panel(draw_rect, color, (245, 250, 255) if is_hovered else (91, 107, 145), radius=16, shadow=True, glow=is_hovered)
        if is_hovered and not disabled:
            pygame.draw.polygon(screen, (255, 255, 255), [(draw_rect.x + 18, draw_rect.centery), (draw_rect.x + 27, draw_rect.centery - 6), (draw_rect.x + 27, draw_rect.centery + 6)])
        self.draw_text(text, font_obj, text_color, center=draw_rect.center, shadow=True)

    def draw_badge(self, rect, text, color):
        self.draw_panel(rect, color, (255, 255, 255), radius=999, shadow=False)
        self.draw_text(text, small_font, THEME["text_dark"], center=rect.center)

    def draw_tile(self, rect, tile):
        palette = {
            WALL: ((30, 37, 52), (53, 62, 82), (13, 17, 28)),
            PATH: ((46, 57, 73), (66, 78, 97), (27, 34, 48)),
            MUD: ((90, 60, 43), (128, 87, 58), (55, 39, 32)),
            ICE: ((66, 148, 178), (136, 218, 238), (29, 76, 103)),
            DOOR: ((101, 70, 42), (170, 113, 57), (55, 36, 24)),
        }
        base, light, dark = palette[tile]
        pygame.draw.rect(screen, dark, rect)
        inner = rect.inflate(-3, -3)
        pygame.draw.rect(screen, base, inner, border_radius=7)
        if tile == WALL:
            for yy in range(inner.y + 7, inner.bottom, 12):
                pygame.draw.line(screen, light, (inner.x + 4, yy), (inner.right - 4, yy), 2)
            for xx in range(inner.x + 12, inner.right, 24):
                pygame.draw.line(screen, (24, 29, 43), (xx, inner.y + 4), (xx, inner.bottom - 4), 1)
        elif tile == PATH:
            pygame.draw.rect(screen, (88, 99, 119), inner.inflate(-10, -10), 1, border_radius=5)
            pygame.draw.circle(screen, (103, 113, 130), (inner.x + 10, inner.y + 9), 2)
            pygame.draw.circle(screen, (47, 54, 70), (inner.right - 9, inner.bottom - 11), 2)
        elif tile == MUD:
            pygame.draw.circle(screen, light, (inner.centerx - 6, inner.centery + 4), 7)
            pygame.draw.circle(screen, dark, (inner.centerx + 8, inner.centery - 5), 5)
            pygame.draw.ellipse(screen, (72, 44, 29), (inner.x + 8, inner.y + 20, 18, 8))
        elif tile == ICE:
            pygame.draw.rect(screen, light, inner.inflate(-8, -8), 1, border_radius=7)
            pygame.draw.line(screen, (225, 252, 255), (inner.x + 8, inner.y + 11), (inner.right - 9, inner.bottom - 8), 2)
            pygame.draw.line(screen, (205, 245, 255), (inner.right - 14, inner.y + 7), (inner.centerx, inner.centery + 2), 1)
        elif tile == DOOR:
            pygame.draw.rect(screen, light, inner.inflate(-12, -7), border_radius=5)
            pygame.draw.line(screen, (54, 31, 22), (inner.centerx, inner.y + 7), (inner.centerx, inner.bottom - 7), 2)
            pygame.draw.circle(screen, (255, 214, 91), (inner.right - 12, inner.centery), 3)
        pygame.draw.rect(screen, (13, 16, 27), rect, 1)

    def draw_player_sprite(self, center, skin_key=None, scale=1.0, label=False):
        skin_key = skin_key or self.selected_skin
        skin = self.player_skins.get(skin_key, self.player_skins["zex"])
        cx, cy = int(center[0]), int(center[1])
        s = max(1, int(20 * scale))
        accent = skin["accent"]
        shirt = skin["shirt"]
        hair = skin["hair"]
        skin_tone = skin.get("skin", (228, 178, 137))
        style = skin.get("style", "zex")

        # Soft ground shadow and player selection ring.
        pygame.draw.ellipse(screen, (2, 5, 12), (cx - s, cy + s // 2, s * 2, s // 2))
        pygame.draw.circle(screen, accent, (cx, cy), s + 5, 2)

        # Arms.
        arm_color = (25, 31, 43) if style in ("ninja", "cyber") else shirt
        pygame.draw.line(screen, arm_color, (cx - s // 2 - 6, cy + 6), (cx - s - 6, cy + 16), 6)
        pygame.draw.line(screen, arm_color, (cx + s // 2 + 6, cy + 6), (cx + s + 6, cy + 16), 6)

        # Body.
        pygame.draw.rect(screen, (25, 31, 43), (cx - s // 2 - 3, cy - 1, s + 6, s + 11), border_radius=8)
        pygame.draw.rect(screen, shirt, (cx - s // 2, cy + 1, s, s + 6), border_radius=7)
        pygame.draw.line(screen, accent, (cx - s // 2 + 2, cy + s // 2), (cx + s // 2 - 2, cy + s // 2), 3)

        # Head / hair / gear variants.
        if style == "ninja":
            pygame.draw.circle(screen, (18, 22, 30), (cx, cy - s // 2), s // 2 + 7)
            pygame.draw.rect(screen, (12, 15, 22), (cx - 12, cy - s // 2 - 5, 24, 12), border_radius=5)
            pygame.draw.rect(screen, accent, (cx - 11, cy - s // 2 - 1, 22, 4), border_radius=3)
            pygame.draw.circle(screen, (235, 245, 255), (cx - 5, cy - s // 2 + 1), 2)
            pygame.draw.circle(screen, (235, 245, 255), (cx + 5, cy - s // 2 + 1), 2)
        elif style == "cyber":
            pygame.draw.circle(screen, skin_tone, (cx, cy - s // 2), s // 2 + 6)
            pygame.draw.rect(screen, (20, 29, 43), (cx - 14, cy - s // 2 - 12, 28, 12), border_radius=5)
            pygame.draw.rect(screen, accent, (cx - 12, cy - s // 2 - 4, 24, 6), border_radius=4)
            pygame.draw.line(screen, accent, (cx + 11, cy - s // 2 + 2), (cx + 17, cy - s // 2 + 8), 2)
        elif style == "zex":
            pygame.draw.circle(screen, hair, (cx - 12, cy - s // 2 + 2), 8)
            pygame.draw.circle(screen, skin_tone, (cx, cy - s // 2), s // 2 + 6)
            pygame.draw.arc(screen, hair, (cx - 15, cy - s // 2 - 14, 30, 22), 3.05, 6.25, 6)
            pygame.draw.circle(screen, hair, (cx + 11, cy - s // 2 - 2), 6)
            pygame.draw.circle(screen, accent, (cx + 14, cy - s // 2 + 5), 3)
            pygame.draw.circle(screen, (250, 250, 255), (cx - 5, cy - s // 2), 3)
            pygame.draw.circle(screen, (250, 250, 255), (cx + 5, cy - s // 2), 3)
            pygame.draw.circle(screen, (16, 20, 28), (cx - 5, cy - s // 2), 1)
            pygame.draw.circle(screen, (16, 20, 28), (cx + 5, cy - s // 2), 1)
        elif style == "rook":
            pygame.draw.circle(screen, skin_tone, (cx, cy - s // 2), s // 2 + 6)
            pygame.draw.rect(screen, (40, 37, 32), (cx - 14, cy - s // 2 - 11, 28, 11), border_radius=5)
            pygame.draw.rect(screen, accent, (cx - 6, cy - s // 2 - 9, 12, 3), border_radius=2)
            pygame.draw.rect(screen, (41, 47, 55), (cx - 12, cy + 2, 24, 9), border_radius=3)
            pygame.draw.circle(screen, (250, 250, 255), (cx - 5, cy - s // 2), 3)
            pygame.draw.circle(screen, (250, 250, 255), (cx + 5, cy - s // 2), 3)
            pygame.draw.circle(screen, (16, 20, 28), (cx - 5, cy - s // 2), 1)
            pygame.draw.circle(screen, (16, 20, 28), (cx + 5, cy - s // 2), 1)
        else:
            pygame.draw.circle(screen, skin_tone, (cx, cy - s // 2), s // 2 + 6)
            pygame.draw.arc(screen, hair, (cx - 14, cy - s // 2 - 14, 28, 20), 3.14, 6.28, 6)
            pygame.draw.rect(screen, accent, (cx - 14, cy - s // 2 - 9, 28, 6), border_radius=3)
            pygame.draw.circle(screen, (250, 250, 255), (cx - 5, cy - s // 2), 3)
            pygame.draw.circle(screen, (250, 250, 255), (cx + 5, cy - s // 2), 3)
            pygame.draw.circle(screen, (16, 20, 28), (cx - 5, cy - s // 2), 1)
            pygame.draw.circle(screen, (16, 20, 28), (cx + 5, cy - s // 2), 1)

        if style not in ("ninja", "cyber"):
            pygame.draw.line(screen, (50, 32, 30), (cx - 5, cy - s // 2 + 8), (cx + 5, cy - s // 2 + 8), 2)

        # Boots / lower body.
        pygame.draw.rect(screen, (22, 27, 37), (cx - s // 2 - 4, cy + s + 2, 8, 8), border_radius=3)
        pygame.draw.rect(screen, (22, 27, 37), (cx + s // 2 - 4, cy + s + 2, 8, 8), border_radius=3)

        if label:
            self.draw_text(skin["name"], small_font, THEME["text"], center=(cx, cy + 38))

    def draw_zombie_sprite(self, center, z_type="greedy", frozen=False, scale=1.0):
        cx, cy = int(center[0]), int(center[1])
        s = max(1, int(20 * scale))
        data = {
            "greedy": {"skin": (122, 186, 95), "shirt": (109, 87, 56), "eye": (255, 237, 91), "tag": "G"},
            "bfs": {"skin": (75, 202, 116), "shirt": (63, 92, 72), "eye": (255, 246, 143), "tag": "B"},
            "astar": {"skin": (66, 132, 255), "shirt": (55, 60, 98), "eye": (255, 74, 90), "tag": "A*"},
        }.get(z_type, {"skin": (90, 190, 110), "shirt": (70, 80, 70), "eye": (255, 240, 80), "tag": "?"})
        pulse = 2 if z_type == "astar" and (pygame.time.get_ticks() // 250) % 2 == 0 else 0
        pygame.draw.ellipse(screen, (2, 4, 10), (cx - s, cy + s // 2, s * 2, s // 2))
        if z_type == "astar":
            pygame.draw.circle(screen, (255, 70, 90), (cx, cy), s + 10 + pulse, 2)
        pygame.draw.line(screen, data["skin"], (cx - s - 5, cy + 1), (cx - s // 2, cy + 13), 6)
        pygame.draw.line(screen, data["skin"], (cx + s + 5, cy - 1), (cx + s // 2, cy + 13), 6)
        pygame.draw.rect(screen, data["shirt"], (cx - s // 2 - 3, cy, s + 6, s + 8), border_radius=7)
        pygame.draw.polygon(screen, (32, 37, 48), [(cx - 10, cy + 5), (cx - 2, cy + 13), (cx - 11, cy + 18)])
        pygame.draw.circle(screen, data["skin"], (cx, cy - s // 2), s // 2 + 7)
        pygame.draw.circle(screen, (54, 93, 66), (cx + 8, cy - s // 2 - 5), 3)
        pygame.draw.circle(screen, data["eye"], (cx - 5, cy - s // 2 - 1), 3 + pulse)
        pygame.draw.circle(screen, data["eye"], (cx + 6, cy - s // 2 - 2), 3 + pulse)
        pygame.draw.circle(screen, (10, 12, 16), (cx - 5, cy - s // 2 - 1), 1)
        pygame.draw.circle(screen, (10, 12, 16), (cx + 6, cy - s // 2 - 2), 1)
        pygame.draw.line(screen, (30, 35, 28), (cx - 7, cy - s // 2 + 9), (cx + 8, cy - s // 2 + 7), 2)
        if frozen:
            pygame.draw.circle(screen, (205, 248, 255), (cx, cy), s + 9, 3)
            pygame.draw.line(screen, (205, 248, 255), (cx - s, cy - s), (cx + s, cy + s), 2)

    def draw_character(self, center, color, kind="player", frozen=False):
        if kind == "zombie":
            self.draw_zombie_sprite(center, "greedy", frozen=frozen)
        else:
            self.draw_player_sprite(center)

    def draw_exit(self, center, small=False):
        cx, cy = int(center[0]), int(center[1])
        r = 16 if small else 22
        pygame.draw.circle(screen, (2, 4, 10), (cx + 3, cy + 4), r + 3)
        pygame.draw.circle(screen, (255, 202, 71), (cx, cy), r + 2)
        pygame.draw.circle(screen, (255, 244, 168), (cx, cy), r - 5)
        pygame.draw.rect(screen, (42, 28, 20), (cx - 8, cy - 10, 16, 22), border_radius=4)
        pygame.draw.circle(screen, (255, 222, 90), (cx + 4, cy + 1), 2)
        self.draw_text("EXIT", tiny_font, THEME["text_dark"], center=(cx, cy + r + 10))

    def draw_item(self, center, item_type):
        color = ITEM_COLORS[item_type]
        cx, cy = int(center[0]), int(center[1])
        pygame.draw.circle(screen, (2, 4, 10), (cx + 2, cy + 4), 16)
        pygame.draw.circle(screen, color, (cx, cy), 15)
        pygame.draw.circle(screen, (255, 255, 255), (cx - 4, cy - 5), 3)
        if item_type == SPEED_BOOST:
            pygame.draw.polygon(screen, THEME["text_dark"], [(cx - 2, cy - 10), (cx + 6, cy - 1), (cx + 1, cy - 1), (cx + 4, cy + 10), (cx - 7, cy - 2), (cx - 1, cy - 2)])
        elif item_type == FREEZE_TRAP:
            for angle in range(0, 180, 45):
                if angle == 0:
                    pygame.draw.line(screen, THEME["text_dark"], (cx - 9, cy), (cx + 9, cy), 2)
                elif angle == 90:
                    pygame.draw.line(screen, THEME["text_dark"], (cx, cy - 9), (cx, cy + 9), 2)
                else:
                    pygame.draw.line(screen, THEME["text_dark"], (cx - 7, cy - 7), (cx + 7, cy + 7), 2)
                    pygame.draw.line(screen, THEME["text_dark"], (cx - 7, cy + 7), (cx + 7, cy - 7), 2)
                    break
        else:
            pygame.draw.circle(screen, THEME["text_dark"], (cx, cy), 8, 2)
            pygame.draw.circle(screen, THEME["text_dark"], (cx, cy), 3)

    def draw_character_card(self, rect, skin_key, selected=False):
        skin = self.player_skins[skin_key]
        border = skin["accent"] if selected else (68, 82, 112)
        bg = (28, 38, 58) if selected else (21, 29, 46)
        self.draw_panel(rect, bg, border, radius=22, shadow=True, glow=selected)
        self.draw_player_sprite((rect.centerx, rect.y + 76), skin_key, scale=1.12)
        self.draw_text(skin["name"], card_font, skin["accent"], center=(rect.centerx, rect.y + 144))
        self.draw_text(skin["role"], small_font, THEME["muted"], center=(rect.centerx, rect.y + 174))
        gender_text = skin.get("gender", "male").upper()
        gender_color = (234, 102, 154) if skin.get("gender") == "female" else (96, 176, 255)
        gender_badge = pygame.Rect(rect.centerx - 50, rect.y + 205, 100, 26)
        self.draw_badge(gender_badge, gender_text, gender_color)
        badge = pygame.Rect(rect.centerx - 58, rect.bottom - 44, 116, 28)
        self.draw_badge(badge, "SELECTED" if selected else "COSMETIC", skin["accent"] if selected else (86, 96, 124))

    def draw_main_menu(self):
        self.draw_gradient_background((8, 12, 24), (31, 19, 39))
        left_card = pygame.Rect(54, 78, 470, 565)
        self.draw_panel(left_card, (18, 24, 42), (83, 102, 145), radius=30, glow=True)
        self.draw_text("NO WAY OUT", title_font, THEME["text"], center=(290, 150), shadow=True)
        self.draw_text("Dark Cartoon Survival Edition", font, THEME["accent_2"], center=(290, 212))
        self.draw_text("Escape the maze while zombies hunt you with Greedy, BFS and A* AI.", small_font, THEME["muted"], center=(290, 250))

        self.btn_campaign = pygame.Rect(135, 306, 310, 54)
        self.btn_character = pygame.Rect(135, 374, 310, 54)
        self.btn_editor = pygame.Rect(135, 442, 310, 54)
        self.btn_help = pygame.Rect(135, 510, 310, 54)
        self.draw_button(self.btn_campaign, "Start Campaign", (72, 220, 142), (103, 250, 172), menu_font, THEME["text_dark"])
        self.draw_button(self.btn_character, "Character Select", (88, 154, 255), (118, 184, 255), menu_font, THEME["text_dark"])
        self.draw_button(self.btn_editor, "Level Editor", (255, 197, 72), (255, 222, 112), menu_font, THEME["text_dark"])
        self.draw_button(self.btn_help, "How to Play", (164, 119, 255), (190, 150, 255), menu_font, THEME["text_dark"])

        hint_rect = pygame.Rect(112, 592, 356, 38)
        self.draw_panel(hint_rect, (34, 42, 63), (72, 88, 124), radius=14, shadow=False)
        self.draw_text("WASD / Arrows to move  |  1,2,3 powerups", small_font, THEME["muted"], center=hint_rect.center)

        preview = pygame.Rect(575, 92, 320, 505)
        self.draw_panel(preview, (17, 23, 37), (96, 115, 156), radius=30, shadow=True, glow=True)
        self.draw_text("SURVIVAL PREVIEW", font, THEME["accent_2"], center=(preview.centerx, preview.y + 36))
        # Mini mock scene for first impression only.
        mini_origin = (preview.x + 44, preview.y + 88)
        mini_size = 38
        sample_grid = [
            [WALL, WALL, WALL, WALL, WALL, WALL],
            [WALL, PATH, PATH, MUD, PATH, WALL],
            [WALL, ICE, WALL, PATH, PATH, WALL],
            [WALL, PATH, PATH, DOOR, PATH, WALL],
            [WALL, PATH, WALL, PATH, PATH, WALL],
            [WALL, WALL, WALL, WALL, WALL, WALL],
        ]
        for r in range(6):
            for c in range(6):
                rect = pygame.Rect(mini_origin[0] + c * mini_size, mini_origin[1] + r * mini_size, mini_size, mini_size)
                old_size = TILE_SIZE
                self.draw_tile(rect, sample_grid[r][c])
        self.draw_player_sprite((mini_origin[0] + 1.5 * mini_size, mini_origin[1] + 1.5 * mini_size), self.selected_skin)
        self.draw_zombie_sprite((mini_origin[0] + 4.5 * mini_size, mini_origin[1] + 2.5 * mini_size), "astar")
        self.draw_exit((mini_origin[0] + 4.5 * mini_size, mini_origin[1] + 4.5 * mini_size), small=True)
        self.draw_text("Current survivor", small_font, THEME["muted"], center=(preview.centerx, preview.bottom - 92))
        self.draw_text(self.player_skins[self.selected_skin]["name"], menu_font, self.player_skins[self.selected_skin]["accent"], center=(preview.centerx, preview.bottom - 54), shadow=True)

    def draw_character_select(self):
        self.draw_gradient_background((9, 13, 26), (20, 26, 42))
        self.draw_text("CHOOSE YOUR SURVIVOR", title_font, THEME["text"], center=(WIDTH // 2, 76))
        self.draw_text("Cosmetic only: same movement, same items, same AI challenge.", font, THEME["muted"], center=(WIDTH // 2, 122))
        self.skin_cards = {}
        card_w, card_h, gap = 166, 326, 18
        start_x = (WIDTH - (card_w * len(self.skin_order) + gap * (len(self.skin_order) - 1))) // 2
        for i, skin_key in enumerate(self.skin_order):
            rect = pygame.Rect(start_x + i * (card_w + gap), 172, card_w, card_h)
            self.skin_cards[skin_key] = rect
            self.draw_character_card(rect, skin_key, self.selected_skin == skin_key)
        selected = self.player_skins[self.selected_skin]
        selected_bar = pygame.Rect(WIDTH // 2 - 245, 520, 490, 36)
        self.draw_panel(selected_bar, (22, 31, 48), selected["accent"], radius=17, shadow=False, glow=True)
        self.draw_text(f"Selected: {selected['name']}  |  {selected['gender'].upper()}  |  visual skin only", small_font, THEME["text"], center=selected_bar.center)
        self.btn_character_start = pygame.Rect(WIDTH // 2 - 170, 580, 340, 56)
        self.btn_back_rect = pygame.Rect(28, 26, 116, 44)
        self.draw_button(self.btn_character_start, "Continue", THEME["success"], (126, 245, 181), menu_font, THEME["text_dark"])
        self.draw_button(self.btn_back_rect, "Back", (58, 69, 95), (79, 94, 128), font)

    def draw_tutorial(self):
        self.draw_gradient_background((9, 13, 26), (24, 27, 44))
        card = pygame.Rect(70, 62, WIDTH - 140, HEIGHT - 124)
        self.draw_panel(card, (18, 25, 41), (87, 106, 147), radius=30, glow=True)
        self.draw_text("HOW TO PLAY", title_font, THEME["text"], center=(WIDTH//2, 122), shadow=True)
        self.draw_text("Reach the glowing exit. Zombies use real pathfinding algorithms to hunt you.", font, THEME["muted"], center=(WIDTH//2, 176))

        sections = [
            ("Controls", "Move with WASD or Arrow Keys. Press ESC/P to pause."),
            ("Powerups", "1 = Speed boost, 2 = Freeze zombies, 3 = Decoy target."),
            ("Tiles", "Mud slows you, ice speeds you up, doors open/close, walls block movement."),
            ("Enemies", "Yellow = Greedy, Green = BFS shortest path, Blue = A* weighted pathfinder."),
            ("Editor", "Create a custom maze, validate it, then play-test it instantly."),
        ]
        for i, (head, body) in enumerate(sections):
            y = 225 + i * 70
            panel = pygame.Rect(130, y, WIDTH - 260, 52)
            self.draw_panel(panel, (26, 35, 55), (75, 92, 125), radius=16, shadow=False)
            self.draw_text(head, font, THEME["accent_2"], midleft=(panel.x + 22, panel.centery - 11))
            self.draw_text(body, small_font, THEME["text"], midleft=(panel.x + 170, panel.centery + 10))

        # Tiny tile legend preview.
        legend_x, legend_y = WIDTH//2 - 170, 585
        for i, tile in enumerate([PATH, MUD, ICE, DOOR, WALL]):
            rect = pygame.Rect(legend_x + i * 70, legend_y, 38, 38)
            self.draw_tile(rect, tile)
        self.draw_text("Tip: doors changing can reroute A* zombies, so watch the maze.", small_font, THEME["warning"], center=(WIDTH//2, 650))
        self.btn_tutorial_back = pygame.Rect(28, 26, 116, 44)
        self.draw_button(self.btn_tutorial_back, "Back", (58, 69, 95), (79, 94, 128), font)

    def draw_campaign_map(self):
        self.draw_gradient_background((12, 17, 31), (24, 32, 55))
        self.draw_text("SELECT LEVEL", title_font, THEME["text"], center=(WIDTH//2, 76), shadow=True)
        self.draw_text("Each zombie family shows a different pathfinding algorithm.", font, THEME["muted"], center=(WIDTH//2, 124))
        self.level_buttons = []
        start_x = WIDTH//2 - 310
        start_y = 190
        last_center = None
        for i in range(15):
            row = i // 5
            col = i % 5
            rect = pygame.Rect(start_x + col*155, start_y + row*116, 105, 84)
            self.level_buttons.append(rect)
            unlocked = i < self.unlocked_levels
            if i < 5:
                diff, base, ztype = "GREEDY", THEME["success"], "greedy"
            elif i < 10:
                diff, base, ztype = "BFS", THEME["warning"], "bfs"
            else:
                diff, base, ztype = "A*", THEME["danger"], "astar"
            if last_center:
                pygame.draw.line(screen, (75, 90, 122), last_center, rect.center, 3)
            last_center = rect.center
            color = base if unlocked else (54, 59, 75)
            border = (255, 255, 255) if rect.collidepoint(pygame.mouse.get_pos()) and unlocked else (91, 107, 145)
            self.draw_panel(rect, color, border, radius=22, shadow=True, glow=rect.collidepoint(pygame.mouse.get_pos()) and unlocked)
            if unlocked:
                self.draw_zombie_sprite((rect.centerx, rect.y + 24), ztype, scale=0.6)
            else:
                self.draw_text("LOCK", small_font, (135, 142, 160), center=(rect.centerx, rect.y + 24))
            level_color = THEME["text_dark"] if unlocked else (145, 150, 165)
            self.draw_text(str(i+1), menu_font, level_color, center=(rect.centerx, rect.centery + 10), shadow=False)
            self.draw_text(diff if unlocked else "LOCKED", tiny_font, level_color, center=(rect.centerx, rect.bottom - 13))
        legend = pygame.Rect(WIDTH//2 - 330, HEIGHT - 82, 660, 42)
        self.draw_panel(legend, (26, 33, 53), (79, 95, 132), radius=18, shadow=False)
        self.draw_text("Greedy: direct chase   |   BFS: shortest route   |   A*: weighted intelligent pathfinding", small_font, THEME["muted"], center=legend.center)
        self.btn_back_rect = pygame.Rect(24, 24, 116, 44)
        self.draw_button(self.btn_back_rect, "Back", (74, 82, 112), (95, 105, 145), font)

    def draw_editor(self):
        self.draw_gradient_background((14, 18, 31), (32, 30, 50))
        self.tool_rects = {}
        self.draw_text("LEVEL EDITOR", menu_font, THEME["text"], center=(WIDTH//2, 30), shadow=True)
        self.draw_text("Paint tiles, validate the maze, then play-test it.", small_font, THEME["muted"], center=(WIDTH//2, 58))
        board_rect = pygame.Rect(self.grid_x_offset - 10, self.grid_y_offset - 10, COLS*TILE_SIZE + 20, ROWS*TILE_SIZE + 20)
        self.draw_panel(board_rect, (15, 20, 32), (75, 92, 125), radius=18, shadow=True)
        for r in range(ROWS):
            for c in range(COLS):
                rect = pygame.Rect(self.grid_x_offset + c*TILE_SIZE, self.grid_y_offset + r*TILE_SIZE, TILE_SIZE, TILE_SIZE)
                self.draw_tile(rect, self.editor_grid[r][c])
        sx = self.grid_x_offset + self.editor_player_start[1]*TILE_SIZE + TILE_SIZE//2
        sy = self.grid_y_offset + self.editor_player_start[0]*TILE_SIZE + TILE_SIZE//2
        self.draw_player_sprite((sx, sy), self.selected_skin)
        self.draw_text("S", font, THEME["text"], center=(sx, sy + 24), shadow=True)
        wx = self.grid_x_offset + self.editor_win_point[1]*TILE_SIZE + TILE_SIZE//2
        wy = self.grid_y_offset + self.editor_win_point[0]*TILE_SIZE + TILE_SIZE//2
        self.draw_exit((wx, wy), small=True)
        for z in self.editor_zombie_spawns:
            zx = self.grid_x_offset + z[1]*TILE_SIZE + TILE_SIZE//2
            zy = self.grid_y_offset + z[0]*TILE_SIZE + TILE_SIZE//2
            self.draw_zombie_sprite((zx, zy), self.editor_zombie_diff)
        left = pygame.Rect(8, 82, 142, 510)
        self.draw_panel(left, (20, 26, 43), (79, 95, 132), radius=20)
        self.draw_text("Tools", font, THEME["text"], center=(left.centerx, left.top + 25))
        tools = [(WALL, "Wall"), (PATH, "Path"), (MUD, "Mud"), (ICE, "Ice"), (DOOR, "Door"), ("Start(S)", "Start"), ("End(E)", "Exit"), ("Zombie(Z)", "Zombie")]
        for i, (tool_id, label) in enumerate(tools):
            rect = pygame.Rect(left.x + 12, left.y + 56 + i*48, 118, 36)
            selected = self.editor_current_tool == tool_id
            color = (90, 168, 255) if selected else (48, 58, 84)
            text_color = THEME["text_dark"] if selected else THEME["text"]
            self.draw_button(rect, label, color, (124, 195, 255), font, text_color)
            self.tool_rects[tool_id] = rect
        right = pygame.Rect(WIDTH - 166, 82, 154, 305)
        self.draw_panel(right, (20, 26, 43), (79, 95, 132), radius=20)
        self.draw_text("Actions", font, THEME["text"], center=(right.centerx, right.top + 25))
        self.btn_diff = pygame.Rect(right.x + 12, right.y + 56, 130, 40)
        self.draw_button(self.btn_diff, f"AI: {self.editor_zombie_diff.upper()}", (96, 94, 166), (124, 122, 205), small_font)
        self.btn_validate = pygame.Rect(right.x + 12, right.y + 112, 130, 40)
        self.draw_button(self.btn_validate, "Validate", (255, 203, 83), (255, 226, 118), font, THEME["text_dark"])
        self.btn_play = pygame.Rect(right.x + 12, right.y + 168, 130, 40)
        self.draw_button(self.btn_play, "Play Test", (72, 220, 142), (103, 250, 172), font, THEME["text_dark"], disabled=not self.editor_valid)
        self.btn_back_rect = pygame.Rect(right.x + 12, right.y + 224, 130, 40)
        self.draw_button(self.btn_back_rect, "Menu", (255, 88, 103), (255, 118, 132), font)
        help_box = pygame.Rect(WIDTH - 166, 420, 154, 128)
        self.draw_panel(help_box, (24, 31, 49), (79, 95, 132), radius=18, shadow=False)
        self.draw_text("Left click", small_font, THEME["accent_2"], center=(help_box.centerx, help_box.y + 28))
        self.draw_text("paint / place", tiny_font, THEME["muted"], center=(help_box.centerx, help_box.y + 49))
        self.draw_text("Borders stay", small_font, THEME["accent_2"], center=(help_box.centerx, help_box.y + 82))
        self.draw_text("locked walls", tiny_font, THEME["muted"], center=(help_box.centerx, help_box.y + 103))
        status = pygame.Rect(170, HEIGHT - 46, WIDTH - 340, 36)
        border = THEME["success"] if self.editor_valid else THEME["warning"]
        self.draw_panel(status, (24, 31, 49), border, radius=16, shadow=False, glow=self.editor_valid)
        self.draw_text(self.editor_message, font, border, center=status.center)

    def validate_editor(self):
        reachable = self.get_reachable_tiles(tuple(self.editor_player_start), self.editor_grid)
        if tuple(self.editor_win_point) not in reachable:
            self.editor_valid = False
            self.editor_message = "Invalid map: the exit cannot be reached."
            return False
        for z in self.editor_zombie_spawns:
            if tuple(z) not in reachable:
                self.editor_valid = False
                self.editor_message = "Invalid map: a zombie spawn is blocked."
                return False
        self.editor_valid = True
        self.editor_message = "Valid map. Press Play Test to run it."
        return True

    def draw_danger_overlay(self):
        if not hasattr(self, "zombies") or not self.zombies:
            return
        min_dist = min(abs(z.pos[0] - self.player[0]) + abs(z.pos[1] - self.player[1]) for z in self.zombies)
        if min_dist > 4:
            return
        alpha = max(35, 115 - min_dist * 22)
        pulse = 18 if (pygame.time.get_ticks() // 220) % 2 == 0 else 0
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.rect(overlay, (255, 45, 68, alpha + pulse), (0, 0, WIDTH, HEIGHT), 10)
        screen.blit(overlay, (0, 0))

    def draw_game(self):
        self.draw_gradient_background((9, 12, 22), (25, 30, 42))
        header = pygame.Rect(16, 10, WIDTH - 32, 48)
        self.draw_panel(header, (18, 24, 40), (75, 92, 125), radius=18, shadow=False)
        title = f"Level {self.current_level_idx+1}" if self.state == "GAME" else "Custom Level"
        z_label = self.config.get("zombie_type", self.editor_zombie_diff).upper() if hasattr(self, "config") else "CUSTOM"
        skin_name = self.player_skins[self.selected_skin]["name"]
        self.draw_text(f"{title}  |  {skin_name}", font, THEME["text"], midleft=(36, header.centery))
        self.draw_text(f"Enemy AI: {z_label}", small_font, THEME["accent_2"], center=(WIDTH//2 - 165, header.centery))
        self.draw_text("Objective: reach the glowing exit", small_font, THEME["muted"], center=(WIDTH//2 + 68, header.centery))
        self.draw_text("1 Speed  2 Freeze  3 Decoy", small_font, THEME["warning"], center=(WIDTH - 210, header.centery))
        self.btn_game_menu = pygame.Rect(WIDTH - 106, 18, 82, 32)
        self.draw_button(self.btn_game_menu, "Menu", (58, 69, 95), (79, 94, 128), small_font)
        board_rect = pygame.Rect(self.grid_x_offset - 10, self.grid_y_offset - 10, COLS*TILE_SIZE + 20, ROWS*TILE_SIZE + 20)
        self.draw_panel(board_rect, (11, 15, 26), (75, 92, 125), radius=18, shadow=True)
        for r in range(ROWS):
            for c in range(COLS):
                rect = pygame.Rect(self.grid_x_offset + c*TILE_SIZE, self.grid_y_offset + r*TILE_SIZE, TILE_SIZE, TILE_SIZE)
                self.draw_tile(rect, self.grid[r][c])
        if self.freeze_until:
            ice_overlay = pygame.Surface((COLS*TILE_SIZE, ROWS*TILE_SIZE), pygame.SRCALPHA)
            ice_overlay.fill((150, 230, 255, 58))
            screen.blit(ice_overlay, (self.grid_x_offset, self.grid_y_offset))
        wx = self.grid_x_offset + self.win_point[1] * TILE_SIZE + TILE_SIZE//2
        wy = self.grid_y_offset + self.win_point[0] * TILE_SIZE + TILE_SIZE//2
        self.draw_exit((wx, wy))
        for item in self.items:
            ix = self.grid_x_offset + item['pos'][1] * TILE_SIZE + TILE_SIZE//2
            iy = self.grid_y_offset + item['pos'][0] * TILE_SIZE + TILE_SIZE//2
            self.draw_item((ix, iy), item['type'])
        if self.decoy_position and pygame.time.get_ticks() < self.decoy_until:
            dx = self.grid_x_offset + self.decoy_position[1] * TILE_SIZE + TILE_SIZE//2
            dy = self.grid_y_offset + self.decoy_position[0] * TILE_SIZE + TILE_SIZE//2
            pygame.draw.circle(screen, ITEM_COLORS[DECOY], (dx, dy), 25, 4)
            pygame.draw.circle(screen, ITEM_COLORS[DECOY], (dx, dy), 12, 2)
            self.draw_text("DECOY", tiny_font, ITEM_COLORS[DECOY], center=(dx, dy + 27), shadow=True)
        for z in self.zombies:
            zx = self.grid_x_offset + z.pos[1] * TILE_SIZE + TILE_SIZE//2
            zy = self.grid_y_offset + z.pos[0] * TILE_SIZE + TILE_SIZE//2
            self.draw_zombie_sprite((zx, zy), z.z_type, frozen=bool(self.freeze_until))
            label = "GREEDY" if z.z_type == "greedy" else ("BFS" if z.z_type == "bfs" else "A*")
            self.draw_text(label, tiny_font, THEME["text"], center=(zx, zy + 27), shadow=True)
        px = self.grid_x_offset + int(self.player_pos[0])
        py = self.grid_y_offset + int(self.player_pos[1])
        if self.player_moving:
            trail = pygame.Surface((70, 70), pygame.SRCALPHA)
            pygame.draw.circle(trail, (*self.player_skins[self.selected_skin]["accent"], 55), (35, 35), 24)
            screen.blit(trail, (px - 35, py - 35))
        self.draw_player_sprite((px, py), self.selected_skin)
        if self.speed_boost_until:
            pygame.draw.circle(screen, ITEM_COLORS[SPEED_BOOST], (px, py), 27, 4)
        inv = pygame.Rect(WIDTH//2 - 355, HEIGHT - 55, 710, 42)
        self.draw_panel(inv, (18, 24, 40), (75, 92, 125), radius=18, shadow=False)
        entries = [(SPEED_BOOST, "1 Speed"), (FREEZE_TRAP, "2 Freeze"), (DECOY, "3 Decoy")]
        for i, (k, label) in enumerate(entries):
            slot = pygame.Rect(inv.x + 22 + i * 232, inv.y + 7, 202, 28)
            self.draw_panel(slot, (30, 38, 57), ITEM_COLORS[k], radius=13, shadow=False)
            pygame.draw.circle(screen, ITEM_COLORS[k], (slot.x + 18, slot.centery), 10)
            self.draw_text(f"{label}: {self.inventory[k]}", small_font, THEME["text"], midleft=(slot.x + 36, slot.centery))
        now = pygame.time.get_ticks()
        chip_x = WIDTH - 280
        if self.freeze_until:
            remaining = max(0, (self.freeze_until - now) // 1000 + 1)
            self.draw_badge(pygame.Rect(chip_x, 64, 108, 28), f"Frozen {remaining}s", ITEM_COLORS[FREEZE_TRAP])
            chip_x -= 118
        if self.speed_boost_until:
            remaining = max(0, (self.speed_boost_until - now) // 1000 + 1)
            self.draw_badge(pygame.Rect(chip_x, 64, 102, 28), f"Speed {remaining}s", ITEM_COLORS[SPEED_BOOST])
        self.draw_danger_overlay()

    def draw_pause_menu(self):
        self.draw_gradient_background((9, 13, 25), (20, 25, 40))
        card = pygame.Rect(WIDTH//2 - 285, HEIGHT//2 - 195, 570, 390)
        self.draw_panel(card, (18, 25, 40), (78, 94, 128), radius=30, glow=True)
        self.draw_text("PAUSED", go_font, THEME["text"], center=(WIDTH//2, HEIGHT//2 - 115))
        self.draw_text("The run is frozen until you resume or return to the menu.", font, THEME["muted"], center=(WIDTH//2, HEIGHT//2 - 70))
        skin = self.player_skins[self.selected_skin]
        self.draw_player_sprite((WIDTH//2 - 120, HEIGHT//2 - 8), self.selected_skin, scale=1.15)
        self.draw_text(f"Survivor: {skin['name']}", font, skin["accent"], center=(WIDTH//2 + 72, HEIGHT//2 - 22))
        self.draw_text("ESC / P: Resume    |    M: Main Menu", small_font, THEME["muted"], center=(WIDTH//2 + 72, HEIGHT//2 + 12))
        self.btn_pause_resume = pygame.Rect(WIDTH//2 - 175, HEIGHT//2 + 68, 350, 52)
        self.btn_pause_menu = pygame.Rect(WIDTH//2 - 175, HEIGHT//2 + 132, 350, 52)
        self.draw_button(self.btn_pause_resume, "Resume", THEME["success"], (126, 245, 181), menu_font, THEME["text_dark"])
        self.draw_button(self.btn_pause_menu, "Main Menu", (58, 69, 95), (79, 94, 128), menu_font)

    def draw_end_screen(self):
        if self.game_won:
            self.draw_gradient_background((13, 42, 36), (15, 24, 40))
            title = "LEVEL COMPLETE"
            color = THEME["success"]
            subtitle = "You found the exit before the undead reached you."
            btn_text = "Return to Editor" if self.play_mode == "editor" else ("Next Level" if self.current_level_idx < 14 else "Finish")
        else:
            self.draw_gradient_background((49, 19, 31), (13, 17, 31))
            title = "YOU WERE CAUGHT"
            color = THEME["danger"]
            subtitle = "The maze closed in. Try a smarter route."
            btn_text = "Return to Editor" if self.play_mode == "editor" else "Retry Level"
        card = pygame.Rect(WIDTH//2 - 285, HEIGHT//2 - 175, 570, 350)
        self.draw_panel(card, (18, 24, 40), (91, 107, 145), radius=30, glow=True)
        self.draw_text(title, go_font, color, center=(WIDTH//2, HEIGHT//2 - 93), shadow=True)
        self.draw_text(subtitle, font, THEME["muted"], center=(WIDTH//2, HEIGHT//2 - 42))
        if self.game_won:
            self.draw_exit((WIDTH//2, HEIGHT//2 + 10), small=True)
        else:
            self.draw_zombie_sprite((WIDTH//2, HEIGHT//2 + 12), "astar", scale=1.15)
        self.btn_main = pygame.Rect(WIDTH//2 - 175, HEIGHT//2 + 68, 350, 52)
        self.btn_next = pygame.Rect(WIDTH//2 - 175, HEIGHT//2 + 132, 350, 52)
        self.draw_button(self.btn_main, "Main Menu", (74, 82, 112), (95, 105, 145), menu_font)
        hover = tuple(min(255, v + 28) for v in color)
        self.draw_button(self.btn_next, btn_text, color, hover, menu_font, THEME["text_dark"] if self.game_won else THEME["text"])

    def run(self):
        while True:
            clock.tick(FPS)
            if self.state in ["GAME", "EDITOR_PLAY"]:
                self.update_timers()
                self.update_player_movement()
                self.toggle_doors()
                self.update_zombies()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    pos = event.pos
                    self.sound.play("click")
                    if self.state == "MAIN_MENU":
                        if self.btn_campaign.collidepoint(pos):
                            self.state = "CAMPAIGN_MAP"
                        elif self.btn_character.collidepoint(pos):
                            self.state = "CHARACTER_SELECT"
                        elif self.btn_editor.collidepoint(pos):
                            self.state = "EDITOR"
                        elif self.btn_help.collidepoint(pos):
                            self.state = "TUTORIAL"
                    elif self.state == "TUTORIAL":
                        if self.btn_tutorial_back.collidepoint(pos):
                            self.state = "MAIN_MENU"
                    elif self.state == "CHARACTER_SELECT":
                        if self.btn_back_rect.collidepoint(pos):
                            self.state = "MAIN_MENU"
                        elif self.btn_character_start.collidepoint(pos):
                            self.state = "CAMPAIGN_MAP"
                        else:
                            for skin_key, rect in self.skin_cards.items():
                                if rect.collidepoint(pos):
                                    self.selected_skin = skin_key
                    elif self.state == "CAMPAIGN_MAP":
                        if self.btn_back_rect.collidepoint(pos):
                            self.state = "MAIN_MENU"
                        for i, r in enumerate(self.level_buttons):
                            if r.collidepoint(pos) and i < self.unlocked_levels:
                                self.start_level(i)
                    elif self.state in ["GAME", "EDITOR_PLAY"]:
                        if hasattr(self, "btn_game_menu") and self.btn_game_menu.collidepoint(pos):
                            self.pause_return_state = self.state
                            self.state = "PAUSE_MENU"
                    elif self.state == "PAUSE_MENU":
                        if self.btn_pause_resume.collidepoint(pos):
                            self.state = self.pause_return_state
                        elif self.btn_pause_menu.collidepoint(pos):
                            self.state = "MAIN_MENU"
                    elif self.state in ["WIN_SCREEN", "LOSE_SCREEN"]:
                        if self.btn_main.collidepoint(pos):
                            self.state = "MAIN_MENU"
                        elif self.btn_next.collidepoint(pos):
                            if self.play_mode == "editor":
                                self.state = "EDITOR"
                            elif self.game_won:
                                if self.current_level_idx < 14:
                                    self.start_level(self.current_level_idx + 1)
                                else:
                                    self.state = "MAIN_MENU"
                            else:
                                self.start_level(self.current_level_idx)
                    elif self.state == "EDITOR":
                        if self.btn_back_rect.collidepoint(pos):
                            self.state = "MAIN_MENU"
                        elif self.btn_diff.collidepoint(pos):
                            self.editor_zombie_diff = "bfs" if self.editor_zombie_diff == "greedy" else ("astar" if self.editor_zombie_diff == "bfs" else "greedy")
                        elif self.btn_validate.collidepoint(pos):
                            self.validate_editor()
                        elif self.btn_play.collidepoint(pos) and self.editor_valid:
                            self.start_editor_level()
                        else:
                            for t, rect in self.tool_rects.items():
                                if rect.collidepoint(pos):
                                    self.editor_current_tool = t
                if self.state == "EDITOR" and pygame.mouse.get_pressed()[0]:
                    mx, my = pygame.mouse.get_pos()
                    c = (mx - self.grid_x_offset) // TILE_SIZE
                    r = (my - self.grid_y_offset) // TILE_SIZE
                    if 0 <= r < ROWS and 0 <= c < COLS:
                        if r in [0, ROWS-1] or c in [0, COLS-1]:
                            continue
                        t = self.editor_current_tool
                        if t in [WALL, PATH, MUD, ICE, DOOR]:
                            self.editor_grid[r][c] = t
                            self.editor_valid = False
                        elif t == "Start(S)":
                            self.editor_player_start = [r, c]
                            self.editor_grid[r][c] = PATH
                            self.editor_valid = False
                        elif t == "End(E)":
                            self.editor_win_point = [r, c]
                            self.editor_grid[r][c] = PATH
                            self.editor_valid = False
                        elif t == "Zombie(Z)":
                            if [r, c] not in self.editor_zombie_spawns:
                                if len(self.editor_zombie_spawns) >= 3:
                                    self.editor_zombie_spawns.pop(0)
                                self.editor_zombie_spawns.append([r, c])
                                self.editor_valid = False
                if self.state == "TUTORIAL" and event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_ESCAPE, pygame.K_p, pygame.K_BACKSPACE]:
                        self.state = "MAIN_MENU"
                if self.state == "PAUSE_MENU" and event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_ESCAPE, pygame.K_p]:
                        self.state = self.pause_return_state
                    elif event.key == pygame.K_m:
                        self.state = "MAIN_MENU"
                if self.state in ["GAME", "EDITOR_PLAY"] and event.type == pygame.KEYDOWN:
                    if event.key in [pygame.K_ESCAPE, pygame.K_p]:
                        self.pause_return_state = self.state
                        self.state = "PAUSE_MENU"
                    elif event.key in [pygame.K_UP, pygame.K_w]:
                        self.move_player(0, -1)
                    elif event.key in [pygame.K_DOWN, pygame.K_s]:
                        self.move_player(0, 1)
                    elif event.key in [pygame.K_LEFT, pygame.K_a]:
                        self.move_player(-1, 0)
                    elif event.key in [pygame.K_RIGHT, pygame.K_d]:
                        self.move_player(1, 0)
                    elif event.key == pygame.K_1:
                        self.use_item(SPEED_BOOST)
                    elif event.key == pygame.K_2:
                        self.use_item(FREEZE_TRAP)
                    elif event.key == pygame.K_3:
                        self.use_item(DECOY)
            if self.state == "MAIN_MENU":
                self.draw_main_menu()
            elif self.state == "TUTORIAL":
                self.draw_tutorial()
            elif self.state == "CHARACTER_SELECT":
                self.draw_character_select()
            elif self.state == "CAMPAIGN_MAP":
                self.draw_campaign_map()
            elif self.state == "EDITOR":
                self.draw_editor()
            elif self.state in ["GAME", "EDITOR_PLAY"]:
                self.draw_game()
            elif self.state == "PAUSE_MENU":
                self.draw_pause_menu()
            elif self.state in ["WIN_SCREEN", "LOSE_SCREEN"]:
                self.draw_end_screen()
            pygame.display.flip()

if __name__ == '__main__':
    Game().run()