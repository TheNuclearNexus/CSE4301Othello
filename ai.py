from dataclasses import dataclass, field
import math
from grid import BLACK, NONE, SWAP_TEAM, WHITE, Grid, Move


@dataclass
class Node:
    grid: Grid
    acting_team: int
    children: list["Node"]
    _initialized: bool = False
    move: Move = field(default=(0,0))

    weight: float = field(init=False, default=0)

    def eval(self) -> float:
        self.weight = self.grid.eval(self.acting_team)
        return self.weight

    def set_children(self):
        if self._initialized:
            return
        
        self._initialized = True
        for move in self.grid.get_valid_moves(self.acting_team):
            self.children.append(
                Node(
                    self.grid.copy().make_move(self.acting_team, move),
                    SWAP_TEAM[self.acting_team],
                    [],
                )
            )

class AbortSignal:
    _flag: bool = False

    def signal(self,):
        self._flag = True

    def reset(self):
        self._flag = False

    def is_signalled(self):
        return self._flag


ABORT = AbortSignal()

def evaluate(
    node: Node, depth: int, alpha: float, beta: float, maximizing: bool
) -> float:
    """
        Apply the alphabeta pruning algorithm to the node
    """
    if ABORT.is_signalled():
        return 0

    if depth == 0:
        return node.eval()

    node.set_children()

    if len(node.children) == 0:
        return node.eval()
    

    if maximizing:
        value = -math.inf
        for child in node.children:
            value = max(value, evaluate(child, depth - 1, alpha, beta, False))

            if value > beta:
                break

            alpha = max(value, alpha)

        node.weight = value
    else:
        value = math.inf
        for child in node.children:
            value = min(value, evaluate(child, depth - 1, alpha, beta, True))

            if value < alpha:
                break

            beta = min(value, beta)

        node.weight = value

    return node.weight