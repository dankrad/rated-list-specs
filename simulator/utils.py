from eth2spec.utils.ssz.ssz_typing import Bytes32, uint64, uint
from eth2spec.utils.ssz.ssz_impl import serialize
from node import NodeId
from hashlib import sha256
import secrets

ENDIANNESS = "little"


def bytes_to_uint64(data: bytes) -> uint64:
    return uint64(int.from_bytes(data, ENDIANNESS))


def uint_to_bytes(n: uint) -> bytes:
    return serialize(n)


def hash(data: bytes) -> Bytes32:
    return Bytes32(sha256(data).digest())


def gen_node_id():
    return NodeId(secrets.token_bytes(32))
