import rustworkx as rx
import random
from node import NodeId
from utils import bytes_to_int


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
        return node_vertice in self.malicious_nodes


class AcyclicTestAttack(AttackVec):
    def __init__(self, graph: rx.PyGraph, defunct_sub_root: int, parent_sub_root: int):
        super().__init__(graph)
        self.parent_sub_root = parent_sub_root
        self.defunct_sub_root = defunct_sub_root
        self.malicious_nodes = set()

    def recursively_add_children(self, parent, node):
        for peer in self.graph.neighbors(node):
            if peer != parent:
                self.malicious_nodes.add(peer)
                self.recursively_add_children(node, peer)

    def setup_attack(self):
        self.recursively_add_children(self.parent_sub_root, self.defunct_sub_root)
        self.num_attack_nodes = len(self.malicious_nodes)

    def should_respond(self, node_vertice: int) -> bool:
        return node_vertice in self.malicious_nodes
