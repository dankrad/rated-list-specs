from node import NodeProfile
import networkx as nx
from simulator import SimulatedNode
from utils import gen_node_id
import matplotlib.pyplot as plt


# mimics a rated list tree without any cycles.
def construct_acyclic_graph(degree: int = 5) -> nx.Graph:
    G = nx.Graph()

    current_node_count = 1

    for level_1 in range(degree):
        G.add_edge(0, current_node_count)
        level_1 = current_node_count
        current_node_count += 1

        for i in range(degree):
            G.add_edge(level_1, current_node_count)
            level_2 = current_node_count
            current_node_count += 1

            for i in range(degree):
                G.add_edge(level_2, current_node_count)
                current_node_count += 1

    return G


def main():
    acyclic_graph = construct_acyclic_graph(50)
    # erdos_renyi = nx.erdos_renyi(20000, 0.3)

    sim_node = SimulatedNode(acyclic_graph)
    sim_node.construct_tree()

    offline_profile = NodeProfile(False, False, True)

    # randomly assign half of the nodes as malicious
    def random_selector(node_id):
        level1_child = sim_node.dht.nodes[sim_node.own_id].children[0]
        if node_id in sim_node.dht.nodes[level1_child].children:
            return True

        return False

    sim_node.bind(offline_profile, random_selector)

    # using a random block root just for initial testing
    for sample in range(128):
        block_root = gen_node_id()

        # FIXME: technically all samples must be in the mapping. we just need enough nodes in the network
        if sample not in sim_node.dht.sample_mapping:
            print("No record of nodes that serve sample: " + str(sample))
            continue

        nodes_with_sample = sim_node.filter_nodes(block_root, sample)

        # just pick the first node from the list
        # TODO: come up with different startegies for this
        node_id = nodes_with_sample.pop()

        sim_node.request_sample(node_id, block_root, sample)
        sim_node.process_requests()

    # print(sim_node.dht)


if __name__ == "__main__":
    main()
