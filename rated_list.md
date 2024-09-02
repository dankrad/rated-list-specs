---
title: Draft

---

# Rated List specificetions

## Constants

The below constants assume a max node degree of 100

|     Name                              | Value         |
|---------------------------------------|---------------|
| MAX_TREE_DEPTH                        | 3             | 
| MAX_CHILDREN                          | 100           |
| MAX_PARENTS                           | 100           |
| MAX_BLOBS_PER_BLOCK                   | 6             |
| NUMBER_OF_COLUMNS                     | uint64(64)    |
| Cell                                  | ByteVector[BYTES_PER_FIELD_ELEMENT * FIELD_ELEMENTS_PER_CELL] |
| FIELD_ELEMENTS_PER_CELL               | uint64(64)    |
| MAX_BLOB_COMMITMENTS_PER_BLOCK        | uint64(4096)  |
| KZGProof                              | Bytes48       |
| KZGCommitment                         | Bytes48       |
| KZG_COMMITMENTS_INCLUSION_PROOF_DEPTH | uint64(4)     | 

## Custom types

We assume all peer ids (interchangeably called node ids) are 256-bit strings represented as `Bytes32`

```python
NodeId = Bytes32
```

We will represent SampleIds as integers, although they could potentially be represented as pairs in the future

```python
SampleId = uint64
```

### `NodeRecord`

```python
@dataclass
class NodeRecord:
    node_id: NodeId
    csc: uint8
    children: List[NodeId, MAX_CHILDREN]
    parents: List[NodeId, MAX_PARENTS] # creates a doubly linked list
```

### ScoreKeeper

Data type to keep the score for one DAS query (corresponding to one block)

```python
class ScoreKeeper:
    descendants_contacted: Dict[NodeId, Set[Tuple[NodeId, SampleId]]]
    descendants_replied: Dict[NodeId, Set[Tuple[NodeId, SampleId]]]
```


### RatedListData

Data type to keep all information required to maintain a rated list instance

```python
class RatedListData:
    sample_mapping: Dict[SampleId, Set[NodeId]]
    nodes: Dict[NodeId, NodeRecord]
    scores: Dict[Bytes32, ScoreKeeper]
```

### `compute_descendant_score`

```python
def compute_descendant_score(rated_list_data: RatedListData,
                             block_root: Root,
                             node_id: NodeId) -> float:
    score_keeper = rated_list_data.scores[block_root]
    return len(score_keeper.descendants_replied[node_id]) /
          len(score_keeper.descendants_contacted[node_id]) if len(score_keeper.descendants_contacted[node_id]) > 0 else 1.0
```

### `compute_node_score`

```python
def compute_node_score(rated_list_data: RatedListData,
                       block_root: Root,
                       node_id: NodeId) -> float:
    # TODO:
    # For each path in which the node appears from the root of the tree, the "pathScore" is the `descendant_score` of the lowest node in the path
    # Return the highest score of any such path
    # This might require refactoring the data structure for more efficient
    # computation

    score = compute_descendant_score(rated_list_data, block_root, node_id)

    cur_path_scores: Dict[NodeId, float] = {
        parent: score for parent in rated_list_data.nodes[node_id].parents
    }

    best_score = 0.0

    while cur_path_scores:
        new_path_scores: Dict[NodeId, float] = {}
        for node, score in cur_path_scores.items():
            for parent in rated_list_data.nodes[node].parents:
                if parent == rated_list_data.own_id:
                    best_score = max(best_score, score)
                else:
                    par_score = compute_descendant_score(rated_list_data, block_root, parent)
                    if parent not in new_path_scores or
                        new_path_scores[parent] < par_score:
                        new_path_scores[parent] = par_score

        cur_path_scores = new_path_scores

    return best_score
```

### `on_get_peers_response`

Function that is called whenever we get the peer list of a node.

```python
def on_get_peers_response(rated_list_data: RatedListData, node_id: NodeId, peers: Sequence[(NodeId, uint8)]):
    
    for peer_id, csc in peers:
        child_node: NodeRecord = None

        if peer_id not in rated_list_data.nodes: 
            child_node = NodeRecord(peer_id, csc, [], [])
            rated_list_data.nodes[peer_id] = child_node

        rated_list_data.nodes[peer_id].parents.append(node_id)
        rated_list_data.nodes[node_id].children.append(peer_id)

    for child_id in rated_list_data.nodes[node_id].children:
        if child_id not in [id for id, _ in peer]:
            # Node no longer has child peer, remove link
            rated_list_data.nodes[node].children.remove(child_id)
            rated_list_data.nodes[child_id].parents.remove(node_id)
            if len(rated_list_data.nodes[child_id].parents) == 0:
                rated_list_data.nodes.remove(child_id)
```

### `on_request_score_update`

This function should be called whenever a node sends a request for a data sample to another node found using rated list

```python
def on_request_score_update(rated_list_data: RatedListData,
                            block_root: Root,
                            node_id: NodeId,
                            sample_id: SampleId):
    node_record = rated_list_data.nodes[nodes_id]
    score_keeper = rated_list_data.scores[block_root]
    cur_ancestors = set(node_record.parents)
    while cur_ancestors:
        new_ancestors = set()
        for ancestor in cur_ancestors:
            score_keeper.descendants_contacted[ancestor].append((node_id, sample_id))
            new_ancestors.update(ancestor.parents)
        cur_ancestors = new_ancestors
```

### `on_response_score_update`

This function should be called whenever a node receives a response to a request for a data sample from a node.

```python
def on_response_score_update(rated_list_data: RatedListData,
                             block_root: Root,
                             node_id: NodeId,
                             sample_id: SampleId):
    node_record = rated_list_data.nodes[nodes_id]
    score_keeper = rated_list_data.scores[block_root]
    cur_ancestors = set(node_record.parents)
    while cur_ancestors:
        new_ancestors = set()
        for ancestor in cur_ancestors:
            score_keeper.descendants_replied[ancestor].append((node_id, sample_id))
            new_ancestors.update(ancestor.parents)
        cur_ancestors = new_ancestors
```

### `add_samples_on_entry`

```python
def add_samples_on_entry(rated_list_data: RatedListData, node_id: NodeId, csc: uint8):
    sample_ids = get_custody_columns(node_id, csc)
    for id in sample_ids:
        if not rated_list_data.sample_mapping[id]:
            rated_list_data.sample_mapping[id] = set()
    
        rated_list_data.sample_mapping[id].update(node_id)
```

### `remove_samples_on_exit`

```python
def remove_samples_on_exit(rated_list_data: RatedListData, node_id: NodeId, csc: uint8):
    sample_ids = get_custody_columns(node_id, csc)
    
    for id in sample_ids:
        if not rated_list_data.sample_mapping[id]:
            continue

        rated_list_data.sample_mapping[id].remove(node_id)
```

### `filter_nodes`

```python
def filter_nodes(rated_list_data: RatedListData, block_root: Bytes32, sample_id: SampleId) -> List[NodeId]:
    scores = []
    filter_score = 0.9
    filtered_nodes = set()
    evicted_nodes = set()

    while len(filtered_nodes) == 0:
        for node_id in rated_list_data.sample_mapping[sample_id]:
            score = compute_node_score(rated_list_data, block_root, node_id)
            scores.append((node_id, score))

            if score >= filter_score and node not in evicted_nodes:
                filtered_nodes.update(node_id)
            elif score < filter_score:
                evicted_nodes.update(rated_list_data.nodes[node_id])
                evicted_nodes.update(rated_list_data.nodes[node_id].children)
        
        # if no nodes are filtered then reset the filter score to avg - 0.1. this will guarantee atleast one node.
        filter_score = sum([score for _, score in scores])/ len(scores) - 0.1

            
    return filtered_nodes
```

## Sample Distribution

### Custody requirement

Each node downloads and custodies a minimum of `CUSTODY_REQUIREMENT` subnets per slot. The particular subnets that the node is required to custody are selected pseudo-randomly (more on this below).

A node *may* choose to custody and serve more than the minimum honesty requirement. Such a node explicitly advertises a number greater than `CUSTODY_REQUIREMENT` through the peer discovery mechanism, specifically by setting a higher value in the `csc`(custody_subnet_count) field within its ENR. This value can be increased up to `DATA_COLUMN_SIDECAR_SUBNET_COUNT`, indicating a super-full node.

A node stores the custodied columns for the *duration of the pruning period* and responds to peer requests for samples on those columns.

### Public, deterministic selection

The particular columns that a node custodies are selected pseudo-randomly as a function (`get_custody_columns`) of the node-id and custody size -- importantly this function can be run by any party as the inputs are all public.

*Note*: increasing the `custody_size` parameter for a given `node_id` extends the returned list (rather than being an entirely new shuffle) such that if `custody_size` is unknown, the default `CUSTODY_REQUIREMENT` will be correct for a subset of the node's custody.

```python
def get_custody_columns(node_id: NodeID, custody_subnet_count: uint8) -> Sequence[ColumnIndex]:
    assert custody_subnet_count <= DATA_COLUMN_SIDECAR_SUBNET_COUNT

    subnet_ids: List[uint64] = []
    current_id = uint256(node_id)
    while len(subnet_ids) < custody_subnet_count:
        subnet_id = (
            bytes_to_uint64(hash(uint_to_bytes(uint256(current_id)))[0:8])
            % int(DATA_COLUMN_SIDECAR_SUBNET_COUNT)
        )
        if subnet_id not in subnet_ids:
            subnet_ids.append(subnet_id)
        if current_id == UINT256_MAX:
            # Overflow prevention
            current_id = NodeID(0)
        current_id += 1

    assert len(subnet_ids) == len(set(subnet_ids))

    columns_per_subnet = NUMBER_OF_COLUMNS // int(DATA_COLUMN_SIDECAR_SUBNET_COUNT)
    return sorted([
        ColumnIndex(int(DATA_COLUMN_SIDECAR_SUBNET_COUNT) * i + subnet_id)
        for i in range(columns_per_subnet)
        for subnet_id in subnet_ids
    ])
```

### Samples

In the current state of DAS, blobs are extended using a one-dimensional erasure coding extension. The matrix comprises maximum `MAX_BLOBS_PER_BLOCK` rows and fixed `NUMBER_OF_COLUMNS` columns, with each row containing a `Blob` and its corresponding extension. Each column in the matrix is a sample with its id(`SampleId`) equal to the index of the column.

### Sample Gossip Parameters

For each sample -- use `data_sidecar_{subnet_id}` subnets, where `subnet_id` can be computed with the `compute_subnet_for_data_sidecar(sample_id: SampleId)` helper.

```python
def compute_subnet_for_data_sidecar(sample_id: SampleId) -> SubnetID:
    return SubnetID(sample_id % DATA_COLUMN_SIDECAR_SUBNET_COUNT)
```

Verifiable samples(matrix columns) are distributed on the assigned subnet. To custody a particular sample, a node joins the respective gossipsub subnet. If a node fails to get a sample on the sample subnet, a node can also utilize the Req/Resp protocol to query the missing sample from other peers. The payload of the subnet is of type `DataSidecar`

```python
class DataSidecar:
    id: SampleId  # Index of column in extended matrix
    sample: List[Cell, MAX_BLOB_COMMITMENTS_PER_BLOCK]
    kzg_commitments: List[KZGCommitment, MAX_BLOB_COMMITMENTS_PER_BLOCK]
    kzg_proofs: List[KZGProof, MAX_BLOB_COMMITMENTS_PER_BLOCK]
    signed_block_header: SignedBeaconBlockHeader
    kzg_commitments_inclusion_proof: Vector[Bytes32, KZG_COMMITMENTS_INCLUSION_PROOF_DEPTH]
```

### Row (blob) custody

In the one-dimension construction, a node samples the peers by requesting the whole `DataColumnSidecar`. In reconstruction, a node can reconstruct all the blobs by 50% of the columns. Note that nodes can still download the row via `blob_sidecar_{subnet_id}` subnets.
