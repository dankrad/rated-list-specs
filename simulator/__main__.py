from dascore import get_custody_columns
from node import Node
from utils import NodeId
import secrets
from networkx import graph
from simulator import Simulator


def generate_node_ids(count):
    ids = []
    for i in range(count):
        ids.append(secrets.token_bytes(32))

    return ids


def main():
    ## start the simulator-> add peers to the node -> block production
    random_secret = secrets.token_bytes(32)
    peers = generate_node_ids(50)
    node = Node(random_secret, generate_node_ids(50))
    
    G = graph.Graph()
    sim = Simulator(node, G)
    sim.run([NodeId(node_id) for node_id in peers])
    


if __name__ == "__main__":
    main()
