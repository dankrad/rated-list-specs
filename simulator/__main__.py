import rustworkx as rx
import random
import time

from utils import int_to_bytes
from simulator import SimulatedNode
from node import Root, NodeId, compute_node_score
from attack import SybilAttack, DefunctSubTreeAttack, BalancingAttack, EclipseAttack


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


def acyclic_graph_defunct_subtree_test():
    print("\nAcyclic Graph Defunct Sub Tree Attack:\n")
    # construct an acyclic subtree
    acyclic_graph = construct_acyclic_graph(50)

    # mark an entire subtree offline
    attack = DefunctSubTreeAttack(
        graph=acyclic_graph, defunct_sub_root=1, parent_sub_root=0
    )

    # initialize a simulated node with rated list node(root node of
    # rated list tree) as root node of the acyclic graph
    sim_node = SimulatedNode(
        graph=acyclic_graph, attack=attack, binding_vertex=0)

    block_root = Root(int_to_bytes(0))

    # query for samples and get a report out
    report = sim_node.query_samples(block_root)


def random_graph_defunct_subtree_test():
    print("\nRandom Graph Defunct Sub Tree Attack:\n")
    # construct a random graph
    erdos_renyi_graph = rx.undirected_gnp_random_graph(10000, 0.015)

    # select the rated list node (root node of rated list tree)
    # and a child of the rated list node
    root_node = random.choice(erdos_renyi_graph.nodes())
    child_node = random.choice(erdos_renyi_graph.neighbors(root_node))

    # mark an entire subtree offline
    attack = DefunctSubTreeAttack(
        graph=erdos_renyi_graph, defunct_sub_root=child_node, parent_sub_root=root_node
    )

    # initialize a simulated node with the rated list node as seleted before
    sim_node = SimulatedNode(
        graph=erdos_renyi_graph, attack=attack, binding_vertex=root_node
    )

    block_root = Root(int_to_bytes(0))

    # query for samples and get a report out
    report = sim_node.query_samples(block_root)


def sybil_poisoning_test(rate: int):
    print(f"\nSybil Attack: Rate {rate}\n")
    erdos_renyi_graph = rx.undirected_gnp_random_graph(10000, 0.015)

    sybil_attack = SybilAttack(graph=erdos_renyi_graph, sybil_rate=rate)

    sim_node = SimulatedNode(graph=erdos_renyi_graph, attack=sybil_attack)

    block_root = Root(int_to_bytes(0))

    report = sim_node.query_samples(block_root)


# There are various interpretations of an eclipse attack.
# 1. The attack can be directly on the rated list node. This would hardly provide any
#    benefit since the node
# 2. The attack can be on a node in the network to bring down it's score or partition
#    it's view of the network
# 3. The attack can be made on another malicious node to bring down it's score
#    and therefore lessen the obligation of serving samples.
def eclipse_attack_test(rate):
    print(f"\nEclipse Attack: Rate {rate}\n")
    erdos_renyi_graph = rx.undirected_gnp_random_graph(10000, 0.015)

    # select a node to eclipse
    rnd_node = random.choice(erdos_renyi_graph.nodes())
    eclipse_root_node = EclipseAttack(
        graph=erdos_renyi_graph, compromised_node=rnd_node, eclipse_rate=rate
    )

    # Eclipse the root node itself by setting the binding vertex the same as the compromised node
    # sim_node = SimulatedNode(
    #     graph=erdos_renyi_graph, attack=eclipse_root_node, binding_vertex=rnd_node
    # )

    # Eclipse a random node by not setting the binding vertex the same as the compromised node
    sim_node = SimulatedNode(graph=erdos_renyi_graph, attack=eclipse_root_node)

    block_root = Root(int_to_bytes(0))

    report = sim_node.query_samples(block_root)

    eclipse_score = compute_node_score(
        sim_node.dht, block_root, NodeId(int_to_bytes(rnd_node))
    )

    print(f"Score of the eclipsed node: {eclipse_score}")


def balancing_attack():
    print("\nBalancing Attack:\n")
    erdos_renyi_graph = rx.undirected_gnp_random_graph(10000, 0.015)

    # select a root node for the balancing attack
    root_node = random.choice(erdos_renyi_graph.nodes())

    balance_attack = BalancingAttack(
        graph=erdos_renyi_graph, root_node=root_node)

    sim_node = SimulatedNode(
        graph=erdos_renyi_graph, attack=balance_attack, binding_vertex=root_node
    )

    block_root = Root(int_to_bytes(0))

    report = sim_node.query_samples(block_root)


def main():
    start_time = time.time()

    acyclic_graph_defunct_subtree_test()
    random_graph_defunct_subtree_test()

    sybil_poisoning_test(0.3)
    sybil_poisoning_test(0.4)
    sybil_poisoning_test(0.5)
    sybil_poisoning_test(0.6)
    sybil_poisoning_test(0.7)
    sybil_poisoning_test(0.8)
    sybil_poisoning_test(0.9)

    eclipse_attack_test(0.5)

    balancing_attack()

    print(f"the simulator ran for {time.time()-start_time}s")


if __name__ == "__main__":
    main()
