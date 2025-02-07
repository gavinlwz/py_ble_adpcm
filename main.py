import pyaudio

from py_adpcm import adpcm_generic_frame_decode_stereo, adpcm_generic_frame_decode_mono
from py_gatt import disconnect_ble_client, get_client_ble, get_notify_data

FORMAT = pyaudio.paInt16  # 16-bit PCM
RATE = 16000
CHANNELS = 1

if __name__ == '__main__':
    dev_idx = 0
    if 0 == dev_idx:
        target_address = "C0:01:02:03:04:AB"
        ntf_uuid = "0000f0a1-0000-1000-8000-00805f9b34fb"
    else:
        target_address = "00:01:02:03:04:BB"
        ntf_uuid = '28be4cb6-cd67-11e9-a32f-2a2ae2dbcce4'
    client = None
    try:
        client = get_client_ble(target_address, ntf_uuid)
    except Exception as e:
        print(str(e))
        exit(0)
    dev_audio = pyaudio.PyAudio()
    stream = dev_audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True)
    if 1 == CHANNELS:
        adpcm_decode = adpcm_generic_frame_decode_mono
    else:
        adpcm_decode = adpcm_generic_frame_decode_stereo
    last_frame_size = 0
    while True:
        adpcm = get_notify_data()
        if 0 == len(adpcm):
            print('disconnect')
            break
        frame_size = len(adpcm)
        pcm_data = adpcm_decode(adpcm)
        stream.write(bytes(pcm_data))
        if last_frame_size != frame_size:
            last_frame_size = frame_size
            print(frame_size)

    stream.stop_stream()
    stream.close()
    dev_audio.terminate()
    disconnect_ble_client(client)
