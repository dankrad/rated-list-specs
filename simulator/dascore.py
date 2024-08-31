from eth2spec.utils.ssz.ssz_typing import uint256, uint64, uint8
from typing import List, Sequence
from utils import NodeId, SampleId, bytes_to_uint64, uint_to_bytes, hash, ENDIANNESS


DATA_COLUMN_SIDECAR_SUBNET_COUNT = uint8(128)
NUMBER_OF_COLUMNS = uint8(128)
MIN_CUSTODY_COUNT = uint8(2)
UINT256_MAX = uint256(2**256 - 1)


def get_custody_columns(
    node_id: NodeId, custody_subnet_count: uint8 = MIN_CUSTODY_COUNT
) -> Sequence[SampleId]:
    assert custody_subnet_count <= DATA_COLUMN_SIDECAR_SUBNET_COUNT

    subnet_ids: List[uint64] = []
    current_id = uint256(int.from_bytes(node_id,ENDIANNESS))

    while len(subnet_ids) < custody_subnet_count:
        subnet_id = bytes_to_uint64(
            hash(uint_to_bytes(uint256(current_id)))[0:8]
        ) % int(DATA_COLUMN_SIDECAR_SUBNET_COUNT)
        print(subnet_id)
        if subnet_id not in subnet_ids:
            subnet_ids.append(subnet_id)
        if current_id == UINT256_MAX:
            # Overflow prevention
            current_id = NodeId(0)
        current_id += 1

    assert len(subnet_ids) == len(set(subnet_ids))

    columns_per_subnet = NUMBER_OF_COLUMNS // int(DATA_COLUMN_SIDECAR_SUBNET_COUNT)
    return sorted(
        [
            SampleId(int(DATA_COLUMN_SIDECAR_SUBNET_COUNT) * i + subnet_id)
            for i in range(columns_per_subnet)
            for subnet_id in subnet_ids
        ]
    )
