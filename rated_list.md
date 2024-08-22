---
title: Draft

---

# Rated List specificetions

## Constants

The below constants assume a max node degree of 100

|     Name         | Value     |
|------------------|-----------|
| MAX_TREE_DEPTH   | 3         | 
| MAX_ID_LIST      | 100       | 
| MAX_CHILDREN     | 100       |
| MAX_PARENTS      | 100       |


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
    children: List[NodeRecord, MAX_CHILDREN]
    parents: List[NodeRecord, MAX_PARENTS] # creates a doubly linked list
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
    nodes: Dict[NodeId, NodeRecord]
    scores: Dict[Bytes32, ScoreKeeper]
```


#### `create_empty_node_record`

```python
def create_empty_node_record(id: NodeId) -> NodeRecord:
    """ TODO: Add a description here """
    
    node_record = NodeRecord(
        node_id: NodeId,
        children: [], 
        parents: []
    )

    return node_record
```

### `compute_descendant_score`

```python
def compute_descendant_score(rated_list_data: RatedListData,
                             block_root: Root,
                             node_id: NodeId) -> float:
   score_keeper = rated_list_data.scores[block_root]
   return score_keeper.descendants_contacted[node_id] /
          score_keeper.descendants_replied[node_id]
```

#### `compute_node_score`

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

#### `on_get_peers_response`

Function that is called whenever we get the peer list of a node.

```python
def on_get_peers_response(rated_list_data: RatedListData, node: NodeId, children: Sequence[NodeId]):
    
    for child_id in children:
        child_node: NodeRecord = None

        if child_id not in rated_list_data.nodes: 
            child_node = create_empty_node_record(child_id)
            rated_list_data.nodes[child_id] = child_node

        rated_list_data.nodes[child_id].parents.add(node)
        rated_list_data.nodes[node].children.add(child_node)

    for child_id in rated_list_data.nodes[node].children:
        if child_id not in children:
            # Node no longer has child peer, remove link
            rated_list_data.nodes[node].children.remove(child_id)
            rated_list_data.nodes[child_id].parents.remove(node)
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
