from __future__ import annotations

import os.path

import pygame
import sys
import math
from enum import Enum
from pygame.locals import *
from dataclasses import dataclass
from typing import Dict, Iterable, Tuple
from random import choice


@dataclass(frozen=True)
class Position:
    x: int
    y: int

    def translate(self, x: int | Position, y: int = 0):
        if isinstance(x, Position):
            return Position(self.x + x.x, self.y + x.y)
        else:
            return Position(self.x + x, self.y + y)

    def rot_left(self):
        return Position(-self.y, self.x)

    def rot_right(self):
        return Position(self.y, -self.x)


@dataclass(frozen=True)
class Cell:
    color: Color
    solid: bool


RENDER_BACKGROUND = Color(57, 20, 20)
BACKGROUND_CELL = Cell(Color(0, 0, 0), False)


class World:
    def __init__(self, width: int = 10, height: int = 20):
        self.grid: Dict[Position, Cell] = {}
        self.width = width
        self.height = height
        for x in range(width):
            for y in range(height):
                self.grid[Position(x, y)] = BACKGROUND_CELL

    def pos_is_free(self, pos):
        if pos in self.grid:
            return not self.grid[pos].solid
        else:
            return False

    def stamp(self, color: Color, positions: Iterable[Position]):
        for pos in positions:
            if self.pos_is_free(pos):
                self.grid[pos] = Cell(color, True)

    def clean_full_lines(self) -> int:
        """Removes the full lines, collapses the world, and returns the number of cleared lines"""
        y = self.height - 1
        line_count = 0
        while y >= 0:
            row_full = True
            for x in range(0, self.width):
                if not self.grid[Position(x, y)].solid:
                    row_full = False
                    break
            if row_full:
                line_count += 1
                for ty in range(y, -1, -1):
                    print(ty)
                    for x in range(0, self.width):
                        if ty == 0:
                            self.grid[Position(x, ty)] = BACKGROUND_CELL
                        else:
                            self.grid[Position(x, ty)] = self.grid[Position(x, ty - 1)]
            else:
                y -= 1
        return line_count


class RotationStrategy(Enum):
    NO_ROTATION = 1
    THREE_BY_THREE = 2


MOVE_OFFSETS = {
    'LEFT': Position(-1, 0),
    'RIGHT': Position(1, 0),
    'DOWN': Position(0, 1),
}


@dataclass
class Tetrimino:
    center_pos: Position
    block_offsets: Iterable[Position]
    color: Color
    rotation_strategy: RotationStrategy

    def blocks(self) -> Iterable[Position]:
        return (self.center_pos.translate(offset) for offset in self.block_offsets)

    def is_legal_in(self, world: World):
        for block in self.blocks():
            if not world.pos_is_free(block):
                return False
        return True

    def move_offset(self, offset: Position) -> Tetrimino:
        return Tetrimino(self.center_pos.translate(offset), self.block_offsets, self.color, self.rotation_strategy)

    def rotate_left(self) -> Tetrimino:
        if self.rotation_strategy == RotationStrategy.NO_ROTATION:
            return self
        else:
            return Tetrimino(self.center_pos, [offset.rot_left() for offset in self.block_offsets],
                             self.color,
                             self.rotation_strategy)

    def rotate_right(self) -> Tetrimino:
        if self.rotation_strategy == RotationStrategy.NO_ROTATION:
            return self
        else:
            return Tetrimino(self.center_pos, [offset.rot_right() for offset in self.block_offsets],
                             self.color,
                             self.rotation_strategy)

    def debug(self):
        print(f'Position {self.center_pos}')
        for block in self.blocks():
            print(f' Block: {block}')


def o_piece():
    return Tetrimino(Position(4, 2), (Position(0, 0), Position(0, 1), Position(1, 0), Position(1, 1)),
                     Color(255, 213, 0), RotationStrategy.NO_ROTATION)


def l_piece():
    return Tetrimino(Position(4, 2), (Position(0, 0), Position(-1, 0), Position(1, 0), Position(1, 1)),
                     Color(114, 203, 59), RotationStrategy.THREE_BY_THREE)


def rl_piece():
    return Tetrimino(Position(4, 2), (Position(0, 0), Position(-1, 0), Position(1, 0), Position(-1, 1)),
                     Color(255, 151, 28), RotationStrategy.THREE_BY_THREE)


def i_piece():
    return Tetrimino(Position(4, 2), (Position(0, 0), Position(-1, 0), Position(1, 0), Position(2, 0)),
                     Color(3, 65, 174), RotationStrategy.THREE_BY_THREE)


def t_piece():
    return Tetrimino(Position(4, 2), (Position(0, 0), Position(-1, 0), Position(1, 0), Position(0, 1)),
                     Color(145, 79, 166), RotationStrategy.THREE_BY_THREE)


def s_piece():
    return Tetrimino(Position(4, 2), (Position(0, 0), Position(-1, 0), Position(0, 1), Position(1, 1)),
                     Color(255, 193, 124), RotationStrategy.THREE_BY_THREE)


def z_piece():
    return Tetrimino(Position(4, 2), (Position(0, 0), Position(1, 0), Position(0, 1), Position(-1, 1)),
                     Color(255, 50, 19), RotationStrategy.THREE_BY_THREE)


@dataclass
class TetriminoFactory:
    next_tetrimino: Tetrimino

    @staticmethod
    def create() -> TetriminoFactory:
        return TetriminoFactory(TetriminoFactory._choose())

    def pop_next_tetrimino(self) -> Tetrimino:
        output = self.next_tetrimino
        self.next_tetrimino = TetriminoFactory._choose()
        return output

    def reset(self):
        self.next_tetrimino = TetriminoFactory._choose()

    @staticmethod
    def _choose() -> Tetrimino:
        return choice([o_piece, l_piece, rl_piece, i_piece, t_piece, s_piece, z_piece])()


@dataclass
class GameState:
    world: World
    score: int
    tetrimino: Tetrimino
    running: bool
    level: int
    lines_cleared: int
    t_factory: TetriminoFactory

    @staticmethod
    def create() -> GameState:
        t_factory = TetriminoFactory.create()
        return GameState(World(), 0, t_factory.pop_next_tetrimino(), True, 1, 0, t_factory)

    def reset(self):
        self.world = World(self.world.width, self.world.height)
        self.score = 0
        self.running = True
        self.level = 1
        self.lines_cleared = 0
        self.t_factory.reset()
        self.tetrimino = self.t_factory.pop_next_tetrimino()

    def update_interval_ms(self):
        return 1000 * (0.75 ** (self.level - 1))

    def update_state(self):
        if self.running:
            new_tetrimino = self.tetrimino.move_offset(MOVE_OFFSETS['DOWN'])
            if new_tetrimino.is_legal_in(self.world):
                self.tetrimino = new_tetrimino
            else:
                self.world.stamp(self.tetrimino.color, self.tetrimino.blocks())
                self._add_cleared_lines(self.world.clean_full_lines())
                self.tetrimino = self.t_factory.pop_next_tetrimino()
                if not self.tetrimino.is_legal_in(self.world):
                    self.running = False

    def _add_cleared_lines(self, lines: int):
        self.lines_cleared += lines
        self.level = 1 + math.floor(self.lines_cleared / 10)
        self.score += calculate_score_increase(lines)


class CoordinateConverter:
    def __init__(self, target_window: Rect, world_size: Tuple[int, int]):
        self.x_scale = target_window.width / world_size[0]
        self.y_scale = target_window.height / world_size[1]
        self.x_offset = target_window.x
        self.y_offset = target_window.y

    def pos_to_rect(self, pos: Position) -> Rect:
        return Rect(self.x_offset + pos.x * self.x_scale,
                    self.y_offset + pos.y * self.y_scale,
                    self.x_scale,
                    self.y_scale)


def calculate_score_increase(cleared_lines: int):
    assert (0 <= cleared_lines <= 4)
    if cleared_lines == 1:
        return 100
    elif cleared_lines == 2:
        return 200
    elif cleared_lines == 3:
        return 400
    elif cleared_lines == 4:
        return 800
    else:
        return 0


def handle_player_input(game_state: GameState, key: int) -> bool:
    new_tetrimino = None
    end_cycle_early = False
    if key == K_LEFT:
        new_tetrimino = game_state.tetrimino.move_offset(MOVE_OFFSETS['LEFT'])
    elif key == K_RIGHT:
        new_tetrimino = game_state.tetrimino.move_offset(MOVE_OFFSETS['RIGHT'])
    elif key == K_SPACE:
        new_tetrimino = game_state.tetrimino
        while new_tetrimino.move_offset(MOVE_OFFSETS['DOWN']).is_legal_in(game_state.world):
            new_tetrimino = new_tetrimino.move_offset(MOVE_OFFSETS['DOWN'])
        end_cycle_early = True
    elif key == K_UP:
        new_tetrimino = game_state.tetrimino.rotate_right()
    elif key == K_DOWN:
        new_tetrimino = game_state.tetrimino.move_offset(MOVE_OFFSETS['DOWN'])
    elif key == K_r:
        game_state.reset()
    elif key == K_s:
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.fadeout(50)
        else:
            pygame.mixer.music.play(-1, fade_ms=50)
    if new_tetrimino and new_tetrimino.is_legal_in(game_state.world):
        game_state.tetrimino = new_tetrimino
    return end_cycle_early


class Renderer:
    def __init__(self, surface: pygame.Surface, game_state: GameState, game_window: Rect, font: pygame.font.Font,
                 score_area: Rect):
        self.surface = surface
        self.game_state = game_state
        converter = CoordinateConverter(game_window, (game_state.world.width, game_state.world.height))
        self.pos_to_rect = {
            pos: converter.pos_to_rect(pos) for pos in game_state.world.grid
        }
        self.scale = max(converter.x_scale, converter.y_scale)
        self.font = font
        self.score_area = score_area
        self.game_over = self.font.render('Game Over - press R to restart', True, Color(255, 255, 255))
        margin = 20
        game_over_width = self.game_over.get_width() + margin * 2
        game_over_height = self.game_over.get_height() + margin * 2

        self.game_over_black_rect = Rect((game_window.width - game_over_width) / 2 + game_window.left,
                                         (game_window.height - game_over_height) / 2 + game_window.top,
                                         game_over_width, game_over_height)
        self.game_over_text_rect = Rect((game_window.width - self.game_over.get_width()) / 2 + game_window.left,
                                        (game_window.height - self.game_over.get_height()) / 2 + game_window.top,
                                        self.game_over.get_width(), self.game_over.get_height())

    def render_frame(self):
        self.surface.fill(RENDER_BACKGROUND)
        for pos, cell in self.game_state.world.grid.items():
            self.surface.fill(cell.color, self.pos_to_rect[pos])
        target_rect = self.score_area
        textsurface = self.font.render(f'Score: {self.game_state.score}', True, Color(255, 255, 255),
                                       RENDER_BACKGROUND)
        self.surface.blit(textsurface, target_rect)
        target_rect = Rect(target_rect.left, target_rect.top + textsurface.get_height() + 10, target_rect.width,
                           target_rect.height)
        textsurface = self.font.render(f'Level: {self.game_state.level}', True, Color(255, 255, 255),
                                       RENDER_BACKGROUND)
        self.surface.blit(textsurface, target_rect)
        target_rect = Rect(target_rect.left, target_rect.top + textsurface.get_height() + 10, target_rect.width,
                           target_rect.height)
        textsurface = self.font.render(f'Lines cleared: {self.game_state.lines_cleared}', True, Color(255, 255, 255),
                                       RENDER_BACKGROUND)
        self.surface.blit(textsurface, target_rect)

        if self.game_state.running:
            # Render active tetrimino
            for block in self.game_state.tetrimino.blocks():
                if block in self.pos_to_rect:
                    self.surface.fill(self.game_state.tetrimino.color,
                                      self.pos_to_rect[block])
        else:
            self.surface.fill(Color(0, 0, 0), self.game_over_black_rect)
            self.surface.blit(self.game_over, self.game_over_text_rect)

        # Render next tetrimino
        target_rect = Rect(target_rect.left, target_rect.top + textsurface.get_height() + 20,
                           4 * self.scale,
                           4 * self.scale)
        converter = CoordinateConverter(target_rect, (4, 4))
        self.surface.fill(Color(0, 0, 0), target_rect)
        for offset in self.game_state.t_factory.next_tetrimino.block_offsets:
            self.surface.fill(self.game_state.t_factory.next_tetrimino.color,
                              converter.pos_to_rect(offset.translate(1, 1)))


def main():
    pygame.init()
    surface: pygame.Surface = pygame.display.set_mode((700, 800))
    game_state: GameState = GameState.create()
    game_font = pygame.font.SysFont('Comic Sans MS', 30)
    renderer: Renderer = Renderer(surface, game_state, Rect(50, 50, 350, 700), game_font, Rect(450, 200, 200, 200))
    last_update = pygame.time.get_ticks()
    if os.path.isfile('music.mid'):
        pygame.mixer.music.load('music.mid')
        pygame.mixer.music.play(-1)

    while True:
        end_cycle_early = False
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if event.type == KEYDOWN:
                end_cycle_early = handle_player_input(game_state, event.key)

        if pygame.time.get_ticks() - last_update > game_state.update_interval_ms() or end_cycle_early:
            last_update = pygame.time.get_ticks()
            game_state.update_state()
        renderer.render_frame()
        pygame.display.update()


if __name__ == '__main__':
    main()
