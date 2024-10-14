import rustworkx as rx
import random
import time

from utils import int_to_bytes
from simulator import SimulatedNode
from node import Root, NodeId, compute_node_score
from attack import SybilAttack, AcyclicTestAttack, BalancingAttack, EclipseAttack


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

    # acyclic_test_attack = AcyclicTestAttack(
    #     graph=acyclic_graph, defunct_sub_root=1, parent_sub_root=0
    # )
    # sybil_attack = SybilAttack(graph=erdos_renyi_graph, sybil_rate=0.5)

    rnd_node = random.choice(erdos_renyi_graph.nodes())
    eclipse_root_node = EclipseAttack(erdos_renyi_graph, rnd_node, 0.5)

    # balance_attack = BalancingAttack(
    #     graph=erdos_renyi_graph,
    #     root_node=root_node
    # )

    # sim_node = SimulatedNode(
    #     graph=acyclic_graph, attack=acyclic_test_attack, binding_vertex=0
    # )
    # sim_node = SimulatedNode(graph=erdos_renyi_graph, attack=sybil_attack)
    # sim_node=SimulatedNode(
    #     graph=erdos_renyi_graph, attack=balance_attack, binding_vertex=root_node
    # )
    # Eclipse the root node itself by setting the binding vertex the same as the compromised node
    # sim_node = SimulatedNode(
    #     graph=erdos_renyi_graph, attack=eclipse_root_node, binding_vertex=rnd_node
    # )
    # Eclipse a random node by not setting the binding vertex the same as the compromised node
    sim_node = SimulatedNode(graph=erdos_renyi_graph, attack=eclipse_root_node)

    block_root = Root(int_to_bytes(0))

    sim_node.query_samples(block_root)

    eclipse_score = compute_node_score(
        sim_node.dht, block_root, NodeId(int_to_bytes(rnd_node))
    )
    print(f"Score of the eclipsed node: {eclipse_score}")
    print(f"the simulator ran for {time.time()-start_time}s")


if __name__ == "__main__":
    main()
