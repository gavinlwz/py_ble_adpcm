ima_index_table = [
    -1, -1, -1, -1, 2, 4, 6, 8,
    -1, -1, -1, -1, 2, 4, 6, 8
]

ima_step_table = [
    7, 8, 9, 10, 11, 12, 13, 14, 16, 17,
    19, 21, 23, 25, 28, 31, 34, 37, 41, 45,
    50, 55, 60, 66, 73, 80, 88, 97, 107, 118,
    130, 143, 157, 173, 190, 209, 230, 253, 279, 307,
    337, 371, 408, 449, 494, 544, 598, 658, 724, 796,
    876, 963, 1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066,
    2272, 2499, 2749, 3024, 3327, 3660, 4026, 4428, 4871, 5358,
    5894, 6484, 7132, 7845, 8630, 9493, 10442, 11487, 12635, 13899,
    15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794, 32767
]


def _encoder(sample, prevsample, previndex):
    predsample = prevsample
    index = previndex
    step = ima_step_table[index]

    # Compute difference between actual and predicted sample
    diff = sample - predsample
    if diff >= 0:
        code = 0
    else:
        code = 8
        diff = -diff

    # Quantize difference into 4-bit code using quantizer step size
    tempstep = step
    if diff >= tempstep:
        code |= 4
        diff -= tempstep
    tempstep >>= 1
    if diff >= tempstep:
        code |= 2
        diff -= tempstep
    tempstep >>= 1
    if diff >= tempstep:
        code |= 1

    # Inverse quantize code into predicted difference using quantizer step size
    diffq = step >> 3
    if code & 4:
        diffq += step
    if code & 2:
        diffq += step >> 1
    if code & 1:
        diffq += step >> 2

    # Fixed predictor computes new prediction by adding old prediction to predicted difference
    if code & 8:
        predsample -= diffq
    else:
        predsample += diffq

    # Correct overflow
    if predsample > 32767:
        predsample = 32767
    elif predsample < -32768:
        predsample = -32768

    # Get new quantizer step-size index by adding old index to table lookup
    index += ima_index_table[code]

    # Correct quantizer step index overflow
    if index < 0:
        index = 0
    elif index > 88:
        index = 88

    return code & 0x0f, predsample, index


def _decoder(code, prevsample, previndex):
    predsample = prevsample
    index = previndex

    # Find quantizer step size from lookup table
    step = ima_step_table[index]

    # Inverse quantize code into difference using quantizer step size
    diffq = step >> 3
    if code & 4:
        diffq += step
    if code & 2:
        diffq += step >> 1
    if code & 1:
        diffq += step >> 2

    # Add difference to predicted sample
    if code & 8:
        predsample -= diffq
    else:
        predsample += diffq

    # Correct overflow
    if predsample > 32767:
        predsample = 32767
    elif predsample < -32768:
        predsample = -32768

    # Get new quantizer step-size index by adding old index to table lookup
    index += ima_index_table[code]

    # Correct quantizer step index overflow
    if index < 0:
        index = 0
    elif index > 88:
        index = 88

    return predsample, index


def adpcm_generic_frame_encode_mono(samples, idx: int, frame_size_per_ch: int):
    num_of_samples = int((frame_size_per_ch - 3) * 2 + 1)
    if len(samples) != num_of_samples:
        raise Exception('num of samples is not equal {}'.format(num_of_samples))
    frame_byte = []
    frame_byte.append(samples[0] & 0xff)
    frame_byte.append((samples[0] >> 8) & 0xff)
    frame_byte.append(idx)
    _encoder_prevsample = samples[0]
    _encoder_previndex = idx
    encoded_samples = []
    for i in range(1, num_of_samples, 2):
        sample = samples[i]
        _code, _encoder_prevsample, _encoder_previndex = _encoder(sample, _encoder_prevsample, _encoder_previndex)
        sample = samples[i + 1]
        _code_h, _encoder_prevsample, _encoder_previndex = _encoder(sample, _encoder_prevsample, _encoder_previndex)
        encoded_samples.append(_code)
    return encoded_samples


def adpcm_generic_frame_decode_stereo(frame_data):
    prevsample_l = frame_data[0] | (frame_data[1] << 8)
    if 0 != prevsample_l & (1 << 15):
        prevsample_l = prevsample_l - (1 << 16)
    previndex_l = frame_data[2]
    prevsample_r = frame_data[3] | (frame_data[4] << 8)
    if 0 != prevsample_r & (1 << 15):
        prevsample_r = prevsample_r - (1 << 16)
    previndex_r = frame_data[5]
    sample_l = [prevsample_l]
    sample_r = [prevsample_r]
    cnt = len(frame_data)
    for i in range(6, cnt, 2):
        code = frame_data[i]
        prevsample_l, previndex_l = _decoder(code & 0x0f, prevsample_l, previndex_l)
        sample_l.append(prevsample_l)
        prevsample_l, previndex_l = _decoder((code >> 4) & 0x0f, prevsample_l, previndex_l)
        sample_l.append(prevsample_l)

    for i in range(7, cnt, 2):
        code = frame_data[i]
        prevsample_r, previndex_r = _decoder(code & 0x0f, prevsample_r, previndex_r)
        sample_r.append(prevsample_r)
        prevsample_r, previndex_r = _decoder((code >> 4) & 0x0f, prevsample_r, previndex_r)
        sample_r.append(prevsample_r)
    sample_cnt = len(sample_l)
    r_cnt = len(sample_r)
    if sample_cnt > r_cnt:
        sample_cnt = r_cnt
    sample_bytes = bytearray()
    for i in range(sample_cnt):
        sample_bytes.append(sample_l[i] & 0xff)
        sample_bytes.append((sample_l[i] >> 8) & 0xff)
        sample_bytes.append(sample_r[i] & 0xff)
        sample_bytes.append((sample_r[i] >> 8) & 0xff)
    return sample_bytes


def adpcm_generic_frame_decode_mono(frame_data):
    prevsample = frame_data[0] | (frame_data[1] << 8)
    if 0 != prevsample & (1 << 15):
        prevsample = prevsample - (1 << 16)
    previndex = frame_data[2]
    sample = [prevsample]
    cnt = len(frame_data)
    for i in range(3, cnt, 1):
        code = frame_data[i]
        prevsample, previndex = _decoder(code & 0x0f, prevsample, previndex)
        sample.append(prevsample)
        prevsample, previndex = _decoder((code >> 4) & 0x0f, prevsample, previndex)
        sample.append(prevsample)

    sample_cnt = len(sample)
    sample_bytes = bytearray()
    for i in range(sample_cnt):
        sample_bytes.append(sample[i] & 0xff)
        sample_bytes.append((sample[i] >> 8) & 0xff)
    return sample_bytes
