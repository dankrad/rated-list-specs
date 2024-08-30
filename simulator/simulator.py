from node import Node
from networkx import Graph


# TODO: simulate validator exits and entries. maybe we just allow a distribution for arrivals and exits.
# TODO: add visualization
class Simulator:
    def __init__(self, node: Node, graph: Graph, binding_vertex):
        self.node = node
        self.graph = graph

        self.node.get_peers = self.get_peers
        self.node.request_sample = self.request_sample

        # TODO: assign node ids to all graph vertices

    def bind(self, profile: NodeProfile, node_ids: List[NodeId]):
        # TODO: add profile for a range of node_ids
        # should also support randomly assigning profiles, assinging profiles at different levels
        # assigning profiles for sybil testing etc.
        print("not implemented")

    def request_sample(
        self, node_id: NodeId, block_root: Root, samples: Sequence[SampleId]
    ):
        for sample in samples:
            # TODO: add the request to a queue
            self.node.on_request_score_update(block_root, node_id, samples)

    def get_peers(self, node_id: NodeId):
        # TODO: should fetch all peers of a particular node id from the graph
        peers = None
        self.node.on_get_peers_response(node_id, peers)

    def process_requests(self):
        # TODO: Read the queue of requests for each one check node profile and respond accordingly
        # Call self.node.on_response_score_update(block_root, node_id, sample_id)
        print("not implemented")
