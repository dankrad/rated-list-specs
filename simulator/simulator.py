import rustworkx as rx
import random as rn
import queue
from dataclasses import dataclass
from collections import deque
from typing import Tuple, List

# Project specific
from attack import AttackVec
import node as rl_node
from utils import int_to_bytes, bytes_to_int
from node import (
    DATA_COLUMN_SIDECAR_SUBNET_COUNT,
    MAX_CHILDREN,
    NodeId,
    SampleId,
    Root,
    MAX_TREE_DEPTH,
    RatedListData,
    NodeRecord,
)


@dataclass
class RequestQueueItem:
    node_id: NodeId
    sample_id: SampleId
    block_root: Root


class SimulatedNode:
    def print_debug(self, *args):
        if self.debug:
            print(args)

    def __init__(
        self,
        graph: rx.PyGraph,
        attack: AttackVec,
        binding_vertex: int = None,
        debug: bool = False,
    ):
        self.debug = debug
        self.graph = graph
        self.request_queue = queue.Queue()
        self.attack = attack

        # calculate average degree of the graph
        sum = 0
        for node in self.graph.nodes():
            sum = sum + self.graph.degree(self.graph[node])

        self.print_debug("Average Degree:", sum / len(self.graph.nodes()))

        # map rated list node to one of the graph vertices
        if binding_vertex is None:
            binding_vertex = rn.choice(self.graph.node_indices())

        self.dht = RatedListData(
            NodeId(int_to_bytes(binding_vertex)), {}, {}, {})
        self.dht.nodes[self.dht.own_id] = NodeRecord(
            self.dht.own_id, set(), set())

        self.print_debug(
            "mapped rated list node to graph vertice " + str(binding_vertex)
        )

        self._construct_tree()

        self.print_debug("constructed the rated list")

        self.attack.setup_attack()

        self.print_debug("initialized the attack vector")

    def request_sample(self, node_id: NodeId, block_root: Root, sample: SampleId):
        self.print_debug("Requesting samples from", node_id)

        rl_node.on_request_score_update(self.dht, block_root, node_id, sample)
        self.request_queue.put(
            RequestQueueItem(node_id=node_id, sample_id=sample,
                             block_root=block_root)
        )

    def get_peers(self, node_id: NodeId):
        peers = []

        random_neighbors = list(self.graph.neighbors(bytes_to_int(node_id)))

        rn.shuffle(random_neighbors)

        for i, peer_id in enumerate(random_neighbors):
            # if i >= MAX_CHILDREN:
            #     break

            peer_id_bytes = NodeId(int_to_bytes(peer_id))
            peers.append(peer_id_bytes)
            rl_node.add_samples_on_entry(self.dht, peer_id_bytes)
        rl_node.on_get_peers_response(self.dht, node_id, peers)

    def process_requests(self) -> List[Tuple[RequestQueueItem, bool]]:
        request_status = []

        while not self.request_queue.empty():
            request: RequestQueueItem = self.request_queue.get()

            if not self.attack.should_respond(bytes_to_int(request.node_id)):
                self.print_debug("Rejected sample request", request)
                request_status.append((request, False))
                continue

            rl_node.on_response_score_update(
                self.dht,
                block_root=request.block_root,
                node_id=request.node_id,
                sample_id=request.sample_id,
            )
            request_status.append((request, True))

        return request_status

    def _construct_tree(self):
        self.print_debug("constructing the rated list tree from the graph")

        # iterative BFS approach to find peers
        # where max_tree_depth is parametrised
        queue = deque([(self.dht.own_id, 0)])

        while queue:
            current_node_id, current_level = queue.popleft()

            if current_level >= MAX_TREE_DEPTH:
                continue

            self.get_peers(current_node_id)

            for child_id in self.dht.nodes[current_node_id].children:
                # no point adding to the list if we are not gonna use the item
                if (current_level + 1) < MAX_TREE_DEPTH:
                    queue.append((child_id, current_level + 1))

    def is_ancestor(self, grand_child: NodeId, check_ancestor: NodeId) -> bool:
        # all nodes are children(grand or great grand
        # until tree depth) of root node
        if check_ancestor == self.dht.own_id:
            return True

        if check_ancestor == grand_child:
            return True

        if check_ancestor in self.dht.nodes[grand_child].parents:
            return True

        # assuming the grand_child is at the last
        # level check grand parents(level 1)
        for parent in self.dht.nodes[grand_child].parents:
            if check_ancestor in self.dht.nodes[parent].parents:
                return True

            # if our assumption is wrong the parents are the root node itself
            if parent == self.dht.own_id:
                return False

        return False

    def query_samples(self, block_root: Root, querying_strategy):
        sampling_result = {"evicted": set(), "filtered": set(),
                           "malicious": set()}
        
        count = 0

        # using a random block root just for initial testing
        for sample in range(DATA_COLUMN_SIDECAR_SUBNET_COUNT):
            # NOTE: technically all samples must be in the mapping.
            # we just need enough nodes in the network
            if sample not in self.dht.sample_mapping:
                self.print_debug(
                    "No record of nodes that serve sample: " + str(sample))
                continue

            filtered_nodes = rl_node.filter_nodes(self.dht, block_root, sample)

            # calculate the set of evicted nodes a.k.a nodes not filtered
            all_nodes = self.dht.sample_mapping[sample]
            filtered_set = set([node for node, _ in filtered_nodes])

            sampling_result["filtered"].update(filtered_set)
            sampling_result["evicted"].update(all_nodes - filtered_set)

            # remove nodes that were filtered before but were evicted later
            sampling_result["filtered"] -= sampling_result["evicted"]

            if querying_strategy == "all":
                for node, _ in filtered_nodes:
                    count+=1
                    self.request_sample(node, block_root, sample)
                    

                result = self.process_requests()

                for response in result:
                    if (
                        response[0].node_id in filtered_nodes
                        and response[0].sample_id == sample
                        and response[0].block_root == block_root
                        and response[1]
                    ):
                        sampling_result[sample] = True
            else:
                if querying_strategy == "high":
                    # sort the list in descending order
                    sorted(filtered_nodes, key=lambda a: a[1], reverse=True)
                elif querying_strategy == "low":
                    # sort the list in ascending order
                    sorted(filtered_nodes, key=lambda a: a[1], reverse=False)
                else:
                    filtered_nodes = rn.shuffle(filtered_nodes)

                for node, _ in filtered_nodes:
                    count+=1
                    self.request_sample(node, block_root, sample)
                    
                    # since we make only request the result would contain only one item
                    result = self.process_requests()[0]

                    # if the request was successful break out of the loop
                    if (
                        result[0].node_id == node
                        and result[0].sample_id == sample
                        and result[0].block_root == block_root
                        and result[1]
                    ):
                        sampling_result[sample] = True
                        break
                    
            
            if sample not in sampling_result:
                self.print_debug(f"sampleId={sample} was not found in the network sample_mapping={self.dht.sample_mapping[sample]}")
                self.print_debug(f"total honest nodes selected for sampleId={sample} nodes={self.dht.sample_mapping[sample]-(all_nodes-filtered_nodes)}")
                sampling_result[sample] = False

        malicious_nodes = self.attack.get_malicious_nodes()
        sampling_result["malicious"] = set(
            [NodeId(int_to_bytes(id)) for id in malicious_nodes]
        )

        print(f"total requests={count}")
        return sampling_result

    def print_report(self, report):
        # Positive Outcome of rated list:
        #     to evict malicious nodes
        # False Positive: evicting honest nodes
        # True Positive: evicting malicious nodes
        # False Negative: NOT evicting malicious nodes
        # True Negative: NOT evicting honest nodes
        
        print(f"Evicted Nodes: {len(report["evicted"])}")
        print(f"Malicious Nodes: {len(report["malicious"])}")
        print(f"Filtered Nodes: {len(report["filtered"])}")

        false_positives = set()
        for node in report["evicted"]:
            if node not in report["malicious"]:
                false_positives.add(node)

        true_positives = set()
        for node in report["evicted"]:
            if node in report["malicious"]:
                true_positives.add(node)

        true_negatives = set()
        for node in report["filtered"]:
            if node not in report["malicious"]:
                true_negatives.add(node)

        false_negatives = set()
        for node in report["filtered"]:
            if node in report["malicious"]:
                false_negatives.add(node)

        if (
            self.dht.own_id not in report["evicted"]
            or self.dht.own_id not in report["filtered"]
        ):
            report["filtered"].add(self.dht.own_id)

        if (len(true_positives) + len(false_negatives)) != len(report["malicious"]):
            print(f"number of malicious nodes doesn't match TP + FN")
            # raise Exception("number of malicious nodes doesn't match TP + FN")

        if (len(false_positives) + len(true_negatives)) != (
            self.graph.num_nodes() - len(report["malicious"])
        ):
            print(f"number of honest nodes doesn't match TN + FP")
            # raise Exception("number of honest nodes doesn't match TN + FP")

        print(
            f"False Positive Rate: {
                len(false_positives)/(len(false_positives) + len(true_negatives))}"
        )
        print(
            f"False Negative Rate: {
                len(false_negatives)/(len(false_negatives) + len(true_positives))}"
        )

        count = 0
        for sample in range(DATA_COLUMN_SIDECAR_SUBNET_COUNT):
            if sample in report:
                if report[sample]:
                    count += 1

        print(f"Obtained Samples: {count}/{DATA_COLUMN_SIDECAR_SUBNET_COUNT}")
