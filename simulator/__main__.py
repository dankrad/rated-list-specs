import rustworkx as rx
from simulator import SimulatedNode, gen_node_id
import time



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

    acyclic_graph = construct_acyclic_graph(50)
    # erdos_renyi_graph = rx.undirected_gnp_random_graph(10000, 0.015)

    sim_node = SimulatedNode(acyclic_graph, 0)
    # sim_node = SimulatedNode(erdos_renyi_graph)

    sim_node.construct_tree()
    
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

    print(f"{len(evicted_nodes)} evicted nodes")
    print(f"the simulator ran for {time.time()-start_time}s")


if __name__ == "__main__":
    main()
