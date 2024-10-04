import rustworkx as rx
from attack.attack import AttackVec

class NodeBehaviour:
    def __init__(self, graph: rx.PyGraph, attack: AttackVec):
        self.graph = graph
        self.attack = attack
        
    def init_attack(self):
        self.attack.setup_attack()
        
    def should_respond(self, node_id: int) -> bool:
        return self.attack.is_malicious(node_id=node_id)