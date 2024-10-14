import rustworkx as rx
import random


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


# There are various interpretations of an eclipse attack.
# 1. The attack can be directly on the rated list node. This would hardly provide any
#    benefit since the node
# 2. The attack can be on a node in the network to bring down it's score or partition
#    it's view of the network
# 3. The attack can be made on another malicious node to bring down it's score
#    and therefore lessen the obligation of serving samples.
class EclipseAttack(AttackVec):
    def __init__(self, graph: rx.PyGraph, compromised_node: int, eclipse_rate: int):
        super().__init__(graph)
        self.malicious_nodes = set()
        self.compromised_node = compromised_node
        self.eclipse_rate = eclipse_rate

    def setup_attack(self):
        self.malicious_nodes = set(self.graph.neighbors(self.compromised_node))
        self.num_attack_nodes = len(self.malicious_nodes)

    def should_respond(self, node_vertice: int) -> bool:
        return node_vertice in self.malicious_nodes


class BalancingAttack(AttackVec):
    """
    here we are trying to make a small subset of nodes at each malicious in intend to bring down
    the average confidence score that increase the chance of picking malicious subtree in other
    branches of the graph
    """

    def __init__(self, graph: rx.PyGraph, root_node: int):
        super().__init__(graph)
        self.root_node = root_node
        self.malicious_nodes = set()

    def recursively_add_children(self, parent, node, factor, depth=0):
        if depth == 3:
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

        malicious_subtree_root = random.choice(
            self.graph.neighbors(self.root_node))
        # offline an entire subtree bringing the global confidence score down
        # self.recursively_add_children(None, malicious_subtree_root,1)
        self.num_attack_nodes = len(self.malicious_nodes)
        print(f"malicious nodes={self.num_attack_nodes}")

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
        self.recursively_add_children(
            self.parent_sub_root, self.defunct_sub_root)
        self.num_attack_nodes = len(self.malicious_nodes)

    def should_respond(self, node_vertice: int) -> bool:
        return node_vertice in self.malicious_nodes
