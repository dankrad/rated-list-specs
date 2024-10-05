from typing import List, Dict, Tuple, Set, Sequence
from eth2spec.utils.ssz.ssz_typing import Bytes32
from dataclasses import dataclass
from utils import NodeId, SampleId, Root
from dascore import get_custody_columns

MAX_TREE_DEPTH = 3
MAX_CHILDREN = 100
MAX_PARENTS = 100


@dataclass
class NodeRecord:
    node_id: NodeId
    children: Set[NodeId]
    parents: Set[NodeId]


@dataclass
class ScoreKeeper:
    """This class implements the score keeper data structure"""

    descendants_contacted: Dict[NodeId, Set[Tuple[NodeId, SampleId]]]
    descendants_replied: Dict[NodeId, Set[Tuple[NodeId, SampleId]]]


@dataclass
class RatedListDHT:
    """This class implements the rated list data structure"""

    sample_mapping: Dict[SampleId, Set[NodeId]]
    nodes: Dict[NodeId, NodeRecord]
    scores: Dict[Root, ScoreKeeper]


class Node:
    """This class implements a node in the network"""

    def __init__(self, id: NodeId):
        print(" starting a new node in the network")
        self.own_id = id
        self.dht = RatedListDHT({}, {}, {})
        self.dht.nodes[id] = NodeRecord(id, set(), set())

        print(" started a node in the node with nodeId - %s", id)

    def compute_descendant_score(self, block_root: Root, node_id: NodeId) -> float:
        # if scores are being computed before shooting out the first request, then the scorekeeper
        # object is not yet initialized. In this case we assign the best score for any node_id
        if block_root not in self.dht.scores:
            return 1.0

        score_keeper = self.dht.scores[block_root]

        # Additionally, no previous sample requests might be made to a particular node_id's descendant
        # before trying to calculate its score. In this case we assign the best score for the node_id
        if node_id not in score_keeper.descendants_contacted:
            return 1.0

        # if the node_id is not in the reply then none of its descendants that were contacted replied
        # so return 0
        if node_id not in score_keeper.descendants_replied:
            return 0

        return (
            len(score_keeper.descendants_replied[node_id])
            / len(score_keeper.descendants_contacted[node_id])
            if len(score_keeper.descendants_contacted[node_id]) > 0
            else 1.0
        )

    def on_get_peers_response(self, node_id: NodeId, peers: Sequence[NodeId]):
        for peer_id in peers:
            child_node: NodeRecord = None

            if peer_id not in self.dht.nodes:
                child_node = NodeRecord(peer_id, set(), set())
                self.dht.nodes[peer_id] = child_node

            # if one of the peers is already a parent. don't include it
            if peer_id in self.dht.nodes[node_id].parents:
                continue

            self.dht.nodes[peer_id].parents.add(node_id)
            self.dht.nodes[node_id].children.add(peer_id)

        # if the peers response of the current node_id doesn't include some of
        # the past children then remove them
        for child_id in self.dht.nodes[node_id].children:
            if child_id not in peers:
                # Node no longer has child peer, remove link
                self.dht.nodes[node_id].children.remove(child_id)
                self.dht.nodes[child_id].parents.remove(node_id)

                if len(self.dht.nodes[child_id].parents) == 0:
                    del self.dht.nodes[child_id]

    def compute_node_score(self, block_root: Root, node_id: NodeId) -> float:
        if node_id == self.own_id:
            return 1.0

        score = self.compute_descendant_score(block_root, node_id)

        cur_path_scores: Dict[NodeId, float] = {node_id: score}
        touched_nodes = set()

        best_score = 0.0

        # traverse all paths of node_id by iterating through its parents and
        # grand parents. Note the best score when the iteration reaches root
        while cur_path_scores:
            new_path_scores: Dict[NodeId, float] = {}
            for node, score in cur_path_scores.items():
                touched_nodes.add(node)
                for parent in self.dht.nodes[node].parents:
                    if parent == self.own_id:
                        best_score = max(best_score, score)
                    else:
                        par_score = self.compute_descendant_score(block_root, parent)
                        if (
                            parent not in new_path_scores
                            or new_path_scores[parent] < par_score
                        ) and parent not in touched_nodes:
                            new_path_scores[parent] = par_score

            cur_path_scores = new_path_scores

        return best_score

    def on_request_score_update(
        self, block_root: Root, node_id: NodeId, sample_id: SampleId
    ):
        node_record = self.dht.nodes[node_id]

        if block_root not in self.dht.scores:
            self.dht.scores[block_root] = ScoreKeeper({}, {})

        score_keeper = self.dht.scores[block_root]
        cur_ancestors = set(node_record.parents)
        touched_nodes = set()

        while cur_ancestors:
            new_ancestors = set()
            for ancestor in cur_ancestors:
                if ancestor in touched_nodes:
                    continue

                touched_nodes.add(ancestor)

                if ancestor not in score_keeper.descendants_contacted:
                    score_keeper.descendants_contacted[ancestor] = set()

                score_keeper.descendants_contacted[ancestor].add((node_id, sample_id))
                new_ancestors.update(self.dht.nodes[ancestor].parents)
            cur_ancestors = new_ancestors

    def on_response_score_update(
        self, block_root: Root, node_id: NodeId, sample_id: SampleId
    ):
        node_record = self.dht.nodes[node_id]
        score_keeper = self.dht.scores[block_root]
        cur_ancestors = set(node_record.parents)

        touched_nodes = set()

        while cur_ancestors:
            new_ancestors = set()
            for ancestor in cur_ancestors:
                if ancestor in touched_nodes:
                    continue

                touched_nodes.add(ancestor)

                if ancestor not in score_keeper.descendants_replied:
                    score_keeper.descendants_replied[ancestor] = set()

                score_keeper.descendants_replied[ancestor].add((node_id, sample_id))
                new_ancestors.update(self.dht.nodes[ancestor].parents)
            cur_ancestors = new_ancestors

    def add_samples_on_entry(self, node_id: NodeId):
        # TODO: support a variable custody count for nodes
        sample_ids = get_custody_columns(node_id)

        for id in sample_ids:
            if id not in self.dht.sample_mapping:
                self.dht.sample_mapping[id] = set()

            self.dht.sample_mapping[id].add(node_id)

    def remove_samples_on_exit(self, node_id: NodeId):
        # TODO: support a variable custody count for nodes
        sample_ids = get_custody_columns(node_id)

        for id in sample_ids:
            if id not in self.dht.sample_mapping:
                continue

            self.dht.sample_mapping[id].remove(node_id)

    def filter_nodes(self, block_root: Bytes32, sample_id: SampleId) -> Set[NodeId]:
        scores = {}
        filter_score = 0.9
        filtered_nodes = set()

        for i in range(2):
            evicted_nodes = set()
            for node_id in self.dht.sample_mapping[sample_id]:
                if node_id not in scores:
                    score = self.compute_node_score(block_root, node_id)
                    scores[node_id] = score

                if scores[node_id] >= filter_score and node_id not in evicted_nodes:
                    filtered_nodes.add(node_id)
                else:
                    # print(f"Removed: {node_id} with score {scores[node_id]}")
                    evicted_nodes.add(node_id)
                    evicted_nodes.update(self.dht.nodes[node_id].children)

            if len(filtered_nodes) > 0:
                break

            print("No nodes above threshold using average")
            # if no nodes are filtered then reset the filter score to avg - 0.1. this will guarantee atleast one node.
            filter_score = (
                sum([score for _, score in scores.items()]) / len(scores) - 0.1
            )
        return filtered_nodes

    def request_sample(
        self, node_id: NodeId, block_root: Root, samples: Sequence[SampleId]
    ):
        print("not implemented")

    def get_peers(self, node_id: NodeId):
        print("not implemented")
