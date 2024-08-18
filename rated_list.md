---
title: Draft

---

#### `Peer`

```python
@dataclass
class Peer:
    peer_id: NODE_ID
    level: uint8
    status_active: bool # redundant variable to last_queried_slot but can be useful.
    last_queried_slot: Slot # tracks the last slot the peer was seens as active
    is_evicted: bool # helps to mark a peer for eviction so that a routine task can remove it
    children: List[Peer, MAX_CHILDREN_PER_PEER]
    parents: List[Peer, MAX_PARENTS_PER_PEER] # creates a doubly linked list
    score: int32
```

#### `RatedList`

```python
RatedList = Dict[NODE_ID, Peer] # A flat routing table makes it easier to manage queries
```

#### `Node`

```python
@dataclass
class Node:
    rated_list: RatedList
    tree_root: Peer
```

#### `IdList`

```python
IdList = List[NODE_ID, MAX_ID_LIST]
```

#### `create_empty_peer`

```python
def create_empty_peer(id: NODE_ID) -> Peer:
    """ TODO: Add a description here """
    
    peer = Peer(
        peer_id: id,
        level: 255,
        status_active: False, 
        last_queried_slot: 0, 
        is_evicted: False, 
        children: None, 
        parents: None, 
        score: float
    )

    return peer_list
```

#### `add_children`

TODO: Check the sacntity of this function. Combines logic of `bfs_build_tree` and `build_tree_iterative` from previous version of the draft
```python
def add_children(rated_list: RatedList, peer: Peer, id_list: IdList):
    
    if peer.level >= MAX_TREE_DEPTH:
        return

    for id in id_list:
        child_peer: Peer = None

        if id not in rated_list: 
            child_peer = create_empty_peer(id)
        elif not rated_list[id].level <= peer.level:
            child_peer = rated_list[id]
            if rated_list[id].level != peer.level + 1:\
                child_peer.parents = []
        else:
            continue

        child_peer.level = peer.level + 1
        child_peer.parents.append(peer)
        
        if child_peer.last_queried_slot != CURRENT_SLOT:
            success, res_list = send_heartbeat(id)
            
            if success and len(res_list) > 0:
                child_peer.last_queried_slot = CURRENT_SLOT
                child_peer.status_active = True

                # makes the algorithm depth-first. advantage is we don't require hold information in memory
                # but we do spend stack memory for it (recursion)
                add_children(rated_list, child_peer, res_list)
            else:
                child_peer.last_queried_slot = CURRENT_SLOT
                child_peer.status_active = False

        peer.children.append(child_peer)
    return
```

#### `compute_score`

```python
def compute_score(peer: Peer) -> float:
    # Interact with the block to determine its status
    # self.block.interact()
    if peer.children:  # If the node has children, compute the average score
        total_score = sum(compute_score(child) for child in peer.children)
        peer.score = total_score / len(peer.children)
    else:
        # score = self.block.get_status()  # Leaf node uses its own block's status
        peer.score = 1.0 if peer.status_active else 0.0
    
    return peer.score
```

#### `evict_nodes`
TODO
