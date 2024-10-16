
from typing import Dict, Tuple, Set, Sequence, List
from eth2spec.utils.ssz.ssz_typing import Bytes32, uint64, uint256, uint8
from dataclasses import dataclass
from utils import bytes_to_uint64, uint_to_bytes, hash, ENDIANNESS



MAX_TREE_DEPTH = 3
MAX_CHILDREN = 100
MAX_PARENTS = 100
DATA_COLUMN_SIDECAR_SUBNET_COUNT = uint8(128)
NUMBER_OF_COLUMNS = uint8(128)
MIN_CUSTODY_COUNT = uint8(2)
UINT256_MAX = uint256(2**256 - 1)



NodeId = Bytes32

SampleId = uint64

Root = Bytes32

@dataclass
class NodeRecord:
    node_id: NodeId
    children: Set[NodeId]
    parents: Set[NodeId] # creates a doubly linked list

@dataclass
class ScoreKeeper:
    descendants_contacted: Dict[NodeId, Set[Tuple[NodeId, SampleId]]]
    descendants_replied: Dict[NodeId, Set[Tuple[NodeId, SampleId]]]

@dataclass
class RatedListData:
    own_id: NodeId
    sample_mapping: Dict[SampleId, Set[NodeId]]
    nodes: Dict[NodeId, NodeRecord]
    scores: Dict[Bytes32, ScoreKeeper]

def compute_descendant_score(rated_list_data: RatedListData,
                             block_root: Root,
                             node_id: NodeId) -> float:
    # if scores are being computed before shooting out the first request, then the scorekeeper
    # object is not yet initialized. In this case we assign the best score for any node_id
    if block_root not in rated_list_data.scores:
        return 1.0

    score_keeper = rated_list_data.scores[block_root]

    # Additionally, no previous sample requests might be made to a particular node_id's descendant
    # before trying to calculate its score. In this case we assign the best score for the node_id
    if node_id not in score_keeper.descendants_contacted:
        return 1.0

    # if the node_id is not in the reply then none of its descendants that were contacted replied
    # so return 0
    if node_id not in score_keeper.descendants_replied:
        return 0

    return len(score_keeper.descendants_replied[node_id]) / len(score_keeper.descendants_contacted[node_id]) if len(score_keeper.descendants_contacted[node_id]) > 0 else 0

def compute_node_score(rated_list_data: RatedListData,
                       block_root: Root,
                       node_id: NodeId) -> float:
    
    
    if node_id == rated_list_data.own_id:
        return 1.0

    score = compute_descendant_score(rated_list_data, block_root, node_id)

    cur_path_scores: Dict[NodeId, float] = {node_id: score}
    touched_nodes = set()

    best_score = 0.0

    # traverse all paths of node_id by iterating through its parents and
    # grand parents. Note the best score when the iteration reaches root
    while cur_path_scores:
        new_path_scores: Dict[NodeId, float] = {}
        for node, score in cur_path_scores.items():
            touched_nodes.add(node)
            for parent in rated_list_data.nodes[node].parents:
                if parent == rated_list_data.own_id:
                    best_score = max(best_score, score)
                else:
                    par_score = compute_descendant_score(rated_list_data, block_root, parent)
                    if (
                        parent not in new_path_scores
                        or new_path_scores[parent] < par_score
                    ) and parent not in touched_nodes:
                        new_path_scores[parent] = par_score

        cur_path_scores = new_path_scores

    return best_score

def on_get_peers_response(rated_list_data: RatedListData, node_id: NodeId, peers: Sequence[NodeId]):
    
    # first add the parent node id 
    if node_id not in rated_list_data.nodes:
        rated_list_data.nodes[node_id] = NodeRecord(node_id, set(), set())

    
    for peer_id in peers:
        child_node: NodeRecord = None

        if peer_id not in rated_list_data.nodes: 
            rated_list_data.nodes[peer_id] = NodeRecord(peer_id, set(), set())

        if peer_id in rated_list_data.nodes[node_id].parents:
            continue

        rated_list_data.nodes[peer_id].parents.add(node_id)
        rated_list_data.nodes[node_id].children.add(peer_id)

    for child_id in rated_list_data.nodes[node_id].children:
        if child_id not in peers:
            # Node no longer has child peer, remove link
            rated_list_data.nodes[node_id].children.remove(child_id)
            rated_list_data.nodes[child_id].parents.remove(node_id)

            if len(rated_list_data.nodes[child_id].parents) == 0:
                rated_list_data.nodes.remove(child_id)

def on_request_score_update(rated_list_data: RatedListData,
                            block_root: Root,
                            node_id: NodeId,
                            sample_id: SampleId):

    node_record = rated_list_data.nodes[node_id]

    if block_root not in rated_list_data.scores:
        rated_list_data.scores[block_root] = ScoreKeeper({}, {})

    score_keeper = rated_list_data.scores[block_root]
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
            new_ancestors.update(rated_list_data.nodes[ancestor].parents)
        cur_ancestors = new_ancestors

def on_response_score_update(rated_list_data: RatedListData,
                             block_root: Root,
                             node_id: NodeId,
                             sample_id: SampleId):

    node_record = rated_list_data.nodes[node_id]
    score_keeper = rated_list_data.scores[block_root]
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
            new_ancestors.update(rated_list_data.nodes[ancestor].parents)
        cur_ancestors = new_ancestors

def add_samples_on_entry(rated_list_data: RatedListData, node_id: NodeId):
    sample_ids = get_custody_columns(node_id)
    for id in sample_ids:
        if id not in rated_list_data.sample_mapping:
            rated_list_data.sample_mapping[id] = set()
    
        rated_list_data.sample_mapping[id].add(node_id)

def remove_samples_on_exit(rated_list_data: RatedListData, node_id: NodeId):
    sample_ids = get_custody_columns(node_id)
    
    for id in sample_ids:
        if id not in rated_list_data.sample_mapping:
            continue

        rated_list_data.sample_mapping[id].remove(node_id)

def filter_nodes(rated_list_data: RatedListData, block_root: Bytes32, sample_id: SampleId) -> Set[Tuple[NodeId, float]]:
    scores = {}
    filter_score = 0.9
    filtered_nodes = set()

    for i in range(2):
        evicted_nodes = set()
        for node_id in rated_list_data.sample_mapping[sample_id]:
            if node_id not in scores:
                score = compute_node_score(rated_list_data, block_root, node_id)
                scores[node_id] = score

            if scores[node_id] >= filter_score and node_id not in evicted_nodes:
                filtered_nodes.add((node_id, scores[node_id]))
            else:
                # print(f"Removed: {node_id} with score {scores[node_id]}")
                evicted_nodes.add(node_id)
                evicted_nodes.update(rated_list_data.nodes[node_id].children)

        if len(filtered_nodes) > 0:
            break

        # if no nodes are filtered then reset the filter score to avg - 0.1. this will guarantee atleast one node.
        filter_score = (
            sum([score for _, score in scores.items()]) / len(scores) - 0.1
        )
    return filtered_nodes

def get_custody_columns(
    node_id: NodeId, custody_subnet_count: uint8 = MIN_CUSTODY_COUNT
) -> Sequence[SampleId]:
    assert custody_subnet_count <= DATA_COLUMN_SIDECAR_SUBNET_COUNT

    subnet_ids: List[uint64] = []
    current_id = uint256(int.from_bytes(node_id, ENDIANNESS))

    while len(subnet_ids) < custody_subnet_count:
        subnet_id = bytes_to_uint64(
            hash(uint_to_bytes(uint256(current_id)))[0:8]
        ) % int(DATA_COLUMN_SIDECAR_SUBNET_COUNT)
        if subnet_id not in subnet_ids:
            subnet_ids.append(subnet_id)
        if current_id == UINT256_MAX:
            # Overflow prevention
            current_id = NodeId(0)
        current_id += 1

    assert len(subnet_ids) == len(set(subnet_ids))

    columns_per_subnet = NUMBER_OF_COLUMNS // int(DATA_COLUMN_SIDECAR_SUBNET_COUNT)
    return sorted(
        [
            SampleId(int(DATA_COLUMN_SIDECAR_SUBNET_COUNT) * i + subnet_id)
            for i in range(columns_per_subnet)
            for subnet_id in subnet_ids
        ]
    )

