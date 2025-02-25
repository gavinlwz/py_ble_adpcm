import asyncio
import binascii

import bleak
from bleak import BleakClient, BleakScanner, BleakError

queue: asyncio.Queue = asyncio.Queue()


def asyncio_run(coro):
    # asyncio.run doesn't seem to exist on Python 3.6.9 / Bleak 0.14.2
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


def on_scan_callback(device, advertisement_data):
    print("\r\n")
    if device.name:
        print(f"{device.address}  {device.name}  ,RSSI: {advertisement_data.rssi}")
    else:
        print(f"{device.address} ,RSSI: {advertisement_data.rssi}")

    manufacturer_data = advertisement_data.manufacturer_data
    for key, value in manufacturer_data.items():
        company_id = key
        adv_len = 3 + len(value)
        hex_data = '{:02x}ff{:04x}{}'.format(adv_len, company_id, value.hex())
        print(hex_data)

    service_data = advertisement_data.service_data
    for key, value in service_data.items():
        hex_data: str = binascii.hexlify(value).decode("utf-8")
        print(hex_data)


async def ble_advertisement_scan_start(scan_callback):
    if scan_callback:
        scanner = BleakScanner(detection_callback=scan_callback)
    else:
        scanner = BleakScanner(detection_callback=on_scan_callback)
    await scanner.start()
    return scanner


async def ble_advertisement_scan_stop(scanner: BleakScanner):
    await scanner.stop()


async def scan_ble_dev():
    devices = await BleakScanner.discover()
    for d in devices:
        print(f"{d.address}  {d.name}")


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


def bel_discover():
    return asyncio_run(scan_ble_dev())


def ble_adv_scan_start(scan_callback):
    return asyncio_run(ble_advertisement_scan_start(scan_callback))


def ble_adv_scan_stop(scanner):
    return asyncio_run(ble_advertisement_scan_stop(scanner))


def get_client_ble(address, uuid=None):
    return asyncio_run(async_get_client_ble(address, uuid))


def disconnect_ble_client(client: BleakClient):
    asyncio_run(client.disconnect())


def get_notify_data():
    r_data = asyncio_run(wait_for_response())
    return r_data
