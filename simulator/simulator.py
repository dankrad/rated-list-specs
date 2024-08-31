from node import Node, NodeProfile
from networkx import Graph
import random as rn
from utils import NodeId,SampleId, Root, MAX_PEERS
from eth2spec.utils.ssz.ssz_typing import Bytes32
from typing import List, Sequence
from dataclasses import dataclass
from utils import bytes_to_uint64,uint_to_bytes
from eth2spec.utils.ssz.ssz_typing import uint256, uint64, uint8
import queue

@dataclass
class RequestQueueItem:
    node_id: NodeId
    sample_id: SampleId
    block_root: Bytes32
    

# TODO: simulate validator exits and entries. maybe we just allow a distribution for arrivals and exits.
# TODO: add visualization

class Simulator:
    
    def __init__(self, node: Node, graph: Graph, binding_vertex=None):
        self.node = node
        self.graph = graph

        self.node.get_peers = self.get_peers
        self.node.request_sample = self.request_sample
        self.request_queue = queue.Queue()
        

        # TODO: assign node ids to all graph vertices

    def bind(self, profile: NodeProfile, node_ids: List[NodeId]):
        
        # TODO: add profile for a range of node_ids
        # should also support randomly assigning profiles, assinging profiles at different levels
        # assigning profiles for sybil testing etc.

        for node_id in node_ids:
            random_peer = None
            while True:
                random_peer = rn.choice(list(self.graph.nodes))
                if self.graph.degree[random_peer]<=MAX_PEERS: break;             
            
            self.graph.add_node(node_id, profile=profile)
            self.graph.add_edge(node_id, random_peer)


    def request_sample(
        self, node_id: NodeId, block_root: Root, samples: Sequence[SampleId]
    ):
        for sample in samples:
            self.node.on_request_score_update(block_root, node_id, sample)
            self.request_queue.put(RequestQueueItem(node_id=node_id,sample_id=sample,block_root=block_root))

            

    def get_peers(self, node_id: NodeId):
        
        # TODO: should fetch all peers of a particular node id from the graph
        
        peers = [peer for peer in self.graph.neighbors(node_id)]
        self.node.on_get_peers_response(node_id, peers)

    def process_requests(self):
        # TODO: Read the queue of requests for each one check node profile and respond accordingly
        # Call self.node.on_response_score_update(block_root, node_id, sample_id)
        while self.request_queue.empty()!=True:
            request: RequestQueueItem = self.request_queue.get()
            node_profile: NodeProfile = self.graph.nodes[request.node_id]
            if node_profile.malicious: continue
            self.node.on_response_score_update(
                block_root=request.block_root,
                node_id=request.node_id,
                sample_id=request.sample_id
                )

    def run(self, peers):
        print("Starting rated list simulator ....")
        self.graph.add_node(self.node.own_id)
        self.bind(NodeProfile(malicious=False,honest=True,offline=False),peers)
        