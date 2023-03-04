import os, sys
import subprocess as sp
from moviepy.config import get_setting
from moviepy.tools import subprocess_call


def ffmpeg_movie_from_frames(filename, folder, fps, digits=6, bitrate="v"):
    s = "%" + "%02d" % digits + "d.png"
    cmd = [
        get_setting("FFMPEG_BINARY"),
        "-y",
        "-f",
        "image2",
        "-r",
        "%d" % fps,
        "-i",
        os.path.join(folder, folder) + "/" + s,
        "-b",
        "%dk" % bitrate,
        "-r",
        "%d" % fps,
        filename,
    ]

    subprocess_call(cmd)


def ffmpeg_extract_subclip(filename, t1, t2, targetname=None):
    name, ext = os.path.splitext(filename)
    if not targetname:
        T1, T2 = [int(1000 * t) for t in [t1, t2]]
        targetname = "%sSUB%d_%d.%s" % (name, T1, T2, ext)

    cmd = [
        get_setting("FFMPEG_BINARY"),
        "-y",
        "-ss",
        "%0.2f" % t1,
        "-i",
        filename,
        "-t",
        "%0.2f" % (t2 - t1),
        "-map",
        "0",
        "-vcodec",
        "copy",
        "-acodec",
        "copy",
        targetname,
    ]

    subprocess_call(cmd)


def ffmpeg_merge_video_audio(
    video,
    audio,
    output,
    vcodec="copy",
    acodec="copy",
    ffmpeg_output=False,
    logger="bar",
):
    cmd = [
        get_setting("FFMPEG_BINARY"),
        "-y",
        "-i",
        audio,
        "-i",
        video,
        "-vcodec",
        vcodec,
        "-acodec",
        acodec,
        output,
    ]

    subprocess_call(cmd, logger=logger)


def ffmpeg_extract_audio(inputfile, output, bitrate=3000, fps=44100):
    cmd = [
        get_setting("FFMPEG_BINARY"),
        "-y",
        "-i",
        inputfile,
        "-ab",
        "%dk" % bitrate,
        "-ar",
        "%d" % fps,
        output,
    ]
    subprocess_call(cmd)


def ffmpeg_resize(video, output, size):
    cmd = [
        get_setting("FFMPEG_BINARY"),
        "-i",
        video,
        "-vf",
        "scale=%d:%d" % (size[0], size[1]),
        output,
    ]

    subprocess_call(cmd)
