import rustworkx as rx
import random


class NodeBehaviour:
    def should_respond(self, node_vertice: int) -> bool:
        raise NotImplementedError("Override and implement")


class AttackVec(NodeBehaviour):
    def __init__(self, graph: rx.PyGraph):
        super().__init__()
        self.graph = graph

    def setup_attack(self):
        raise NotImplementedError("Override and implement")


class SybilAttack(AttackVec):
    def __init__(self, graph: rx.PyGraph, sybil_rate: float):
        super().__init__(graph)
        self.num_sybil_nodes = int(graph.num_nodes() * sybil_rate)
        self.malicious_nodes = set()

    def setup_attack(self):
        all_nodes = list(self.graph.nodes())
        sybil_nodes = random.sample(all_nodes, self.num_sybil_nodes)
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
