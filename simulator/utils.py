from eth2spec.utils.ssz.ssz_typing import Bytes32, uint64, uint
from eth2spec.utils.ssz.ssz_impl import serialize
from hashlib import sha256


ENDIANNESS = "little"


def bytes_to_uint64(data: bytes) -> uint64:
    return uint64(int.from_bytes(data, ENDIANNESS))


def uint_to_bytes(n: uint) -> bytes:
    return serialize(n)


def bytes_to_int(data) -> int:
    return int.from_bytes(data, ENDIANNESS)


def int_to_bytes(n: int) -> bytes:
    return n.to_bytes(32, ENDIANNESS)


def hash(data: bytes) -> Bytes32:
    return Bytes32(sha256(data).digest())

