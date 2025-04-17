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
    global ROUND

    # Get all valid moves for the player
    valid_moves = grid.get_valid_moves(PLAYER_TEAM)
    if len(valid_moves) == 0:
        return
    
    print("Valid moves are", valid_moves)
    while True:
        action = input("Whats your move (i,j) or back: ")

        if action == "back":
            # Roll back the grid to a previous move
            grid = MOVES.pop()
            print("--- New Grid ---")
            print(grid)
            ROUND -= 1
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
    print(f"--- Player Move #{ROUND} ---")
    print(grid)
    print("Score:", grid.eval(PLAYER_TEAM))


grid.get_valid_moves(BOT_TEAM if BOT_FIRST else PLAYER_TEAM)
print("--- Initial Board ---")
print(grid)

ROUND = 0
PLY = 7

MOVES = []

MOVE_THREAD_POOL = ThreadPool(16)

MAX_TIME = 120

while True:
    if not BOT_FIRST:
        do_player_move()

    possible_moves = grid.get_valid_moves(BOT_TEAM)

    # Create empty nodes for each possible move
    move_nodes: list[Node] = [
        Node(grid.copy().make_move(BOT_TEAM, move), BOT_TEAM, [], move=move)
        for move in possible_moves
    ]

    
    def runner(root: Node, ply: int):
        """Evaluates a given node to a given ply"""
        evaluate(root, ply, -math.inf, math.inf, True)

    start_time = time.time()

    best_move: Node|None = None

    # Use smaller plys early on in the game
    if ROUND <= 7:
        max_ply = 6
    elif ROUND <= 10:
        max_ply = 8
    else:
        max_ply = 10

    for i in range(2, max_ply + 1):
        # If we're past the maximum amount of time
        # break out
        if time.time() - start_time > MAX_TIME:
            break

        # Start the thread pool for each move
        t = Thread(target=lambda: MOVE_THREAD_POOL.map(partial(runner, ply=i), move_nodes))
        t.start()

        while t.is_alive():
            cur_time = time.time() - start_time
            print(f"ply = {i} | {cur_time:.3f}s", end="\r", flush=True)
            time.sleep(0.05)

            # Time is up, abort and return
            if cur_time > MAX_TIME:
                ABORT.signal()

        if ABORT.is_signalled():
            print("\nABORTED")
            ABORT.reset()
            break

        move_nodes.sort(key=lambda m: m.weight)

        new_node = Node(move_nodes[-1].grid.copy(), move_nodes[-1].acting_team, [])
        new_node.weight = move_nodes[-1].weight
        new_node.move = move_nodes[-1].move

        best_move = new_node

    if best_move:
        grid = best_move.grid
        grid.get_valid_moves(PLAYER_TEAM)

        print(f"----- Bot Move #{ROUND} -----")
        print(best_move.move)
        print(grid)
        print("Score:", grid.eval(BOT_TEAM))

    if BOT_FIRST:
        do_player_move()

    ROUND += 1
