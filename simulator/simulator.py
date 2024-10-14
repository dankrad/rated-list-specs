import rustworkx as rx
import random as rn
import queue
from dataclasses import dataclass
from collections import deque

# Project specific
from attack import AttackVec
import node as rl_node
from utils import int_to_bytes, bytes_to_int
from node import (
    DATA_COLUMN_SIDECAR_SUBNET_COUNT,
    MAX_CHILDREN,
    NodeId,
    SampleId,
    Root,
    MAX_TREE_DEPTH,
    RatedListData,
    NodeRecord,
)


@dataclass
class RequestQueueItem:
    node_id: NodeId
    sample_id: SampleId
    block_root: Root


class SimulatedNode:
    def __init__(
        self, graph: rx.PyGraph, attack: AttackVec, binding_vertex: int = None
    ):
        self.graph = graph
        self.request_queue = queue.Queue()
        self.attack = attack

        # calculate average degree of the graph
        sum = 0
        for node in self.graph.nodes():
            sum = sum + self.graph.degree(self.graph[node])

        print("Average Degree:", sum / len(self.graph.nodes()))

        # map rated list node to one of the graph vertices
        if binding_vertex is None:
            binding_vertex = rn.choice(self.graph.node_indices())

        self.dht = RatedListData(
            NodeId(int_to_bytes(binding_vertex)), {}, {}, {})
        self.dht.nodes[self.dht.own_id] = NodeRecord(
            self.dht.own_id, set(), set())

        print("mapped rated list node to graph vertice " + str(binding_vertex))

        self._construct_tree()

        print("constructed the rated list")

        self.attack.setup_attack()

        print("initialized the attack vector")

    def filter_nodes(self, block_root: Root, sample: SampleId):
        return rl_node.filter_nodes(self.dht, block_root, sample)

    def request_sample(self, node_id: NodeId, block_root: Root, sample: SampleId):
        print("Requesting samples from", node_id)

        rl_node.on_request_score_update(self.dht, block_root, node_id, sample)
        self.request_queue.put(
            RequestQueueItem(node_id=node_id, sample_id=sample,
                             block_root=block_root)
        )

    def get_peers(self, node_id: NodeId):
        peers = []

        random_neighbors = list(self.graph.neighbors(bytes_to_int(node_id)))

        rn.shuffle(random_neighbors)

        for i, peer_id in enumerate(random_neighbors):
            if i >= MAX_CHILDREN:
                break

            peer_id_bytes = NodeId(int_to_bytes(peer_id))
            peers.append(peer_id_bytes)
            rl_node.add_samples_on_entry(self.dht, peer_id_bytes)
        rl_node.on_get_peers_response(self.dht, node_id, peers)

    def process_requests(self):
        while not self.request_queue.empty():
            request: RequestQueueItem = self.request_queue.get()

            if not self.attack.should_respond(bytes_to_int(request.node_id)):
                print("Rejected sample request", request)
                continue

            rl_node.on_response_score_update(
                self.dht,
                block_root=request.block_root,
                node_id=request.node_id,
                sample_id=request.sample_id,
            )

    def _construct_tree(self):
        print("constructing the rated list tree from the graph")

        # iterative BFS approach to find peers
        # where max_tree_depth is parametrised
        queue = deque([(self.dht.own_id, 1)])

        while queue:
            current_node_id, current_level = queue.popleft()

            if current_level >= MAX_TREE_DEPTH:
                continue

            self.get_peers(current_node_id)

            for child_id in self.dht.nodes[current_node_id].children:
                # no point adding to the list if we are not gonna use the item
                if (current_level + 1) < MAX_TREE_DEPTH:
                    queue.append((child_id, current_level + 1))

    def is_ancestor(self, grand_child: NodeId, check_ancestor: NodeId) -> bool:
        # all nodes are children(grand or great grand
        # until tree depth) of root node
        if check_ancestor == self.dht.own_id:
            return True

        if check_ancestor == grand_child:
            return True

        if check_ancestor in self.dht.nodes[grand_child].parents:
            return True

        # assuming the grand_child is at the last
        # level check grand parents(level 1)
        for parent in self.dht.nodes[grand_child].parents:
            if check_ancestor in self.dht.nodes[parent].parents:
                return True

            # if our assumption is wrong the parents are the root node itself
            if parent == self.dht.own_id:
                return False

        return False

    def query_samples(self, block_root: Root):
        evicted_nodes = set()
        # using a random block root just for initial testing
        for sample in range(DATA_COLUMN_SIDECAR_SUBNET_COUNT):
            # NOTE: technically all samples must be in the mapping.
            # we just need enough nodes in the network
            if sample not in self.dht.sample_mapping:
                print("No record of nodes that serve sample: " + str(sample))
                continue

            filtered_nodes = rl_node.filter_nodes(self.dht, block_root, sample)

            all_nodes = self.dht.sample_mapping[sample]

            # just pick the first node from the list
            # TODO: come up with different startegies for this
            if len(filtered_nodes) > 0:
                evicted_nodes.update(all_nodes - filtered_nodes)
                node_id = filtered_nodes.pop()
            else:
                print("No good nodes found for sample")
                continue

            self.request_sample(node_id, block_root, sample)
            self.process_requests()

        print(f"{len(evicted_nodes)} evicted nodes")

        # nodes that were honest but were evicted
        false_positives = set()
        for node in evicted_nodes:
            if self.attack.should_respond(bytes_to_int(node)):
                false_positives.add(node)

        print(f"{len(false_positives)} false positives")

        # nodes that were attack nodes and were evicted
        true_positives = evicted_nodes - false_positives

        print(f"{len(true_positives)} true positives")

        # nodes that weren't evicted
        negatives = self.graph.num_nodes() - len(evicted_nodes)
        print(f"{negatives} non evicted nodes")

        # attack nodes that weren't evicted
        true_negatives = negatives - abs(
            self.attack.num_attack_nodes - len(true_positives)
        )
        print(f"{true_negatives} true negatives")

        # honest nodes that weren't evicted
        false_negatives = negatives - true_negatives
        print(f"{false_negatives} false negatives")
