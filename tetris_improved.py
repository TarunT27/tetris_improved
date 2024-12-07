import pygame
import random
from pygame import mixer
import json
import os
from math import sin, cos, radians

# Initialize Pygame and mixer
pygame.init()
mixer.init()

# Constants
BLOCK_SIZE = 30
GRID_WIDTH = 10
GRID_HEIGHT = 20
SIDEBAR_WIDTH = 200
WINDOW_WIDTH = GRID_WIDTH * BLOCK_SIZE + SIDEBAR_WIDTH
WINDOW_HEIGHT = GRID_HEIGHT * BLOCK_SIZE

# Color Themes
THEMES = {
    'Classic': {
        'background': (0, 0, 0),
        'grid': (128, 128, 128),
        'text': (255, 255, 255),
        'pieces': [
            (0, 255, 255),   # Cyan
            (255, 255, 0),   # Yellow
            (128, 0, 128),   # Purple
            (0, 255, 0),     # Green
            (255, 0, 0),     # Red
            (0, 0, 255),     # Blue
            (255, 127, 0)    # Orange
        ]
    },
    'Pastel': {
        'background': (230, 230, 230),
        'grid': (180, 180, 180),
        'text': (60, 60, 60),
        'pieces': [
            (182, 232, 241),  # Light Blue
            (255, 245, 157),  # Light Yellow
            (206, 147, 216),  # Light Purple
            (165, 214, 167),  # Light Green
            (239, 154, 154),  # Light Red
            (144, 202, 249),  # Light Blue
            (255, 204, 128)   # Light Orange
        ]
    },
    'Neon': {
        'background': (10, 10, 20),
        'grid': (30, 30, 40),
        'text': (0, 255, 255),
        'pieces': [
            (0, 255, 255),    # Cyan
            (255, 255, 0),    # Yellow
            (255, 0, 255),    # Magenta
            (0, 255, 0),      # Green
            (255, 0, 128),    # Pink
            (0, 191, 255),    # Blue
            (255, 140, 0)     # Orange
        ]
    }
}

# Tetromino shapes
SHAPES = [
    [[1, 1, 1, 1]],  # I
    [[1, 1], [1, 1]],  # O
    [[1, 1, 1], [0, 1, 0]],  # T
    [[1, 1, 0], [0, 1, 1]],  # Z
    [[0, 1, 1], [1, 1, 0]],  # S
    [[1, 1, 1], [1, 0, 0]],  # L
    [[1, 1, 1], [0, 0, 1]]   # J
]

class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        self.size = random.randint(2, 6)
        angle = random.uniform(0, 360)
        speed = random.uniform(2, 5)
        self.dx = cos(radians(angle)) * speed
        self.dy = sin(radians(angle)) * speed
        self.life = 255
        self.decay = random.uniform(5, 10)

    def update(self):
        self.x += self.dx
        self.y += self.dy
        self.dy += 0.1  # Gravity
        self.life -= self.decay
        return self.life > 0

    def draw(self, screen):
        alpha = max(0, min(255, int(self.life)))
        particle_surface = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
        particle_color = (*self.color, alpha)
        pygame.draw.circle(particle_surface, particle_color, (self.size//2, self.size//2), self.size//2)
        screen.blit(particle_surface, (int(self.x), int(self.y)))

class Tetris:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption('Tetris')
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        
        self.difficulty_levels = {
            'Easy': 50,
            'Medium': 30,
            'Hard': 15
        }
        self.current_level = 'Medium'
        self.current_theme = 'Classic'
        self.particles = []
        self.combo = 0
        self.last_clear_time = 0
        self.paused = False
        self.load_highscores()
        self.reset_game()

        # Try to load sound effects
        try:
            self.sounds = {
                'move': mixer.Sound('move.wav'),
                'rotate': mixer.Sound('rotate.wav'),
                'drop': mixer.Sound('drop.wav'),
                'clear': mixer.Sound('clear.wav'),
                'tspin': mixer.Sound('tspin.wav')
            }
        except:
            print("Sound files not found. Game will run without sound.")
            self.sounds = {}

    def load_highscores(self):
        try:
            with open('tetris_highscores.json', 'r') as f:
                self.highscores = json.load(f)
        except:
            self.highscores = []

    def save_highscores(self):
        with open('tetris_highscores.json', 'w') as f:
            json.dump(self.highscores, f)

    def update_highscores(self):
        self.highscores.append({
            'score': self.score,
            'lines': self.lines_cleared,
            'level': self.current_level,
            'date': pygame.time.get_ticks()
        })
        self.highscores.sort(key=lambda x: x['score'], reverse=True)
        self.highscores = self.highscores[:10]  # Keep only top 10
        self.save_highscores()

    def reset_game(self):
        self.grid = [[0 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.current_piece = self.new_piece()
        self.next_piece = self.new_piece()
        self.held_piece = None
        self.can_hold = True
        self.game_over = False
        self.score = 0
        self.lines_cleared = 0
        self.combo = 0
        self.fall_speed = self.difficulty_levels[self.current_level]
        self.particles = []

    def create_particles(self, row):
        theme = THEMES[self.current_theme]
        for x in range(GRID_WIDTH):
            color = self.grid[row][x] if self.grid[row][x] else theme['grid']
            for _ in range(5):  # Create 5 particles per block
                self.particles.append(Particle(
                    x * BLOCK_SIZE + BLOCK_SIZE/2,
                    row * BLOCK_SIZE + BLOCK_SIZE/2,
                    color
                ))

    def update_particles(self):
        self.particles = [p for p in self.particles if p.update()]

    def check_tspin(self):
        if len(self.current_piece['shape']) != 2 or len(self.current_piece['shape'][0]) != 3:
            return False
        
        corners = [
            (self.current_piece['x'], self.current_piece['y']),
            (self.current_piece['x'] + 2, self.current_piece['y']),
            (self.current_piece['x'], self.current_piece['y'] + 2),
            (self.current_piece['x'] + 2, self.current_piece['y'] + 2)
        ]
        
        blocked_corners = 0
        for x, y in corners:
            if (x < 0 or x >= GRID_WIDTH or y >= GRID_HEIGHT or 
                (y >= 0 and self.grid[y][x])):
                blocked_corners += 1
        
        return blocked_corners >= 3

    def new_piece(self):
        shape_idx = random.randint(0, len(SHAPES) - 1)
        shape = [row[:] for row in SHAPES[shape_idx]]  # Deep copy
        x = GRID_WIDTH // 2 - len(shape[0]) // 2
        y = 0
        return {
            'shape': shape,
            'x': x,
            'y': y,
            'color': THEMES[self.current_theme]['pieces'][shape_idx]
        }

    def hold_piece(self):
        if not self.can_hold:
            return
        
        if self.held_piece is None:
            self.held_piece = self.current_piece
            self.current_piece = self.next_piece
            self.next_piece = self.new_piece()
        else:
            self.held_piece, self.current_piece = self.current_piece, self.held_piece
            self.current_piece['x'] = GRID_WIDTH // 2 - len(self.current_piece['shape'][0]) // 2
            self.current_piece['y'] = 0
        
        self.can_hold = False

    def remove_complete_rows(self):
        full_rows = []
        for i, row in enumerate(self.grid):
            if all(cell for cell in row):
                full_rows.append(i)
                self.create_particles(i)

        if full_rows:
            if 'clear' in self.sounds:
                self.sounds['clear'].play()

            # Update combo
            current_time = pygame.time.get_ticks()
            if current_time - self.last_clear_time < 1000:
                self.combo += 1
            else:
                self.combo = 0
            self.last_clear_time = current_time

        # Remove rows and add new ones
        for row_index in full_rows:
            del self.grid[row_index]
            self.grid.insert(0, [0 for _ in range(GRID_WIDTH)])

        # Calculate score
        if full_rows:
            base_score = len(full_rows) * 100
            combo_bonus = self.combo * 50
            tspin_bonus = 400 if self.check_tspin() else 0
            self.score += base_score + combo_bonus + tspin_bonus

        self.lines_cleared += len(full_rows)
        return len(full_rows)

    def draw_text_centered(self, text, y_offset):
        text_surface = self.font.render(text, True, THEMES[self.current_theme]['text'])
        text_rect = text_surface.get_rect(center=(WINDOW_WIDTH//2, WINDOW_HEIGHT//2 + y_offset))
        self.screen.blit(text_surface, text_rect)

    def draw(self):
        theme = THEMES[self.current_theme]
        self.screen.fill(theme['background'])

        # Draw grid background
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                pygame.draw.rect(self.screen, theme['grid'],
                               (x * BLOCK_SIZE, y * BLOCK_SIZE,
                                BLOCK_SIZE - 1, BLOCK_SIZE - 1), 1)

        # Draw fallen pieces
        for y, row in enumerate(self.grid):
            for x, cell in enumerate(row):
                if cell:
                    pygame.draw.rect(self.screen, cell,
                                   (x * BLOCK_SIZE, y * BLOCK_SIZE,
                                    BLOCK_SIZE - 1, BLOCK_SIZE - 1))

        # Draw current piece
        if self.current_piece and not self.game_over and not self.paused:
            for i, row in enumerate(self.current_piece['shape']):
                for j, cell in enumerate(row):
                    if cell:
                        pygame.draw.rect(self.screen, self.current_piece['color'],
                                       ((self.current_piece['x'] + j) * BLOCK_SIZE,
                                        (self.current_piece['y'] + i) * BLOCK_SIZE,
                                        BLOCK_SIZE - 1, BLOCK_SIZE - 1))

        # Draw particles
        for particle in self.particles:
            particle.draw(self.screen)

        # Draw sidebar
        sidebar_x = GRID_WIDTH * BLOCK_SIZE + 10
        y_offset = 20

        # Score and info
        texts = [
            f'Score: {self.score}',
            f'Lines: {self.lines_cleared}',
            f'Level: {self.current_level}',
            f'Combo: {self.combo}x',
            f'Theme: {self.current_theme}'
        ]

        for text in texts:
            text_surface = self.font.render(text, True, theme['text'])
            self.screen.blit(text_surface, (sidebar_x, y_offset))
            y_offset += 40

        # Draw next piece preview
        y_offset += 20
        text_surface = self.font.render('Next:', True, theme['text'])
        self.screen.blit(text_surface, (sidebar_x, y_offset))
        y_offset += 30

        if self.next_piece:
            for i, row in enumerate(self.next_piece['shape']):
                for j, cell in enumerate(row):
                    if cell:
                        pygame.draw.rect(self.screen, self.next_piece['color'],
                                       (sidebar_x + j * BLOCK_SIZE,
                                        y_offset + i * BLOCK_SIZE,
                                        BLOCK_SIZE - 1, BLOCK_SIZE - 1))

        # Draw held piece
        y_offset += 100
        text_surface = self.font.render('Held:', True, theme['text'])
        self.screen.blit(text_surface, (sidebar_x, y_offset))
        y_offset += 30

        if self.held_piece:
            for i, row in enumerate(self.held_piece['shape']):
                for j, cell in enumerate(row):
                    if cell:
                        pygame.draw.rect(self.screen, self.held_piece['color'],
                                       (sidebar_x + j * BLOCK_SIZE,
                                        y_offset + i * BLOCK_SIZE,
                                        BLOCK_SIZE - 1, BLOCK_SIZE - 1))

        # Draw controls
        y_offset += 100
        controls = [
            'Controls:',
            '← → : Move',
            '↑ : Rotate',
            '↓ : Soft Drop',
            'Space : Hard Drop',
            'C : Hold Piece',
            'P : Pause',
            'D : Change Difficulty',
            'T : Change Theme',
            'R : Reset Game'
        ]

        for text in controls:
            text_surface = self.small_font.render(text, True, theme['text'])
            self.screen.blit(text_surface, (sidebar_x, y_offset))
            y_offset += 25

        # Draw game over or pause screen
        if self.game_over:
            s = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
            s.set_alpha(128)
            s.fill((0, 0, 0))
            self.screen.blit(s, (0, 0))
            
            self.draw_text_centered("Game Over!", -50)
            self.draw_text_centered(f"Final Score: {self.score}", 0)
            self.draw_text_centered("Press R to restart", 50)
        
        elif self.paused:
            s = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
            s.set_alpha(128)
            s.fill((0, 0, 0))
            self.screen.blit(s, (0, 0))
            
            self.draw_text_centered("Paused", -25)
            self.draw_text_centered("Press P to resume", 25)

        pygame.display.flip()