#!/usr/bin/env python

# wujian@2018
"""
Compute spectrogram features(using librosa kernels) and write in kaldi format
"""

import argparse
from distutils.util import strtobool

from libs.data_handler import SpectrogramReader, ArchiveWriter
from libs.exraw import BinaryWriter
from libs.opts import StftParser
from libs.utils import get_logger

logger = get_logger(__name__)


def run(args):
    stft_kwargs = {
        "frame_len": args.frame_len,
        "frame_hop": args.frame_hop,
        "round_power_of_two": args.round_power_of_two,
        "window": args.window,
        "center": args.center,  # false to comparable with kaldi
        "apply_log": args.apply_log,
        "apply_pow": args.apply_pow,
        "apply_abs": True,
        "transpose": True  # T x F
    }
    reader = SpectrogramReader(args.wav_scp, **stft_kwargs)
    WriterImpl = {"kaldi": ArchiveWriter, "exraw": BinaryWriter}[args.format]
    with WriterImpl(args.dup_ark, args.scp) as writer:
        for key, feats in reader:
            # default using ch1 in multi-channel case
            if feats.ndim == 3:
                writer.write(key, feats[0])
            else:
                writer.write(key, feats)
    logger.info("Process {:d} utterances".format(len(reader)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=
        "Command to extract spectrogram features(using sptk's librosa kernels) "
        "and write as kaldi's archives",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        parents=[StftParser.parser])
    parser.add_argument("wav_scp",
                        type=str,
                        help="Source location of wave scripts in kaldi format")
    parser.add_argument("dup_ark",
                        type=str,
                        help="Location to dump spectrogram features")
    parser.add_argument("--scp",
                        type=str,
                        default="",
                        help="If assigned, generate corresponding "
                        "scripts for archives")
    parser.add_argument("--format",
                        type=str,
                        default="kaldi",
                        choices=["kaldi", "exraw"],
                        help="Output archive format, see format "
                        "in sptk/libs/exraw.py")
    parser.add_argument("--apply-log",
                        type=strtobool,
                        default=False,
                        help="If true, using log spectrogram "
                        "instead of linear")
    parser.add_argument("--apply-pow",
                        type=strtobool,
                        default=False,
                        help="If true, extract power spectrum "
                        "instead of magnitude spectrum")
    parser.add_argument("--normalize-samples",
                        type=strtobool,
                        default=False,
                        dest="normalize",
                        help="If true, normalize sample "
                        "values between [-1, 1]")
    args = parser.parse_args()
    run(args)
