#!/usr/bin/env python

# wujian@2018

import argparse

import numpy as np
import webrtcvad as vad

from libs.data_handler import WaveReader, WaveWriter

from libs.utils import get_logger

logger = get_logger(__name__)


def split_frame(samps, step):
    N = samps.size
    t = 0
    while True:
        if t + step > N:
            break
        yield samps[t:t + step]
        t += step


class VoiceSpliter(object):
    def __init__(self, mode, cache_size, fs=16000):
        if cache_size <= 0:
            raise ValueError("--cache-size must >= 1")
        self.pyvad = vad.Vad(mode=args.mode)
        self.fs = fs
        self.cache_size = cache_size
        self.reset()

    def run(self, frame):
        if self.cur_steps < 0:
            raise RuntimeError(
                "Seems bugs existed in VoiceSpliter's implementation")
        active = self.pyvad.is_speech(frame, self.fs)
        if active:
            # cur_steps = 0, record cpt_point
            if self.cur_steps == 0:
                self.cpt_point = self.cur_frame
            if not self.voiced:
                self.cur_steps += 1
                if self.cur_steps == self.cache_size:
                    self.voiced = True
        else:
            if self.cur_steps:
                self.cur_steps -= 1
                if self.voiced and self.cur_steps == 0:
                    self.voiced = False
                    self.segments.append((self.cpt_point, self.cur_frame))
        self.cur_frame += 1

    def report(self, voice=True):
        if self.voiced and self.cpt_point != self.cur_frame:
            self.segments.append((self.cpt_point, self.cur_frame))
        if voice:
            return self.segments
        else:
            nsegs = []
            prev = 0
            for i, (m, n) in enumerate(self.segments):
                if i == 0:
                    if m != 0:
                        nsegs.append((i, m))
                else:
                    nsegs.append((prev, m))
                prev = n
            return nsegs

    def reset(self):
        self.cur_steps = 0
        self.cur_frame = 0
        self.cpt_point = 0
        self.voiced = False
        self.segments = []


def run(args):
    def ms_to_n(ms, sr):
        return int(ms * sr / 1000.0)

    splitter = VoiceSpliter(args.mode, args.cache_size, args.sr)
    wav_reader = WaveReader(args.wav_scp, sr=args.sr, normalize=False)
    logger.info(f"Setting vad mode: {args.mode:d}")

    step = ms_to_n(args.chunk_size, args.sr)
    with WaveWriter(args.dst_dir, sr=args.sr, normalize=False) as wav_writer:
        for key, ori_wav in wav_reader:
            splitter.reset()
            for frame in split_frame(ori_wav, step):
                frame = frame.astype(np.int16)
                splitter.run(frame.tobytes())
            segments = splitter.report(voice=False)
            gather = []
            for seg in segments:
                s, t = seg
                gather.append(ori_wav[s * step:(t + 1) * step])
            if len(gather):
                wav_writer.write(key, np.hstack(gather))
            else:
                logger.warn(f"Haven't got active segments for utterance {key}")
    logger.info(f"Processed {len(wav_reader)} utterances")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Command to remove silence from original utterances"
        "(using py-webrtcvad from https://github.com/wiseman/py-webrtcvad). "
        "This is often used in speaker relative tasks.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("wav_scp", type=str, help="Input wav scripts")
    parser.add_argument("dst_dir", type=str, help="Output wav directory")
    parser.add_argument("--mode",
                        type=int,
                        default=2,
                        help="Vad mode used in webrtc "
                        "(0->3 less->more aggressive)")
    parser.add_argument("--chunk-size",
                        type=int,
                        default=10,
                        help="Chunk size in ms (x10)")
    parser.add_argument("--sr",
                        type=int,
                        default=16000,
                        help="Waveform sample rate")
    parser.add_argument("--cache-size",
                        type=int,
                        default=5,
                        help="Number of frames remembered in history")
    args = parser.parse_args()
    run(args)
