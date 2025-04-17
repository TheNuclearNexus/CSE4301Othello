from functools import cache
import math
from multiprocessing.pool import ThreadPool
from threading import Thread
from typing import Literal, Union
import numpy as np
from colors import Colors

NONE = 0
WHITE = 1  # ⚪
BLACK = 2  # ⚫

# Swap the input team with the enemy
SWAP_TEAM = [NONE, BLACK, WHITE]
# Team -> Character
TOKEN_MAP = {
    NONE: "◯",
    WHITE: "⬤",
    BLACK: f"{Colors.RED}⬤{Colors.END}",
    -1: f"{Colors.GREEN}◯{Colors.END}",
}

# General constants weights for tiles around the grid
WEIGHT_GRID = [
    8,
    0,
    2,
    1,
    1,
    2,
    0,
    8,
    0,
    0,
    2,
    0,
    0,
    2,
    0,
    0,
    2,
    2,
    2,
    0,
    0,
    2,
    2,
    2,
    1,
    0,
    0,
    1,
    1,
    0,
    0,
    1,
    1,
    0,
    0,
    1,
    1,
    0,
    0,
    1,
    2,
    2,
    2,
    0,
    0,
    2,
    2,
    2,
    0,
    0,
    2,
    0,
    0,
    2,
    0,
    0,
    8,
    0,
    2,
    1,
    1,
    2,
    0,
    8,
]

Move = tuple[int, int]

STARTING_GRID = [NONE for _ in range(64)]

STARTING_GRID[27] = WHITE
STARTING_GRID[28] = BLACK
STARTING_GRID[35] = BLACK
STARTING_GRID[36] = WHITE

THREAD_POOL = ThreadPool(8)
INDICES = [i for i in range(64)]

DIRECTIONS = [
    (-1, 0),
    (1, 0),
    (0, -1),
    (0, 1),  
    (-1, -1),
    (-1, 1),
    (1, -1),
    (1, 1),
]  

INITAL_POSSIBLE_MOVES = set([
    (4,2), (5,3), (5,4), (4,5), (3, 5), (2, 4), (2, 3), (3, 2)
])

INITAL_FLIPPED_TILES = set([
    (3,3), (4,3), (4, 4), (3, 4)
])

class Grid:
    _grid: np.ndarray
    _valid_moves: set[Move] | None = None
    _team: int = NONE
    _possible_moves: set[Move]
    _flipped_tiles: set[Move]

    def __init__(self, copy=True):
        if copy:
            self._grid = np.array(STARTING_GRID, dtype=np.dtypes.ByteDType)
            self._possible_moves = INITAL_POSSIBLE_MOVES.copy()
            self._flipped_tiles = INITAL_FLIPPED_TILES.copy()

    def __str__(self) -> str:
        """
            Prettify the grid for printing
        """
        output = ""
        output += "   (0)(1)(2)(3)(4)(5)(6)(7)"
        row_int = 7
        output += "\n"
        for i in range(7, -1, -1):
            output += f"({row_int})"
            row_int -= 1
            for j in range(8):
                cell = self[(i, j)]

                if self._valid_moves and (i, j) in self._valid_moves and cell == NONE:
                    output += " " + TOKEN_MAP[-1] + " "
                else:
                    output += " " + TOKEN_MAP[cell] + " "
            output += "\n"

        return output

    def __getitem__(self, move: Move):
        # Return the disc at the given position

        if move[0] < 0 or move[0] > 7 or move[1] < 0 or move[1] > 7:
            return NONE

        return self._grid[(7 - move[0]) * 8 + move[1]]

    def __setitem__(self, move: Move, value: int):
        # Set the disc at the given position
        self._grid[(7 - move[0]) * 8 + move[1]] = value

    def _scan_direction(self, team: int, x: int, y: int, ox: int, oy: int):
        # Scan in the specified direction to see if its a valid move
        foundEnemy = False
        pos = (y + oy, x + ox)

        if self[pos] == team:
            return False

        while self[pos] != NONE:
            if self[pos] != team:
                foundEnemy = True

            if self[pos] == team:
                return foundEnemy

            pos = (pos[0] + oy, pos[1] + ox)

        return False

    def _is_valid(self, team: int, x: int, y: int):
        # Returns true if the move is valid

        for ox, oy in DIRECTIONS:
            if self._scan_direction(team, x, y, ox, oy):
                return True

        return False

    def get_valid_moves(self, team: int) -> set[Move]:
        """
        Returns all valid moves for a given team
        """
        if self._valid_moves is not None and self._team == team:
            return self._valid_moves

        valid_moves = set()


        def runner(move: Move):
            """
                Check if the move is valid
            """
            y, x = move

            if self[(y, x)] != NONE:
                return

            if not self._is_valid(team, x, y):
                return

            valid_moves.add((y, x))

        THREAD_POOL.map(runner, self._possible_moves)

        self._valid_moves = valid_moves
        self._team = team

        return valid_moves

    def _flip_pieces(self, team, x: int, y: int, ox: int, oy: int):
        """
            Flip all pieces in the given direction
        """
        tokens = []
        pos = (y + oy, x + ox)

        while self[pos] != NONE:
            if self[pos] != team:
                tokens.append(pos)
            else:
                for token in tokens:
                    self[token] = team
                return

            pos = (pos[0] + oy, pos[1] + ox)

    def make_move(self, team: int, move: Move) -> "Grid":
        """
            Make the given move
        """
        y, x = move

        self._possible_moves.remove(move)
        self._flipped_tiles.add(move)

        for ox, oy in DIRECTIONS:
            if self[y + oy, x + ox] == NONE and ox + x >= 0 and ox + x < 8 and oy + y >= 0 and oy + y < 8:
                self._possible_moves.add((y + oy, x + ox))

            self._flip_pieces(team, x, y, ox, oy)

        self[(y, x)] = team

        self._valid_moves = None

        return self

    def copy(self) -> "Grid":
        """
            Copy the grid to a new one
        """
        new_grid = Grid(copy=False)
        new_grid._grid = self._grid.copy()
        new_grid._possible_moves = self._possible_moves.copy()
        new_grid._flipped_tiles = self._flipped_tiles.copy()

        return new_grid

    @cache
    @staticmethod
    def eval_position(x: int, y: int, team: int) -> float:
        """ ""
        give more weights to important points
        """
        return WEIGHT_GRID[y * 8 + x]

    def eval_corner(self, x: int, y: int, team: int) -> float:
        """
            Weight cells around the corners more/less depending on who owns the corner
        """
        CORNER_POSITIVE = 6
        CORNER_NEGATIVE = -4

        if (y, x) in {(1, 0), (1, 1), (0, 1)}:
            return CORNER_POSITIVE if self[(0, 0)] == team else CORNER_NEGATIVE
        elif (y, x) in {(0, 6), (1, 6), (1, 7)}:
            return CORNER_POSITIVE if self[(0, 7)] == team else CORNER_NEGATIVE
        elif (y, x) in {(6, 6), (6, 7), (7, 6)}:
            return CORNER_POSITIVE if self[(7, 7)] == team else CORNER_NEGATIVE
        elif (y, x) in {(6, 0), (6, 1), (7, 1)}:
            return CORNER_POSITIVE if self[(7, 0)] == team else CORNER_NEGATIVE

        return 0

    def _get_stable_discs(self):
        """
            Calculate which discs are stable
        """
        stable_dir_count = [0 for _ in range(64)]

        for y,x in self._flipped_tiles:     

            if self[(y, x)] == NONE:
                continue
            color = self[(y, x)]
            
            count = 0
            for dx, dy in DIRECTIONS:
                cx, cy = x + dx, y + dy
                stable_in_dir = False
                while cx >= 0 and cx < 8 and cy >= 0 and cy < 8:
                    if self[(cy, cx)] != color:
                        break
                    cx += dx
                    cy += dy
                else:
                    # Reached edge without interruption — stable in this direction
                    stable_in_dir = True

                if stable_in_dir:
                    count += 1

            stable_dir_count[(7 - y) * 8 + x] = count

        return stable_dir_count

    def eval(self, team: int) -> float:
        """
        Evalutate the board state
        """
        white_scores = []
        black_scores = []

        stable_directions = self._get_stable_discs()

        def runner(m: Move):
            y, x = m
            i = (7 - y) * 8 + x

            if self[(y, x)] == NONE:
                return

            score = 0
            score += Grid.eval_position(x, y, team)
            score += self.eval_corner(x, y, team)
            score *= stable_directions[i] + 1

            if self[(y, x)] == WHITE:
                white_scores.append(score)
            else:
                black_scores.append(score)

        THREAD_POOL.map(runner, self._flipped_tiles)

        white_num = sum(white_scores)
        black_num = sum(black_scores)

        possible_team_moves = math.sqrt(len(self.get_valid_moves(team))) * 2
        possible_opponent_moves = math.sqrt(len(self.get_valid_moves(SWAP_TEAM[team]))) * 2

        if team == WHITE:
            score = white_num - black_num
        elif team == BLACK:
            score = black_num - white_num
        else:
            score = 0

        score += possible_team_moves - possible_opponent_moves
        return score


if __name__ == "__main__":
    grid = Grid()
    grid._grid = np.array([
        1, 1, 1, 1, 1, 1, 1, 1,
        1, 0, 0, 1, 0, 0, 0, 1,
        1, 0, 0, 1, 0, 0, 0, 1,
        1, 0, 0, 1, 0, 1, 0, 1,
        1, 0, 0, 1, 0, 0, 0, 1,
        1, 0, 0, 1, 0, 0, 0, 1,
        1, 0, 0, 1, 0, 0, 0, 1,
        1, 1, 1, 1, 1, 1, 1, 1,
    ])
    stable_discs = grid._get_stable_discs()

    for y in range(8):
        for x in range(8):
            i = (7 - y) * 8 + x

            print(f"{stable_discs[i]} ", end="")

        print()