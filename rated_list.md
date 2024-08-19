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
    level: uint8
    status_active: bool # redundant variable to last_queried_slot but can be useful.
    last_queried_slot: Slot # tracks the last slot the node was seens as active
    is_evicted: bool # helps to mark a node for eviction so that a routine task can remove it
    children: List[NodeRecord, MAX_CHILDREN]
    parents: List[NodeRecord, MAX_PARENTS] # creates a doubly linked list
```

### ScoreKeeper

Data type to keep the score for one DAS query (corresponding to one block)

TODO: Currently this can only handle one query per node (per block). We should think how to score nodes that respond to some queries but not others.

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
        level: 255,
        status_active: False, 
        last_queried_slot: 0, 
        is_evicted: False, 
        children: None, 
        parents: None
    )

    return node_record
```

#### `add_children`

TODO: Check the sanity of this function.

TODO: I'm not a pythonista and I have assumed that objects are always referred (as pointers) instead of copied. we should check this to either keep or remove the last if condition

```python
def add_children(rated_list: NodeList, node: NodeRecord, id_list: IdList):
    
    if node.level >= MAX_TREE_DEPTH:
        return
Bytes32
    for id in id_list:
        child_node: NodeRecord = None

        if id not in rated_list: 
            child_node = create_empty_node_record(id)
            rated_list[id] = child_node
        elif not rated_list[id].level <= node.level:
            child_node = rated_list[id]
            if rated_list[id].level != node.level + 1:
                child_node.parents = []
        else:
            continue

        child_node.level = node.level + 1
        child_node.parents.append(node)
        
        if child_node.last_queried_slot != CURRENT_SLOT:
            success, res_list = get_peers(id)
            
            if success and len(res_list) > 0:
                child_node.last_queried_slot = CURRENT_SLOT
                child_node.status_active = True

                # makes the algorithm depth-first. advantage is we don't require hold information in memory
                # but we do spend stack memory for it (recursion)
                add_children(rated_list, child_node, res_list)
            else:
                child_node.last_queried_slot = CURRENT_SLOT
                child_node.status_active = False

        if id not in rated_list:
            rated_list[id] = child_node

        node.children.append(child_node)
    return
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
    
```

#### `evict_nodes`

```python
def evict_nodes(parent: NodeRecord, threshold: float):
    for child in parent.children:
        if child.score < threshold:
            parent.children.remove(child)
            child.parents.remove(parent)

        evict_nodes(child, threshold)
```

#### `get_peers`

This function is abstracted out to be defined by the underlying p2p network. However, it should be of the below signature

```python
def get_peers(id: NodeId) -> IdList
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