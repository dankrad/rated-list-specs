from typing import * 

NodeId = int
SampleId = str
Root = str

MAX_CHILDREN = 100
MAX_PARENT = 100

class NodeRecord:
    def __init__(self, nodeId):
        self.nodeId = NodeId
        self.children : List[NodeRecord] = {}
        self.parents : List[NodeRecord] = {}

    def add_parent(self, nodeRecord):
        if self.parents.count >= MAX_PARENT:
            print("the max parent limit reached for the node")
            return 
        self.parents.append(nodeRecord)

    def add_children(self, nodeRecord):
        if self.children.count >= MAX_CHILDREN:
            print("the max children limit reached for the node")
            return 
        self.children.append(nodeRecord)

class RatedListDHT:
    """ This class implements the rated list data structure """
    
    def __init__(self):
        self.nodes : Dict[NodeId, NodeRecord] = {}
        self.scores : Dict[str, ScoreKeeper] = {}


class ScoreKeeper:
    """ This class implements the score keeper data structure"""
    def __init__(self):
        self.descendants_contacted: Dict[NodeId,Set[Tuple[NodeId, SampleId]]] = {}
        self.descendants_replied: Dict[NodeId,Set[Tuple[NodeId, SampleId]]] = {} 



class Node:
    """ This class implements a node in the network"""
    def __init__(self, ID):
        print(" starting a new node in the network")
        self.ID = ID
        self.dht = RatedListDHT()
        print(" started a node in the node with nodeId - %s",ID)

    def create_empty_node_record(self, id: NodeId) -> NodeRecord:
        node_record = NodeRecord(
            nodeId=id
        )

        return node_record
    
    """ Here the Root is a bytes32 string"""
    def compute_descendant_score(self,
                             block_root: Root,
                             node_id: NodeId) -> float:
        score_keeper = self.dht .scores[block_root]
        return score_keeper.descendants_contacted[node_id] / score_keeper.descendants_replied[node_id]
    
    def on_get_peers_response(self, node: NodeId, children: Sequence[NodeId]):
    
        for child_id in children:
            child_node: NodeRecord = None

            if child_id not in self.dht.nodes: 
                child_node = self.create_empty_node_record(child_id)
                self.dht.nodes[child_id] = child_node

            child_node.parents.append(node)
            
            if child_id not in self.dht.nodes:
                self.dht.nodes[child_id] = child_node

            self.dht.nodes[node].children.append(child_node)

        for child_id in self.dht.nodes[node].children:
            if child_id not in children:
                self.dht.nodes[node].children.remove(child_id)
                self.dht.nodes[child_id].parents.remove(node)
                if len(self.dht.nodes[child_id].parents) == 0:
                    self.dht.nodes.pop(child_id)



    def compute_node_score(self,
                       block_root: Root,
                       node_id: NodeId) -> float:
        

        score = self.compute_descendant_score(self.dht, block_root, node_id)

        cur_path_scores: Dict[NodeId, float] = {
            parent: score for parent in self.dht.nodes[node_id].parents
        }

        best_score = 0.0

        while cur_path_scores:
            new_path_scores: Dict[NodeId, float] = {}
            for node, score in cur_path_scores.items():
                for parent in self.dht.nodes[node].parents:
                    if parent == self.dht.own_id:
                        best_score = max(best_score, score)
                    else:
                        par_score = self.compute_descendant_score(self.dht, block_root, parent)
                        if parent not in new_path_scores or new_path_scores[parent] < par_score:
                            new_path_scores[parent] = par_score

            cur_path_scores = new_path_scores

        return best_score
    
    def on_get_peers_response(self, node: NodeId, children: Sequence[NodeId]):
    
        for child_id in children:
            child_node: NodeRecord = None

            if child_id not in self.dht.nodes: 
                child_node = self.create_empty_node_record(child_id)
                self.dht.nodes[child_id] = child_node

            child_node.parents.append(node)
            
            if child_id not in self.dht.nodes:
                self.dht.nodes[child_id] = child_node

            self.dht.nodes[node].children.append(child_node)

        for child_id in self.dht.nodes[node].children:
            if child_id not in children:
                self.dht.nodes[node].children.remove(child_id)
                self.dht.nodes[child_id].parents.remove(node)
                if len(self.dht.nodes[child_id].parents) == 0:
                    self.dht.nodes.pop(child_id)
 

    




    
        