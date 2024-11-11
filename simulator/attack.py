import rustworkx as rx
from node import MAX_TREE_DEPTH
import random
import logging 


class NodeBehaviour:
    def should_respond(self, node_vertice: int) -> bool:
        raise NotImplementedError("Override and implement")


class AttackVec(NodeBehaviour):
    def __init__(self, graph: rx.PyGraph, num_attack_nodes: int = 0):
        super().__init__()
        self.graph = graph
        self.num_attack_nodes = num_attack_nodes

    def setup_attack(self):
        raise NotImplementedError("Override and implement")

    def get_malicious_nodes(self):
        raise NotImplementedError("Override and implement")


class SybilAttack(AttackVec):
    def __init__(self, graph: rx.PyGraph, sybil_rate: float):
        super().__init__(graph)
        self.num_attack_nodes = int(graph.num_nodes() * sybil_rate)
        self.malicious_nodes = set()

    def setup_attack(self):
        all_nodes = list(self.graph.nodes())
        sybil_nodes = random.sample(all_nodes, self.num_attack_nodes)
        self.malicious_nodes.update(sybil_nodes)

        # we go an extra step to create random connections with more peers
        # this might prove useful with the provided graph is not random
        for sybil in sybil_nodes:
            neighbors = random.sample(all_nodes, random.randint(1, 5))
            for neighbor in neighbors:
                if not self.graph.has_edge(sybil, neighbor):
                    self.graph.add_edge(sybil, neighbor, None)

        # print(f"Sybil nodes {self.malicious_nodes}")

    def should_respond(self, node_vertice: int) -> bool:
        return node_vertice not in self.malicious_nodes

    def get_malicious_nodes(self):
        return self.malicious_nodes


class EclipseAttack(AttackVec):
    def __init__(self, graph: rx.PyGraph, compromised_node: int, eclipse_rate: int):
        super().__init__(graph)
        self.malicious_nodes = set()
        self.compromised_node = compromised_node
        # TODO: Use the rate to measure the amount of nodes required to eclipse a node
        self.eclipse_rate = eclipse_rate

    def setup_attack(self):
        self.malicious_nodes = set(self.graph.neighbors(self.compromised_node))
        self.num_attack_nodes = len(self.malicious_nodes)

    def should_respond(self, node_vertice: int) -> bool:
        return node_vertice not in self.malicious_nodes

    def get_malicious_nodes(self):
        return self.malicious_nodes


class BalancingAttack(AttackVec):
    """
    We try to favor a set of nodes/subtree over others by posioning other subtrees
    with malicious nodes and bringing their score down
    """

    def __init__(self, graph: rx.PyGraph, root_node: int):
        super().__init__(graph)
        self.root_node = root_node
        self.malicious_nodes = set()

    def recursively_add_children(self, parent, node, factor, depth=0):
        if depth == MAX_TREE_DEPTH:
            return
        depth += 1
        neighbours = self.graph.neighbors(node)
        for peer in random.sample(list(neighbours), int(len(neighbours) * factor)):
            if peer != parent:
                self.malicious_nodes.add(peer)
                self.recursively_add_children(node, peer, factor, depth)

    def setup_attack(self):
        honest_node = random.choice(self.graph.neighbors(self.root_node))
        # we try to poison one of the honest subtree
        self.recursively_add_children(None, honest_node, 0.3)

        malicious_subtree_root = random.choice(self.graph.neighbors(self.root_node))
        # offline an entire subtree bringing the global confidence score down
        # self.recursively_add_children(None, malicious_subtree_root,1)
        self.num_attack_nodes = len(self.malicious_nodes)
        logging.debug(f"malicious nodes={self.num_attack_nodes}")

    def should_respond(self, node_vertice: int) -> bool:
        return node_vertice not in self.malicious_nodes

    def get_malicious_nodes(self):
        return self.malicious_nodes


class DefunctSubTreeAttack(AttackVec):
    def __init__(self, graph: rx.PyGraph, defunct_sub_root: int, parent_sub_root: int):
        super().__init__(graph)
        self.parent_sub_root = parent_sub_root
        self.defunct_sub_root = defunct_sub_root
        self.malicious_nodes = set()

    def recursively_add_children(self, parent, node, depth=0):
        if depth == MAX_TREE_DEPTH:
            return

        for peer in self.graph.neighbors(node):
            if peer != parent:
                self.malicious_nodes.add(peer)
                self.recursively_add_children(node, peer, depth + 1)

    def setup_attack(self):
        self.recursively_add_children(self.parent_sub_root, self.defunct_sub_root, 1)
        self.num_attack_nodes = len(self.malicious_nodes)

    def should_respond(self, node_vertice: int) -> bool:
        return node_vertice not in self.malicious_nodes

    def get_malicious_nodes(self):
        return self.malicious_nodes


class CollusionAttack(AttackVec):
    def __init__(self, graph: rx.PyGraph,sybil_rate=0.2):
        super().__init__(graph)
        self.malicious_nodes = set()
        self.sybil_rate = sybil_rate

    def recursively_add_children(self, malicious_roots):
        for root in malicious_roots:
            for level1 in self.graph.neighbors(root):
                for level2 in self.graph.neighbors(level1):
                    self.malicious_nodes.add(level2)
    
    
    def setup_attack(self):
        random_malicious_roots = random.sample(self.graph.node_indexes(),(self.sybil_rate*self.graph.num_nodes())/(50*50)) # degree 50
        self.recursively_add_children(random_malicious_roots)
        self.num_attack_nodes = len(self.malicious_nodes)