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
    score: int32
```

#### `RatedList`

```python
RatedList = Dict[NodeId, NodeRecord] # A flat routing table makes it easier to manage queries
```

#### `IdList`

```python
IdList = List[NodeId, MAX_ID_LIST]
```

#### `create_empty_peer`

```python
def create_empty_node_record(id: NodeId) -> Peer:
    """ TODO: Add a description here """
    
    node_record = NodeRecord(
        node_id: NodeId,
        level: 255,
        status_active: False, 
        last_queried_slot: 0, 
        is_evicted: False, 
        children: None, 
        parents: None, 
        score: float
    )

    return node_record
```

#### `add_children`

TODO: Check the sanity of this function.

TODO: I'm not a pythonista and I have assumed that objects are always referred (as pointers) instead of copied. we should check this to either keep or remove the last if condition

```python
def add_children(rated_list: RatedList, node: NodeRecord, id_list: IdList):
    
    if node.level >= MAX_TREE_DEPTH:
        return

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

#### `compute_score`

```python
def compute_score(node: NodeRecord) -> float:
    # Interact with the block to determine its status
    # self.block.interact()
    if node.children:  # If the node has children, compute the average score
        total_score = sum(compute_score(child) for child in node.children)
        node.score = total_score / len(node.children)
    else:
        # score = self.block.get_status()  # Leaf node uses its own block's status
        node.score = 1.0 if node.status_active else 0.0
    
    return node.score
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
