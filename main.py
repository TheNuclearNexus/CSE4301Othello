import copy
from functools import partial
import math
from multiprocessing.pool import ThreadPool
from threading import Thread
import time
from ai import ABORT, SWAP_TEAM, Node, evaluate
from colors import Colors
from grid import BLACK, WHITE, Grid, Move


grid = Grid()

TEAM_MAP = {"W": WHITE, "B": BLACK}

PLAYER_TEAM = TEAM_MAP[input("Are you W or B: ").upper()]
BOT_TEAM = SWAP_TEAM[PLAYER_TEAM]
print(f"\nBot is {BOT_TEAM}")

BOT_FIRST = BOT_TEAM == BLACK


def do_player_move():
    global grid
    valid_moves = grid.get_valid_moves(PLAYER_TEAM)
    print("Valid moves are", valid_moves)
    while True:
        action = input("Whats your move (i,j) or back: ")

        if action == "back":
            grid = MOVES.pop()
            print("--- New Grid ---")
            print(grid)
            do_player_move()
            return

        i, j = map(int, action.split(","))

        if (i, j) in valid_moves:
            MOVES.append(grid)
            grid = grid.copy().make_move(PLAYER_TEAM, (i, j))
            break
        else:
            print(f"\n{Colors.RED}Invalid move{Colors.END}\n")

    grid.get_valid_moves(BOT_TEAM)
    print("--- Player Move ---")
    print(grid)


grid.get_valid_moves(BOT_TEAM if BOT_FIRST else PLAYER_TEAM)
print("--- Initial Board ---")
print(grid)

ROUND = 0
PLY = 7

MOVES = []

THREAD_POOL = ThreadPool(8)

MAX_TIME = 120

while True:
    if not BOT_FIRST:
        do_player_move()

    possible_moves = grid.get_valid_moves(BOT_TEAM)

    move_nodes: list[Node] = [
        Node(grid.copy().make_move(BOT_TEAM, move), BOT_TEAM, [])
        for move in possible_moves
    ]

    def runner(root: Node, ply: int):
        evaluate(root, ply, -math.inf, math.inf, True)

    start_time = time.time()

    best_moves: list[Node] = []

    for i in range(2, 50):
        if time.time() - start_time > MAX_TIME:
            break
        # print("ply =", i)

        t = Thread(target=lambda: THREAD_POOL.map(partial(runner, ply=i), move_nodes))
        t.start()

        while t.is_alive():
            cur_time = time.time() - start_time
            print(f"ply = {i} | {cur_time:.3f}s", end="\r", flush=True)
            time.sleep(0.05)
            if cur_time > MAX_TIME:
                ABORT.signal()

        if ABORT.is_signalled():
            print("\nABORTED")
            ABORT.reset()
            break

        move_nodes.sort(key=lambda m: m.weight)

        new_node = Node(move_nodes[-1].grid.copy(), move_nodes[-1].acting_team, [])
        new_node.weight = move_nodes[-1].weight

        best_moves.append(new_node)

    print("\n")
    print(list(map(lambda m: m.weight, best_moves)))
    best_moves = sorted(best_moves, key=lambda m: m.weight)

    if len(best_moves) > 0:
        grid = best_moves[-1].grid
        grid.get_valid_moves(PLAYER_TEAM)

        print("--- Bot Move ---")
        print(grid)

    if BOT_FIRST:
        do_player_move()

    ROUND += 1
