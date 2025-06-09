from Cryptodome.Cipher import AES


def resolve_private_address(address: str, irk: str) -> bool:
    _MSB_MASK = 0b11000000
    _MSB_RPA = 0b01000000
    """Return `True` if the address can be resolved with the IRK."""
    rpa = bytes.fromhex(address.replace(":", ""))
    # Format of a resolvable private address:
    # MSB                                          LSB
    # 01 Random part of prand      Hash value
    # <-   prand (24 bits)  -><-   hash (24 bits)   ->
    if rpa[0] & _MSB_MASK != _MSB_RPA:
        print(f"Address is not an RPA, {address}")
        print(rpa.hex())
        return False

    prand = rpa[:3]
    hash_value = rpa[3:]
    print("prand {}".format(prand.hex()))
    key = bytes.fromhex(irk)[::-1]
    cipher = AES.new(key, AES.MODE_ECB)
    localhash = cipher.encrypt(b"\x00" * 13 + prand)

    print("hash value {}".format(hash_value.hex()))
    sub = localhash[13:]
    print("local hash {}".format(sub.hex()))
    print(localhash.hex())
    if localhash[13:] != hash_value:
        print("24 bits of local hash don't match the RPA's hash")
        return False
    print("*** match ***")
    return True
