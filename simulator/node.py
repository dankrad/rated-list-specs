from typing import List, Dict, Tuple, Set
from eth2spec.utils.ssz.ssz_typing import Bytes32, uint64
from dataclasses import dataclass

type NodeId = Bytes32
type SampleId = uint64
type Root = Bytes32


class NodeRecord:
    def __init__(self, node_id, children, parents):
        self.node_id: NodeId = node_id
        self.children: List[NodeRecord] = children
        self.parents: List[NodeRecord] = parents


@dataclass
class ScoreKeeper:
    """This class implements the score keeper data structure"""

    descendants_contacted: Dict[NodeId, Set[Tuple[NodeId, SampleId]]]
    descendants_replied: Dict[NodeId, Set[Tuple[NodeId, SampleId]]]


@dataclass
class RatedListDHT:
    """This class implements the rated list data structure"""

    nodes: Dict[NodeId, NodeRecord]
    scores: Dict[Root, ScoreKeeper]


class Node:
    """This class implements a node in the network"""

    def __init__(self, id: NodeId, peers: List[NodeId]):
        print(" starting a new node in the network")

        self.own_id = id
        self.dht = RatedListDHT({}, {})

        self.dht.nodes[id] = NodeRecord(id, [], [])
        self.on_get_peers_response(id, peers)

        print(" started a node in the node with nodeId - %s", id)

    def compute_descendant_score(self, block_root: Root, node_id: NodeId) -> float:
        score_keeper = self.dht.scores[block_root]
        return len(score_keeper.descendants_contacted[node_id]) / len(
            score_keeper.descendants_replied[node_id]
        )

    def on_get_peers_response(self, node_id: NodeId, peers: List[NodeId]):
        for peer_id in peers:
            child_node: NodeRecord = None

            if peer_id not in self.dht.nodes:
                child_node = NodeRecord(peer_id, [], [])
                self.dht.nodes[peer_id] = child_node

            self.dht.nodes[peer_id].parents.append(node_id)
            self.dht.nodes[node_id].children.append(child_node)

        for child in self.dht.nodes[node_id].children:
            if child.node_id not in peers:
                # Node no longer has child peer, remove link
                self.dht.nodes[node_id].children.remove(child)
                self.dht.nodes[child.node_id].parents.remove(self.dht.nodes[node_id])

                if len(child.parents) == 0:
                    del self.dht.nodes[child.node_id]

    def compute_node_score(self, block_root: Root, node_id: NodeId) -> float:
        score = self.compute_descendant_score(block_root, node_id)

        cur_path_scores: Dict[NodeId, float] = {
            parent: score for parent in self.dht.nodes[node_id].parents
        }

        best_score = 0.0

        # traverse all paths of node_id by iterating through its parents and
        # grand parents. Note the best score when the iteration reaches root
        while cur_path_scores:
            new_path_scores: Dict[NodeId, float] = {}
            for node, score in cur_path_scores.items():
                for parent in self.dht.nodes[node].parents:
                    if parent == self.own_id:
                        best_score = max(best_score, score)
                    else:
                        par_score = self.compute_descendant_score(block_root, parent)
                        if (
                            parent not in new_path_scores
                            or new_path_scores[parent] < par_score
                        ):
                            new_path_scores[parent] = par_score

            cur_path_scores = new_path_scores

        return best_score
