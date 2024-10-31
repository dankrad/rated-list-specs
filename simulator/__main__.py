import rustworkx as rx
import random
import time
import logging
from utils import int_to_bytes
from simulator import SimulatedNode
from node import Root, NodeId, compute_node_score
from attack import SybilAttack, DefunctSubTreeAttack, BalancingAttack, EclipseAttack
import numpy as np
import os
import json
import sys

# TODO: change this to not be a global variable
GRAPH_JSON_FILE = "./data/random_graph.json"
NUM_NODES_RANDOM = 10000
DEGREE = 50
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


def acyclic_graph_defunct_subtree_test(querying_strategy="high"):
    logging.info("\nAcyclic Graph Defunct Sub Tree Attack:\n")
    # construct an acyclic subtree
    acyclic_graph = construct_acyclic_graph(DEGREE)

    # mark an entire subtree offline
    attack = DefunctSubTreeAttack(
        graph=acyclic_graph, defunct_sub_root=1, parent_sub_root=0
    )

    # initialize a simulated node with rated list node(root node of
    # rated list tree) as root node of the acyclic graph
    sim_node = SimulatedNode(graph=acyclic_graph, attack=attack, binding_vertex=0)

    block_root = Root(int_to_bytes(0))

    # query for samples and get a report out
    report = sim_node.query_samples(block_root, querying_strategy)

    return sim_node.print_report(report)


def random_graph_defunct_subtree_test(querying_strategy="high"):
    logging.info("\nRandom Graph Defunct Sub Tree Attack:\n")

    # construct a random graph
    erdos_renyi_graph = rx.undirected_gnp_random_graph(
        NUM_NODES_RANDOM, DEGREE / NUM_NODES_RANDOM, seed=100
    )

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
    report = sim_node.query_samples(block_root, querying_strategy)

    return sim_node.print_report(report)


def sybil_poisoning_test(graph, rate: float):
    logging.info(f"\n\nSybil Attack: Rate {rate}\n")
    sybil_attack = SybilAttack(graph=graph, sybil_rate=rate)

    sim_node = SimulatedNode(graph=graph, attack=sybil_attack)

    block_root = Root(int_to_bytes(0))

    for threshold in np.arange(0.9, 0.0, -0.1):
        for strategy in ["high", "low", "random"]:
            report = sim_node.query_samples(
                block_root, querying_strategy, is_rated_list=True, threshold=threshold
            )
            random_report = sim_node.query_samples(
                block_root, querying_strategy, is_rated_list=False, threshold=threshold
            )

            sim_node.print_report(report)
            sim_node.print_report(random_report)


"""
There are various interpretations of an eclipse attack.
1. The attack can be directly on the rated list node. This would hardly provide any
   benefit since the node
2. The attack can be on a node in the network to bring down it's score or partition
   it's view of the network
3. The attack can be made on another malicious node to bring down it's score
   and therefore lessen the obligation of serving samples.
"""


def eclipse_attack_test(graph, rate: int, querying_strategy="high"):
    logging.debug(f"\nEclipse Attack: Rate {rate}\n")

    # select a node to eclipse
    rnd_node = random.choice(graph.nodes())
    eclipse_root_node = EclipseAttack(
        graph=graph, compromised_node=rnd_node, eclipse_rate=rate
    )

    # Eclipse the root node itself by setting the binding vertex the same as the compromised node
    # sim_node = SimulatedNode(
    #     graph=erdos_renyi_graph, attack=eclipse_root_node, binding_vertex=rnd_node
    # )

    # Eclipse a random node by not setting the binding vertex the same as the compromised node
    sim_node = SimulatedNode(graph=graph, attack=eclipse_root_node)

    block_root = Root(int_to_bytes(0))

    report = sim_node.query_samples(block_root, querying_strategy)

    eclipse_score = compute_node_score(
        sim_node.dht, block_root, NodeId(int_to_bytes(rnd_node))
    )

    logging.info(f"Score of the eclipsed node: {eclipse_score}")

    return sim_node.print_report(report)


def balancing_attack(graph, querying_strategy="high"):
    logging.info("\nBalancing Attack:\n")

    # select a root node for the balancing attack
    root_node = random.choice(graph.nodes())

    balance_attack = BalancingAttack(graph=graph, root_node=root_node)

    sim_node = SimulatedNode(
        graph=graph, attack=balance_attack, binding_vertex=root_node
    )

    block_root = Root(int_to_bytes(0))

    report = sim_node.query_samples(block_root, querying_strategy)

    sim_node.print_report(report)


# def graph_init():
#     if os.path.exists("./data/random_graph.json"):
#         logging.info("loading graph from json file")
#         # with open(GRAPH_JSON_FILE, "r") as file:
#             # data = json.load(file)
#         graph = rx.from_node_link_json_file(GRAPH_JSON_FILE)
#         print(graph.nodes())

#     else:
#         logging.info("graph not found generating graph")
#         graph = rx.undirected_gnp_random_graph(
#             NUM_NODES_RANDOM, DEGREE / NUM_NODES_RANDOM
#         )
#         json_str = rx.node_link_json(graph)
#         with open(GRAPH_JSON_FILE, "w") as file:
#             file.write(json_str)
#         return graph


def graph_init():
    if os.path.isfile(GRAPH_JSON_FILE):
        logging.info("loading graph from json file")
        graph = rx.from_node_link_json_file(GRAPH_JSON_FILE, node_attrs=de_node_data)
    else:
        logging.info("graph not found generating graph")
        graph = rx.undirected_gnp_random_graph(
            NUM_NODES_RANDOM, DEGREE / NUM_NODES_RANDOM
        )
        rx.node_link_json(graph, path=GRAPH_JSON_FILE, node_attrs=ser_node_data)
    return graph


def de_node_data(data):
    return int(data["value"])


def ser_node_data(data):
    mydict = {}
    mydict["value"] = str(data)
    return mydict


def main():
    graph = graph_init()

    start_time = time.time()

    logging.info(f"number of nodes in the network={NUM_NODES_RANDOM}")
    logging.info(f"connection degree={DEGREE}")

    # acyclic_graph_defunct_subtree_test()
    # random_graph_defunct_subtree_test()

    for sybil_rate in np.arange(0.1, 1.0, 0.1):
        sybil_poisoning_test(graph, sybil_rate)

    # eclipse_attack_test(0.5)

    # balancing_attack()

    logging.debug(f"the simulator ran for {time.time()-start_time}s")


if __name__ == "__main__":
    run_num = sys.argv[1]
    filename = "log_file_" + str(run_num)

    print(filename)

    logging.basicConfig(
        filename="debug.log",
        filemode="w",
        level=logging.DEBUG,
        format="%(levelname)s - %(message)s",
    )

    main()
