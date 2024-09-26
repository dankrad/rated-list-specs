---
title: Draft

---

# Rated List specificetions

## Constants

| Name                                  |   Value                   |
|---------------------------------------|---------------------------|
| `MAX_BLOBS_PER_BLOCK`                 | 256                       |
| `NUM_ROWS = NUM_COLS`                 | 512                       |
| `UINT256_MAX`                         | `uint256(2**256 - 1)`     |
| `MAX_BLOB_COMMITMENTS_PER_BLOCK`      | 256                       |
| `CUSTODY_REQUIREMENT`                 | 2                         |
| `MAX_TREE_DEPTH`                      | 3                         | 
| `MAX_CHILDREN`                        | 100                       |
| `MAX_PARENTS`                         | 100                       |
| `NUM_OF_ROW_OR_COL_SUBNETS`           | (64)TBD                   |

## Custom types

### Basic types

| Name                                  |   Type                    |
|---------------------------------------|---------------------------|
| RowIndex                              | uint64                    |
| ColumnIndex                           | uint64                    |
| Cell                                  | ByteVector[512]           |
| KZGProof                              | Bytes48                   |
| NodeId                                | Bytes32                   |
| CustodySize                           | uint64                    |
| SubnetId                              | uint64                    |

### `SampleId`

We will represent SampleIds as a tuple of integers

```python
SampleId = Tuple[RowIndex, ColumnIndex]
```

### `NodeRecord`

```python
@dataclass
class NodeRecord:
    node_id: NodeId
    custody_size: CustodySize
    children: List[NodeId, MAX_CHILDREN]
    parents: List[NodeId, MAX_PARENTS] # creates a doubly linked list
```

### ScoreKeeper

Data type to keep the score for one DAS query (corresponding to one block)

```python
@dataclass
class ScoreKeeper:
    descendants_contacted: Dict[NodeId, Set[Tuple[NodeId, SampleId]]]
    descendants_replied: Dict[NodeId, Set[Tuple[NodeId, SampleId]]]
```


### RatedListData

Data type to keep all information required to maintain a rated list instance

```python
@dataclass
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
def on_get_peers_response(rated_list_data: RatedListData, node_id: NodeId, peers: Sequence[(NodeId, CustodySize)]):
    
    for peer_id, custody_size in peers:
        child_node: NodeRecord = None

        if peer_id not in rated_list_data.nodes: 
            child_node = NodeRecord(peer_id, custody_size, [], [])
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
def add_samples_on_entry(rated_list_data: RatedListData, node_id: NodeId, custody_size: CustodySize):
    row_ids, col_ids = get_custody_rows_and_columns(node_id, custody_size)
    
    for i, row_id in enumerate(row_ids):
        sample_id = SampleId((row_id, i))
        if not rated_list_data.sample_mapping[sample_id]:
            rated_list_data.sample_mapping[sample_id] = set()
    
        rated_list_data.sample_mapping[sample_id].update(node_id)
    
    for i, col_id in enumerate(col_ids):
        sample_id = SampleId((i, col_id))
        if not rated_list_data.sample_mapping[sample_id]:
            rated_list_data.sample_mapping[sample_id] = set()
    
        rated_list_data.sample_mapping[sample_id].update(node_id)
```

### `remove_samples_on_exit`

```python
def remove_samples_on_exit(rated_list_data: RatedListData, node_id: NodeId, custody_size: CustodySize):
    row_ids, col_ids = get_custody_rows_and_columns(node_id, custody_size)
    
    for i, row_id in enumerate(row_ids):
        sample_id = SampleId((row_id, i))
        if not rated_list_data.sample_mapping[sample_id]:
            rated_list_data.sample_mapping[sample_id] = set()
    
        rated_list_data.sample_mapping[sample_id].remove(node_id)
    
    for i, col_id in enumerate(col_ids):
        sample_id = SampleId((i, col_id))
        if not rated_list_data.sample_mapping[sample_id]:
            rated_list_data.sample_mapping[sample_id] = set()
    
        rated_list_data.sample_mapping[sample_id].remove(node_id)
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

## Samples and Distribution

As per the fulldanksharding proposal, the protocol supports 256 blobs, each of size of 128KB. 
1. ***Matrix Construction***: Each `Blob` is divided into 256 `Cell`s. All the blobs stacked one over the other gives us a matrix of size of 256x256 cells.
    * Each `Cell` is then 512 bytes of blob data. 
2. ***Matrix Extension***: The matrix is first extended row-wise and then column-wise using Reed-Solomon codes to gives us a matrix of size 512x512 cells. This is the final size of the matrix, hence `NUM_ROWS = 512 = NUM_COLS`
3. ***Matrix Integrity***: KZG Polynomial Commitments are used to prove the membership of each cell in a matrix. Each `Cell` then is accompanied with a KZG opening proof to make a `Sample`. The proofs are made against commitments which are part of the block header.
    * Each KZG opening/proof is 48 bytes in size making the `Sample` 560 bytes in size (without other metdata)

```python
@dataclass
class Sample(Container):
    cell: Cell
    kzg_proof: KZGProof
    id: SampleId
```

### Custody

Participating nodes custody entire rows and columns but sampling peers download individual samples. Each node downloads and custodies a minimum of `CUSTODY_REQUIREMENT` number of rows and columns per slot. The particular rows and columns  that the node is required to custody are selected pseudo-randomly using `get_custody_rows_and_columns`. A node *may* choose to custody and serve more than the minimum honesty requirement. Such a node explicitly advertises a number greater than `CUSTODY_REQUIREMENT` through the peer discovery mechanism, specifically by setting a higher value in the `custody_size` field within its ENR. This value can be increased up to `NUM_ROWS = NUM_COLS`, indicating a super-full node.

The below function can be run by any party as the inputs are all public. Increasing the `custody_size` parameter for a given `node_id` extends the returned list (rather than being an entirely new shuffle) such that if `custody_size` is unknown, the default `CUSTODY_REQUIREMENT` will be correct for a subset of the node's custody.

```python
def get_custody_rows_and_columns(node_id: NodeId, custody_size: CustodySize) -> (Sequence[RowIndex], Sequence[ColumnIndex]):
    assert custody_subnet_count <= NUM_ROWS

    row_ids: List[RowIndex] = []
    col_ids: List[ColumnIndex] = []

    current_id = uint256(node_id)

    while len(row_ids) < custody_size:
        row_id = (
            bytes_to_uint64(hash(uint_to_bytes(current_id))[0:8])
            % int(NUM_ROWS)
        )

        col_id = (
            bytes_to_uint64(hash(uint_to_bytes(current_id))[8:16])
            % int(NUM_COLS)
        )

        if row_id not in row_ids:
            row_ids.append(row_id)
        
        if col_id not in col_ids:
            col_ids.append(col_id)

        if current_id == UINT256_MAX:
            # Overflow prevention
            current_id = NodeID(0)
        current_id += 1

    assert len(row_ids) == len(set(row_ids))
    assert len(col_ids) == len(set(col_ids))

    return (sorted([RowIndex(row_id) for row_id in row_ids]), sorted([ColumnIndex(col_id) for col_id in col_ids]))
```

For each custodied row or column, nodes use `data_sidecar_{row/column}_{subnet_id}` subnets, where `subnet_id` can be computed with the `compute_subnet_for_data_sidecar(index: uint64)` helper.

```python
def compute_subnet_for_data_sidecar(index: Union[ColumnIndex, RowIndex]) -> SubnetId:
    return uint64(index % NUM_OF_ROW_OR_COL_SUBNETS)
```

These subnets are used to distribute samples belonging to the row or column. To custody a particular sample, a node joins the respective gossipsub subnet. If a node fails to get a row/column on the subnet, a node can also utilize the Req/Resp protocol to query the missing row/column from other peers. Every row or column distributed as a custody sample is of type `DataSidecar`. As a matter of fact, `DataSideCar` is just list of samples that a node requests for. In the case of custody the requested samples belong to the same row or column. A node stores the custodied rows and columns for the *duration of the pruning period* and responds to peer requests for samples.

```python
class DataSidecar:
    samples: List[Sample, NUM_ROWS]
```

*Note: It is assumed that the kzg commitments and their inclusion proofs are gossiped along with the block header on a seperate subnet.*
