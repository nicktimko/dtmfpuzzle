from __future__ import division # if you're not using Python 3, this'll probably suck anyway.
import math
import itertools
import random
import struct
import wave

# http://en.wikipedia.org/wiki/Dual-tone_multi-frequency_signaling
DTMF_TONES = {
    '1': (697, 1209),
    '2': (697, 1336),
    '3': (697, 1477),
    'A': (697, 1633),
    '4': (770, 1209),
    '5': (770, 1336),
    '6': (770, 1477),
    'B': (770, 1633),
    '7': (852, 1209),
    '8': (852, 1336),
    '9': (852, 1477),
    'C': (852, 1633),
    '*': (941, 1209),
    '0': (941, 1336),
    '#': (941, 1477),
    'D': (941, 1633),
}

FS = 8000
BITS = 16

def rand_phase():
    return 2 * math.pi * random.random()

def f2w(f):
    return 2 * math.pi * f

def tone_gen(key, fs):
    om = [f2w(f) for f in DTMF_TONES[key]]
    n_tones = len(om)
    ph = [rand_phase() for n in range(n_tones)]

    for t in itertools.count(0, 1/fs):
        yield sum(math.cos(o*t + p) for o, p in zip(om, ph)) / n_tones

def tone(t, fs, key, **kwargs):
    n_samp = int(t * fs)
    if key is not None:
        gen = tone_gen(key, fs)
        sm = smooth_attack(n_samp, **kwargs)
        for samp, s in zip(gen, sm):
            yield samp * s
    else:
        for samp in itertools.repeat(0, n_samp):
            yield samp

def smooth_attack(n_samp, roll_on=80, roll_off=None):
    if roll_off is None:
        roll_off = roll_on

    constant_period = n_samp - roll_on - roll_off

    for n in range(roll_on):
        yield (math.cos(math.pi * n / roll_on) - 1) / 2

    for n in range(constant_period):
        yield 1

    for n in range(roll_off):
        yield (math.cos(math.pi * n / roll_on) + 1) / 2

def scale16bit(samp):
    return int(samp * 2 ** (BITS - 1))

def rand_float(min, max):
    return min + (random.random() * (max - min))

def open_wav(filename):
    wav = wave.open(filename, 'w')
    wav.setnchannels(1)
    wav.setframerate(FS)
    wav.setsampwidth(BITS // 8) # 16-bit
    return wav

def AGWN():
    while True:
        yield random.random() * 2 - 1

def test_tones():
    time = 0.2
    digits = '1234567890ABCD*#'
    digits_f = itertools.chain([None], *zip(digits, itertools.repeat(None)))
    tones = itertools.chain(*(tone(time, FS, d) for d in digits_f))

    wav = open_wav('testtones.wav')
    txt = open('testtones.txt', 'w')

    for samp in tones:
        s = scale16bit(samp)
        wav.writeframes(struct.pack('h', s))
        txt.write('{}\n'.format(s))

    wav.close()
    txt.close()

    return digits

def random_tones(n, tone_range, gap_range, SNR, filename):
    keys = list(DTMF_TONES.keys())
    digits = [random.choice(keys) for x in range(n)]
    tone_times = [rand_float(*tone_range) for x in range(n)]
    gap_times = [rand_float(*gap_range) for x in range(n)]


    times = itertools.chain([rand_float(*gap_range)], *zip(tone_times, gap_times))
    digits_f = itertools.chain([None], *zip(digits, itertools.repeat(None)))
    tones = itertools.chain(*(tone(t, FS, d) for t, d in zip(times, digits_f)))

    ksig = SNR / (SNR + 1)
    knoise = 1 / (SNR + 1)

    wav = open_wav(filename + '.wav')
    txt = open(filename + '.txt', 'w')

    for samp, noise in zip(tones, AGWN()):
        s = scale16bit(ksig * samp + knoise * noise)
        wav.writeframes(struct.pack('h', s))
        txt.write('{}\n'.format(s))

    wav.close()
    txt.close()

    return digits

if __name__ == '__main__':
    magic = 1.5
    SNRs = [1e100, 10]
    for i in range(14):
        SNRs.append(SNRs[-1] / magic)

    answer_key = open('answers.txt', 'w')
    for n, SNR in enumerate(SNRs, start=1):
        fn = 'level{:02}'.format(n)
        digits = random_tones(30, [0.12, 0.3], [0.12, 0.3], SNR, fn)
        print(fn, digits)
        answer_key.write('{},{}\n'.format(fn, ''.join(digits)))

    digits = test_tones()
    answer_key.write('testtones,{}'.format(digits))

    answer_key.close()

