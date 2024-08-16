---
title: Untitled

---

Node structure:
- Node ID (node_id): A unique identifier for the node.
- State (state): The current status of the node, such as "active" or "inactive."
- Role (role): Indicates whether the node is a parent or a child.
- Peers (peers): Lists all nodes directly connected to this node, with each peer including its ID, state, and role.


#### `Node structure`

```python
    def __init__(self, node_id, state, role):
        self.node_id = node_id
        self.state = state
        self.role = role
        self.peers = []
        self.block = None  
```

BLock (block): Each node will generate a block and each block will have a score.
#### `Block`
```python
    def __init__(self):
        # Initially, let's assume the block has no response (inactive)
        self.active = False

    def get_status(self):
        # Return the status as a numerical value: 1 for active, 0 for inactive
        return 1 if self.active else 0
        
```

From a p2p graph to generate a peers. 
#### `Graph to get_peer`
```python
class Graph:
    def __init__(self):
        self.peer_list = defaultdict(list)  # Stores adjacency list of nodes
        self.visited_children = set()  # Tracks visited child nodes

    def add_edge(self, node_i, node_j):
        # Adds an undirected edge between node_i and node_j
        self.peer_list[node_i].append(node_j)
        self.peer_list[node_j].append(node_i)

    def get_peers(self, node):
        # Returns all direct neighbors (peers) of the specified node
        return self.peer_list[node]
```

#### class TreeBuilder
```python
    def __init__(self, graph):
        self.graph = graph  # Reference to the graph object
        self.tree = defaultdict(list)  # Initializes the tree structure
        self.visited = set()  # Tracks visited nodes to avoid cycles
```
#### bfs_build_tree
```python
    def bfs_build_tree(self, root, T):
        # Builds the tree using BFS from the root up to depth T
        queue = deque([(root, 0)])  # Queue for BFS, stores nodes and their level
        while queue:
            current_node, level = queue.popleft()
            if current_node not in self.visited:
                self.visited.add(current_node)
                if level < T:  # Continue if the current level is below the threshold T
                    for neighbor in self.graph.get_peers(current_node):
                        if neighbor not in self.visited:
                            self.tree[current_node].append(neighbor)
                            self.graph.visited_children.add(neighbor)  # Mark as visited child
                            queue.append((neighbor, level + 1))
        return self.build_tree_iterative(root, 0)
```
#### build_tree_iterative
```python
    def build_tree_iterative(self, root, T):
        # Builds the tree iteratively to manage depth level accurately
        def recurse_build(current_node, current_level):
            if current_level >= T or current_node in self.graph.visited_children:
                return {"node": current_node, "type": "parent"}  # Mark as parent if conditions met
            self.graph.visited_children.add(current_node)
            children = self.tree[current_node]
            subtree = {
                "node": current_node,
                "type": "parent" if children else "child",  # Determine if node is parent or child
                "children": [recurse_build(child, current_level + 1) for child in children if child not in self.graph.visited_children]
            }
            return subtree

        return recurse_build(root, 0)
```

#### compute_score
```python
   def compute_score(self):
        # Interact with the block to determine its status
        self.block.interact()
        if self.children:  # If the node has children, compute the average score
            total_score = sum(child.compute_score() for child in self.children)
            self.score = total_score / len(self.children)
        else:
            self.score = self.block.get_status()  # Leaf node uses its own block's status
        return self.score
```
#### Tree_scores
```python
    def compute_tree_scores(self, root):
        return root.compute_score()
```