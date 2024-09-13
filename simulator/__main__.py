import networkx as nx
from node import NodeProfile
from simulator import SimulatedNode
from utils import gen_node_id


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
    # erdos_renyi = nx.erdos_renyi_graph(200, 0.3)
    # path_graph = nx.path_graph(5)

    sim_node = SimulatedNode(acyclic_graph, 0)
    # sim_node = SimulatedNode(erdos_renyi)
    # sim_node = SimulatedNode(path_graph)
    sim_node.construct_tree()

    offline_profile = NodeProfile.OFFLINE

    # mark all descendants children of a particular level 1 node offline
    defunct_sub_tree_root = list(sim_node.dht.nodes[sim_node.own_id].children)[0]

    def random_selector(node_id):
        # if node_id == defunct_sub_tree_root:
        # return True

        if node_id in sim_node.dht.nodes[defunct_sub_tree_root].children:
            return True

        # go one more level into the rated list
        for child in sim_node.dht.nodes[defunct_sub_tree_root].children:
            if node_id in sim_node.dht.nodes[child].children:
                return True

        return False

    sim_node.bind(offline_profile, random_selector)

    # TODO: use block.py to simulate block level logic
    block_root = gen_node_id()
    evicted_nodes = set()

    # using a random block root just for initial testing
    for sample in range(128):
        # NOTE: technically all samples must be in the mapping. we just need enough nodes in the network
        if sample not in sim_node.dht.sample_mapping:
            print("No record of nodes that serve sample: " + str(sample))
            continue

        filtered_nodes = sim_node.filter_nodes(block_root, sample)
        all_nodes = sim_node.dht.sample_mapping[sample]

        # just pick the first node from the list
        # TODO: come up with different startegies for this
        if len(filtered_nodes) > 0:
            evicted_nodes.update(all_nodes - filtered_nodes)
            node_id = filtered_nodes.pop()
        else:
            print("No good nodes found for sample")
            continue

        sim_node.request_sample(node_id, block_root, sample)
        sim_node.process_requests()

    count = 0
    # print(sim_node.dht)
    for evicted in evicted_nodes:
        if sim_node.is_ancestor(evicted, defunct_sub_tree_root):
            count += 1
        else:
            print(evicted, sim_node.dht.nodes[evicted].parents)

    print(f"{count}/{len(evicted_nodes)} evicted nodes are descendants of the subtree")


if __name__ == "__main__":
    main()
