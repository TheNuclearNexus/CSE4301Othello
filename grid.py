from multiprocessing.pool import ThreadPool
from threading import Thread
from typing import Literal, Union

from colors import Colors

NONE = 0
WHITE = 1  # ⚪
BLACK = 2  # ⚫

SWAP_TEAM = [NONE, BLACK, WHITE]
TOKEN_MAP = {
    NONE: "◯",
    WHITE: "⬤",
    BLACK: f"{Colors.RED}⬤{Colors.END}",
    -1: f"{Colors.GREEN}◯{Colors.END}",
}

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
    (0, 1),  # up, down, left, right
    (-1, -1),
    (-1, 1),
    (1, -1),
    (1, 1),
]  # diagonals


class Grid:
    _grid: list[int]
    _valid_moves: set[Move] | None = None
    _team: int = NONE

    def __init__(self, copy=True):
        if copy:
            self._grid = STARTING_GRID.copy()

    def __str__(self) -> str:
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
        if move[0] < 0 or move[0] > 7 or move[1] < 0 or move[1] > 7:
            return NONE

        return self._grid[(7 - move[0]) * 8 + move[1]]

    def __setitem__(self, move: Move, value: int):
        self._grid[(7 - move[0]) * 8 + move[1]] = value

    def _scan_direction(self, team: int, x: int, y: int, ox: int, oy: int):
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

        def runner(i: int):
            y = i // 8
            x = i % 8

            if self[(y, x)] != NONE:
                return

            if not self._is_valid(team, x, y):
                return

            valid_moves.add((y, x))

        THREAD_POOL.map(runner, INDICES)

        self._valid_moves = valid_moves
        self._team = team

        return valid_moves

    def _flip_pieces(self, team, x: int, y: int, ox: int, oy: int):
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
        y, x = move

        for ox, oy in DIRECTIONS:
            self._flip_pieces(team, x, y, ox, oy)

        self[(y, x)] = team

        self._valid_moves = None

        return self

    def copy(self) -> "Grid":
        new_grid = Grid(copy=False)
        new_grid._grid = self._grid.copy()

        return new_grid

    def eval_position(self, x: int, y: int, team: int) -> float:
        """ ""
        give more weights to important points
        """
        return WEIGHT_GRID[y * 8 + x]

    def eval_corner(self, x: int, y: int, team: int) -> float:
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
        stable_dir_count = [0 for _ in range(64)]

        for y in range(8):
            for x in range(8):
                if self[(y, x)] not in ("B", "W"):
                    continue
                color = self[(y, x)]
                count = 0
                for dx, dy in DIRECTIONS:
                    cx, cy = y + dx, x + dy
                    stable_in_dir = False
                    while cx >= 0 and cx < 8 and cy >= 0 and cy < 8:
                        if self[(y, x)] != color:
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

        def runner(i: int):
            y = i // 8
            x = i % 8

            if self[(y, x)] == NONE:
                return

            score = 0
            score += self.eval_position(x, y, team)
            score += self.eval_corner(x, y, team)
            score *= stable_directions[i] / 8 + 1

            if self[(y, x)] == WHITE:
                white_scores.append(score)
            else:
                black_scores.append(score)

        THREAD_POOL.map(runner, INDICES)

        white_num = sum(white_scores)
        black_num = sum(black_scores)

        possible_team_moves = len(self.get_valid_moves(team)) * 4
        possible_opponent_moves = len(self.get_valid_moves(SWAP_TEAM[team])) * 4

        if team == WHITE:
            score = white_num - black_num
        elif team == BLACK:
            score = black_num - white_num
        else:
            score = 0

        score += possible_team_moves - possible_opponent_moves
        return score


print(Grid())
