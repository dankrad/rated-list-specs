from node import Node, NodeProfile
import networkx as nx
import random as rn
from utils import NodeId, SampleId, Root, gen_node_id
from eth2spec.utils.ssz.ssz_typing import Bytes32
from typing import Sequence
from dataclasses import dataclass
import queue


@dataclass
class RequestQueueItem:
    node_id: NodeId
    sample_id: SampleId
    block_root: Bytes32


# TODO: make node profiles just an enum
# TODO: simulate validator exits and entries. maybe we just allow a distribution for arrivals and exits.
# TODO: add visualization


class SimulatedNode(Node):
    def __init__(self, graph: nx.Graph, binding_vertex=None):
        super().__init__(gen_node_id())
        self.graph = graph

        self.request_queue = queue.Queue()

        self.graph_mapping = {}

        if binding_vertex is None:
            binding_vertex = rn.choice(list(self.graph.nodes))

        print(
            "mapping " + str(self.own_id) + " to graph vertice " + str(binding_vertex)
        )

        # assign the node's id to the binding vertex
        self.graph_mapping[binding_vertex] = self.own_id
        nx.relabel_nodes(self.graph, self.graph_mapping, copy=False)

        # assign a node id for every vertex in the graph
        for vertex_id in list(self.graph.nodes):
            if vertex_id != self.own_id:
                self.graph_mapping[vertex_id] = gen_node_id()

        # rename all vertices by their assigned node ids
        nx.relabel_nodes(self.graph, self.graph_mapping, copy=False)

    # NOTE: ideally this function should be defined in the node implementation
    def request_sample(self, node_id: NodeId, block_root: Root, sample: SampleId):
        print("Requesting samples from", node_id)

        self.on_request_score_update(block_root, node_id, sample)
        self.request_queue.put(
            RequestQueueItem(node_id=node_id, sample_id=sample, block_root=block_root)
        )

    # NOTE: ideally this function should be defined in the node implementation
    def get_peers(self, node_id: NodeId):
        peers = []

        for peer_id in self.graph.neighbors(node_id):
            peers.append(peer_id)
            # TODO: We should have a workflow where nodes also get removed
            self.add_samples_on_entry(peer_id)
        self.on_get_peers_response(node_id, peers)

    def bind(self, profile: NodeProfile, selector):
        print("Binding profiles to nodes")
        # TODO: instead of a selector function maybe we can define more parameters

        attr_mapping = {}

        for id, node in self.graph.nodes.items():
            if id != self.own_id:
                if selector(id):
                    attr_mapping[id] = {"profile": profile}
                else:
                    attr_mapping[id] = {"profile": NodeProfile.HONEST}

        nx.set_node_attributes(self.graph, attr_mapping)

    def process_requests(self):
        # TODO: implemente node profile behaviours

        while not self.request_queue.empty():
            request: RequestQueueItem = self.request_queue.get()
            node_profile: NodeProfile = (
                self.graph.nodes[request.node_id]["profile"]
                if "profile" in self.graph.nodes[request.node_id]
                else NodeProfile.HONEST
            )

            if node_profile.offline:
                print("Rejected sample request", request)
                continue

            self.on_response_score_update(
                block_root=request.block_root,
                node_id=request.node_id,
                sample_id=request.sample_id,
            )

    def construct_tree(self):
        print("constructing the rated list tree from the graph")

        # construct the tree till level 3 using a depth-first search
        self.get_peers(self.own_id)  # add level 1 peers

        # ask for level two peers from each level one peer
        for level_one_peer_id in self.graph.neighbors(self.own_id):
            self.get_peers(level_one_peer_id)  # add level 2 peers

            # ask for level three peers from each level two peer
            for level_two_peer_id in self.graph.neighbors(level_one_peer_id):
                self.get_peers(level_two_peer_id)  # add level 3 peers

    def is_ancestor(self, grand_child: NodeId, check_ancestor: NodeId) -> bool:
        # all nodes are children(grand or great grand until tree depth) of root node
        if check_ancestor == self.own_id:
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
            if parent == self.own_id:
                return False

        return False
