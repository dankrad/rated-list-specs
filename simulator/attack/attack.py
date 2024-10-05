import rustworkx as rx
import random


class AttackVec:
    def __init__(self, graph: rx.PyGraph):
        self.graph = graph

    def setup_attack(self):
        raise NotImplementedError("Override and implement")

    def is_malicious(self, node_id: int) -> bool:
        raise NotImplementedError("Override and implement")


class SybilAttack(AttackVec):
    def __init__(self, graph: rx.PyGraph, sybil_nodes: int):
        super().__init__(graph)
        self.sybil_nodes = sybil_nodes
        self.malicious_nodes = set()

    def setup_attack(self):
        all_nodes = list(self.graph.nodes())
        sybil_nodes = random.sample(all_nodes, self.sybil_nodes)
        self.malicious_nodes.update(sybil_nodes)

        for sybil in sybil_nodes:
            neighbors = random.sample(all_nodes, random.randint(1, 5))
            for neighbor in neighbors:
                if not self.graph.has_edge(sybil, neighbor):
                    self.graph.add_edge(sybil, neighbor, None)

        # print(f"Sybil nodes {self.malicious_nodes}")

    def is_malicious(self, node_id: int) -> bool:
        return node_id in self.malicious_nodes
