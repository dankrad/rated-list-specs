from eth2spec.utils.ssz.ssz_typing import uint256, uint64, uint8
from typing import List, Sequence
from utils import NodeId, SampleId, bytes_to_uint64, uint_to_bytes, hash, ENDIANNESS

DATA_COLUMN_SIDECAR_SUBNET_COUNT = uint8(128)


NUMBER_OF_COLUMNS = uint8(128)


MIN_CUSTODY_COUNT = uint8(2)


UINT256_MAX = uint256(2**256 - 1)

# Rated List config

MAX_TREE_DEPTH = uint8(3)

MAX_CHILDREN = uint8(100)

MAX_PARENTS = uint8(100)



