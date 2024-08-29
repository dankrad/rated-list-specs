from simulator import Simulator
from node import Node
import secrets
from eth2spec.utils.ssz.ssz_typing import Bytes32


def generate_node_ids(count):
    ids = []
    for i in range(count):
        ids.append(secrets.token_bytes(32))

    return ids


def main():
    print(generate_node_ids(32))
    node = Node(secrets.token_bytes(32), generate_node_ids(50))


if __name__ == "__main__":
    main()
