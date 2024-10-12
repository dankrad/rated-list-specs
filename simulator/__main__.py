import rustworkx as rx
import time

from utils import int_to_bytes
from simulator import SimulatedNode
from node import Root
from attack import SybilAttack


# mimics a rated list tree without any cycles.
def construct_acyclic_graph(degree: int = 5) -> rx.PyGraph:
    G = rx.PyGraph()

    current_node_count = 1
    G.add_node(0)

    for i in range(degree):
        G.add_node(current_node_count)
        G.add_edge(0, current_node_count, None)
        level_1 = current_node_count
        current_node_count += 1

        for i in range(degree):
            G.add_node(current_node_count)
            G.add_edge(level_1, current_node_count, None)
            level_2 = current_node_count
            current_node_count += 1

            for i in range(degree):
                G.add_node(current_node_count)
                G.add_edge(level_2, current_node_count, None)
                current_node_count += 1

    return G


def main():
    start_time = time.time()

    # acyclic_graph = construct_acyclic_graph(50)
    erdos_renyi_graph = rx.undirected_gnp_random_graph(10000, 0.015)

    # acyclic_test_attack = AcyclicAttack(graph=graph, defunct_sub_root=None)
    sybil_attack = SybilAttack(graph=erdos_renyi_graph, sybil_rate=0.5)

    # sim_node = SimulatedNode(graph=acyclic_graph, attack=acyclic_test_attack, binding_vertex=0)
    sim_node = SimulatedNode(graph=erdos_renyi_graph, attack=sybil_attack)

    block_root = Root(int_to_bytes(0))

    sim_node.query_samples(block_root)

    print(f"the simulator ran for {time.time()-start_time}s")


if __name__ == "__main__":
    main()
