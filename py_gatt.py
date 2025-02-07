import asyncio
from bleak import BleakClient, BleakScanner, BleakError

queue: asyncio.Queue = asyncio.Queue()


def asyncio_run(coro):
    # asyncio.run doesn't seem to exist on Python 3.6.9 / Bleak 0.14.2
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


async def list_services(client):
    for service in client.services:
        print(f"[Service] {service.uuid}: {service.description}")
        for char in service.characteristics:
            if "read" in char.properties:
                try:
                    value = bytes(await client.read_gatt_char(char.uuid))
                except Exception as e:
                    value = str(e).encode()
            else:
                value = None

            properties = ",".join(char.properties)
            print(f"  [Characteristic] {char.uuid}: (Handle: {char.handle}) ({properties}) | "
                  f"Name: {char.description}, Value: {value}")

            for desc in char.descriptors:
                value = await client.read_gatt_descriptor(desc.handle)
                print(f"    [Descriptor] {desc.uuid}: (Handle: {desc.handle}) | Value: {value}")


async def wait_for_response():
    ret = await queue.get()
    # print('{} {}'.format(type(ret), len(ret)))
    return ret


def discon_cb(client):
    empty_data = bytes()
    queue.put_nowait(empty_data)


def callback(sender, data):
    # logger.debug(f"< {sender}: {data}")
    response = bytes(data)
    queue.put_nowait(response)


async def async_get_client_ble(ble_address: str, ntf_uuid: str) -> BleakClient:
    device = await BleakScanner.find_device_by_address(ble_address, timeout=5.0)
    if not device:
        raise BleakError(f"A device with address {ble_address} could not be found.")

    # Connect to the device explicitly instead of using the following line which
    # prevents the client from being returner:
    #   with BleakClient(device) as client:
    client = BleakClient(device, disconnected_callback=discon_cb)
    await client.connect()

    if False:
        await list_services(client)
    print('mtu {}'.format(client.mtu_size))
    # register notification callback
    if ntf_uuid:
        await client.start_notify(ntf_uuid, callback)

    return client


def get_client_ble(address, uuid=None):
    return asyncio_run(async_get_client_ble(address, uuid))


def disconnect_ble_client(client: BleakClient):
    asyncio_run(client.disconnect())


def get_notify_data():
    r_data = asyncio_run(wait_for_response())
    return r_data
