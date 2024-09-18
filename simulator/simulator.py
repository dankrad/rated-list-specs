from node import Node, NodeProfile
import rustworkx as rx
import networkx as nx
import random as rn
from typing import Dict
from utils import NodeId, SampleId, Root, gen_node_id
from eth2spec.utils.ssz.ssz_typing import Bytes32
from dataclasses import dataclass
import queue


@dataclass
class RequestQueueItem:
    node_id: NodeId
    sample_id: SampleId
    block_root: Bytes32

@dataclass
class NodeAttribute:
    node_id: NodeId
    node_profile: NodeProfile

# TODO: make node profiles just an enum
# TODO: simulate validator exits and entries. maybe we just allow a distribution for arrivals and exits.
# TODO: add visualization

class SimulatedNode(Node):
    def __init__(self, graph: rx.PyGraph, binding_vertex=None):
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
        # self.graph_mapping[binding_vertex] = self.own_id
        self.graph_mapping[self.own_id] = binding_vertex
        node_id = ""
        # assign a node id for every vertex in the graph
        for vertex_id in self.graph.node_indices():
            if vertex_id != self.own_id:
                node_id=gen_node_id()
                self.graph_mapping[node_id] = vertex_id
                self.graph[vertex_id] = NodeAttribute(node_id=node_id,node_profile=NodeProfile.HONEST)
    
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
        
        node_index = self.graph_mapping[node_id]

        for peer_id in self.graph.neighbors(node_index):        
            peers.append(self.graph[peer_id].node_id)
            # TODO: We should have a workflow where nodes also get removed
            self.add_samples_on_entry(self.graph[peer_id].node_id)
        self.on_get_peers_response(node_id, peers)

    def bind(self, profile: NodeProfile, selector):
        print("Binding profiles to nodes")
        # TODO: instead of a selector function maybe we can define more parameters

        for node in self.graph.nodes():
            if node.node_id != self.own_id:
                if selector(node.node_id):
                   self.graph[self.graph_mapping[node.node_id]].node_profile = profile 
                else:
                   self.graph[self.graph_mapping[node.node_id]].node_profile = NodeProfile.HONEST

        # nx.set_node_attributes(self.graph, attr_mapping)

    def process_requests(self):
        # TODO: implemente node profile behaviours

        while not self.request_queue.empty():
            request: RequestQueueItem = self.request_queue.get()
            node_profile: NodeProfile = self.graph[self.graph_mapping[request.node_id]].node_profile
            
            if node_profile is NodeProfile.OFFLINE:
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
        for level_one_peer_id in self.graph.neighbors(self.graph_mapping[self.own_id]):
            self.get_peers(self.graph[level_one_peer_id].node_id)  # add level 2 peers

            # ask for level three peers from each level two peer
            for level_two_peer_id in self.graph.neighbors(level_one_peer_id):
                self.get_peers(self.graph[level_two_peer_id].node_id)  # add level 3 peers

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
