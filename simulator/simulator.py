import rustworkx as rx
import random as rn
from eth2spec.utils.ssz.ssz_typing import Bytes32
from dataclasses import dataclass
from collections import deque
import secrets
import queue
from attack.attack import SybilAttack
from nodeprofile import NodeBehaviour
from node import (
    MAX_PARENTS,
    MAX_CHILDREN,
    NodeId,
    SampleId,
    Root,
    MAX_TREE_DEPTH,
    RatedListData,
    NodeRecord,
)
import node
from typing import Sequence, Set

def gen_node_id():
        return NodeId(secrets.token_bytes(32))

@dataclass
class RequestQueueItem:
    node_id: NodeId
    sample_id: SampleId
    block_root: Bytes32


@dataclass
class NodeAttribute:
    node_id: NodeId


class SimulatedNode:
    def __init__(self, graph: rx.PyGraph, binding_vertex=None):
        self.dht = RatedListData(gen_node_id(), {}, {}, {})
        self.dht.nodes[self.dht.own_id] = NodeRecord(id, set(), set())

        sybil_rate = 0.5
        self.graph = graph
        self.request_queue = queue.Queue()
        self.node_behaviour = NodeBehaviour(
            graph=graph,
            attack=SybilAttack(
                graph=graph, sybil_nodes=int(graph.num_nodes() * sybil_rate)
            ),
        )
        self.graph_mapping = {}

        self.node_behaviour.init_attack()

        if binding_vertex is None:
            binding_vertex = rn.choice(self.graph.nodes())

        # calculate average degree
        sum = 0
        for node in self.graph.nodes():
            sum = sum + self.graph.degree(self.graph[node])

        print("Average Degree:", sum / len(self.graph.nodes()))
        print(
            "mapping "
            + str(self.dht.own_id)
            + " to graph vertice "
            + str(binding_vertex)
        )

        # assign the node's id to the binding vertex
        # self.graph_mapping[binding_vertex] = self.own_id
        self.graph_mapping[self.dht.own_id] = binding_vertex

        # assign a node id for every vertex in the graph
        for vertex_id in self.graph.node_indices():
            if vertex_id != self.dht.own_id:
                node_id = gen_node_id()
                self.graph_mapping[node_id] = vertex_id
                self.graph[vertex_id] = NodeAttribute(
                    node_id=node_id,
                )
    
    

    def compute_descendant_score(self, block_root: Root, node_id: NodeId) -> float:
        return node.compute_descendant_score(self.dht, block_root, node_id)

    def compute_node_score(self, block_root: Root, node_id: NodeId) -> float:
        return node.compute_node_score(self.dht, block_root, node_id)

    def on_get_peers_response(self, node_id: NodeId, peers: Sequence[NodeId]):
        node.on_get_peers_response(self.dht, node_id, peers)

    def on_request_score_update(
        self, block_root: Root, node_id: NodeId, sample_id: SampleId
    ):
        node.on_request_score_update(self.dht, block_root, node_id, sample_id)

    def on_response_score_update(
        self, block_root: Root, node_id: NodeId, sample_id: SampleId
    ):
        node.on_response_score_update(self.dht, block_root, node_id, sample_id)

    def add_samples_on_entry(self, node_id: NodeId):
        node.add_samples_on_entry(self.dht, node_id)

    def remove_samples_on_exit(self, node_id: NodeId):
        node.remove_samples_on_exit(self.dht, node_id)

    def filter_nodes(self, block_root: Bytes32, sample_id: SampleId) -> Set[NodeId]:
        return node.filter_nodes(self.dht, block_root, sample_id)

    def request_sample(self, node_id: NodeId, block_root: Root, sample: SampleId):
        print("Requesting samples from", node_id)

        self.on_request_score_update(block_root, node_id, sample)
        self.request_queue.put(
            RequestQueueItem(node_id=node_id, sample_id=sample, block_root=block_root)
        )

    def get_peers(self, node_id: NodeId):
        peers = []

        node_index = self.graph_mapping[node_id]
        random_neighbors = list(self.graph.neighbors(node_index))
        rn.shuffle(random_neighbors)

        for i, peer_id in enumerate(random_neighbors):
            if i >= MAX_CHILDREN:
                break

            peers.append(self.graph[peer_id].node_id)
            self.add_samples_on_entry(self.graph[peer_id].node_id)
        self.on_get_peers_response(node_id, peers)

    # def bind(self, profile: NodeProfile, selector):
    #     print("Binding profiles to nodes")
    #     # TODO: instead of a selector function maybe we can define more parameters

    #     for node in self.graph.nodes():
    #         if node.node_id != self.own_id:
    #             if selector(node.node_id):
    #                 self.graph[self.graph_mapping[node.node_id]].node_profile = profile

    def process_requests(self):
        while not self.request_queue.empty():
            request: RequestQueueItem = self.request_queue.get()
            # node_profile: NodeProfile = self.graph[
            #     self.graph_mapping[request.node_id]
            # ].node_profile

            if not self.node_behaviour.should_respond(
                self.graph_mapping[request.node_id]
            ):
                print("Rejected sample request", request)
                continue

            self.on_response_score_update(
                block_root=request.block_root,
                node_id=request.node_id,
                sample_id=request.sample_id,
            )

    def construct_tree(self):
        print("constructing the rated list tree from the graph")

        # iterative BFS approach to find peers where max_tree_depth is parametrised
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
        # all nodes are children(grand or great grand until tree depth) of root node
        if check_ancestor == self.dht.own_id:
            return True

        if check_ancestor == grand_child:
            return True

        if check_ancestor in self.dht.nodes[grand_child].parents:
            return True

        # assuming the grand_child is at the last level check grand parents(level 1)
        for parent in self.dht.nodes[grand_child].parents:
            if check_ancestor in self.dht.nodes[parent].parents:
                return True

            # if our assumption is wrong the parents will be the root node itself
            if parent == self.dht.own_id:
                return False

        return False
