from dascore import get_custody_columns
from node import NodeProfile
import networkx as nx
from simulator import SimulatedNode
import random as rn
from utils import gen_node_id


def main():
    erdos_renyi = nx.erdos_renyi_graph(200, 0.3)
    sim_node = SimulatedNode(erdos_renyi)
    sim_node.construct_tree()

    offline_profile = NodeProfile(False, False, True)

    # randomly assign half of the nodes as malicious
    def random_selector():
        return True  # bool(rn.getrandbits(1))

    sim_node.bind(offline_profile, random_selector)

    # using a random block root just for initial testing
    sim_node.request_sample(gen_node_id(), list(range(64)))
    sim_node.process_requests()

    print(sim_node.dht)


if __name__ == "__main__":
    main()
