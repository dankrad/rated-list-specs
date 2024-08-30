from dascore import get_custody_columns
from node import Node
import secrets


def generate_node_ids(count):
    ids = []
    for i in range(count):
        ids.append(secrets.token_bytes(32))

    return ids


def main():
    node = Node(secrets.token_bytes(32), generate_node_ids(50))
    print(get_custody_columns(secrets.token_bytes(32)))


if __name__ == "__main__":
    main()
