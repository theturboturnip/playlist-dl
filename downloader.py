#!/usr/bin/env python 2.7
import argparse
import lib

parser = argparse.ArgumentParser(description='Download music from a YouTube playlist.', prog="python ./downloader.py")
parser.add_argument("playlist", help="The playlist to download")
parser.add_argument("downloads_folder", help="The location of raw downloaded song files")
parser.add_argument("output_folder", help="The folder to download the playlist to.")

parser.add_argument("--ffmpeg-location", type=str, help="Location of the ffmpeg executable.", default="ffmpeg")
parser.add_argument("--ffprobe-location", type=str, help="Location of the ffprobe executable.", default="ffprobe")
parser.add_argument("--youtube-dl-location", type=str, help="Location of the youtube-dl executable", default="youtube-dl")
parser.add_argument("--local-cmds", action="store_true", help="Equivalent to --ffmpeg-location ./exec/ffmpeg --youtube-dl-location ./exec/youtube-dl")

action_choices = ["NONE", "ALL", "NEW"]
parser.add_argument("--download", choices=action_choices, help="Which videos to download from Youtube. Newly downloaded videos will automatically be normalized unless --normalize is NONE, and these videos will be monoized unless --monoize is NONE.", default="NEW")
parser.add_argument("--normalize", choices=action_choices, help="Which videos to normalize. These videos will automatically be monoized unless --monoized is NONE.", default="NEW")
parser.add_argument("--monoize", choices=action_choices, help="Which videos to download from Youtube.", default="NONE")

parser.add_argument("--metadata-file", type=str, help="Specify the location of the metadata file. This will be loaded from at the start if it exists and written to at the end.", default="./videos.json")
parser.add_argument("--default-artist", type=str, help="Specify the default artist. This can be selected quickly when creating metadata for videos.")
parser.add_argument("--default-album", type=str, help="Specify the default album. This can be selected quickly when creating metadata for videos.")

parser.add_argument("--target-mean-volume", type=float, help="The target mean volume for normalization", default=-12.0)
parser.add_argument("--debug", action="store_true", help="Show debug information about commands called")

args = vars(parser.parse_args())

playlist = args["playlist"]
output_folders = [args["downloads_folder"], args["output_folder"]]
cmd_locations = [args["youtube_dl_location"], args["ffmpeg_location"], args["ffprobe_location"]]
download_status = [args["download"], args["normalize"], args["monoize"]]
metadata_file = args["metadata_file"]
default_metadata = [args["default_artist"], args["default_album"]]
target_volume = args["target_mean_volume"]
debug = args["debug"]

dl = lib.PlaylistDownloader(playlist, output_folders, cmd_locations, download_status, metadata_file, default_metadata, target_volume, debug)
dl.run()