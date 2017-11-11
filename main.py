#!/usr/bin/env python 2.7
import subprocess,json,sys,os,re,shutil

path = os.path.dirname(os.path.abspath(sys.argv[0]))
nullfile = open(os.devnull, "w")

youtube_dl = "youtube-dl"
ffmpeg = "ffmpeg"
ffprobe = "ffprobe"
if "--local-cmds" in sys.argv:
    youtube_dl = "./exec/youtube-dl"
    ffmpeg = "./exec/ffmpeg"
    ffprobe = "./exec/ffprobe"

artist = "Shoji Meguro"
album = "Persona"

dl_titles={}

target_volume = -12.0

def call(args):
    if "--debug-cmds" in sys.argv:
        subprocess.call(args)
    else:
        subprocess.call(args, stdout=nullfile, stderr=nullfile)

def require_args(arg_count):
    if len(sys.argv) < arg_count + 1:
        print "Not enough args!"
        exit(1)

def clean_up():
    print "Quitting..."
    quit()

def get_input(message, boolean = False):
    if (boolean):
        message += " y/*/q: "
    else:
        message += " (q to quit): "
    reply = raw_input(message).strip()
    if reply.lower() == "q":
        clean_up()
    elif boolean:
        return reply.lower() == "y"
    return reply
        
def create_dir(*args):
    to_create = os.path.join(*args)
    if not os.path.exists(to_create):
        os.makedirs(to_create)
    return to_create
        
def files_in(*args):
    folder_path = os.path.join(*args)
    filenames = os.walk(folder_path).next()[2]
    to_return = []
    for filename in filenames:
        to_return.append(os.path.join(folder_path,filename))
    return to_return

def get_file_metadata(path):
    output = subprocess.check_output([ffprobe,"-i",path,"-loglevel","error","-show_entries","format_tags=title,comment","-of","default=noprint_wrappers=1:nokey=1"],stderr=subprocess.STDOUT).decode(sys.stdout.encoding).split("\n")
    return output

def get_dl_title_from_title(video):
    if (video["id"] in dl_titles):
        return dl_titles[video["id"]]
    if ("dl_title" in video):
        return video["dl_title"]
    dl_title = get_input("Title for '"+video["title"].encode("utf8")+"'?")
    if dl_title.strip().lower() == "quit":
        clean_up()
    if dl_title.strip() == "":
        dl_titles[video["id"]] = video["title"]
        return video["title"]
    dl_titles[video["id"]] = dl_title.strip()
    return dl_title.strip()

def download_video(video, output_folder, downloads_dir):
    title=video["dl_title"]
    dl_output_file = os.path.join(downloads_dir,video["title"]+".%(ext)s")

    if not os.path.exists(dl_output_file.replace("%(ext)s","mp3")) or "--redownload" in sys.argv: 
        print "Downloading",video["dl_title"]#,"to",dl_output_file
        call([youtube_dl,"-x","--audio-format","mp3","-o",dl_output_file,"--prefer-ffmpeg","--ffmpeg-location",ffmpeg, "https://youtube.com/watch?v="+video["id"]])

    vol_regex = re.compile(r"mean_volume: (-?[0-9]+.[0-9]+) dB")
    gain = target_volume - float(vol_regex.search(subprocess.check_output([ffmpeg,"-i",dl_output_file.replace("%(ext)s","mp3"),"-af","volumedetect","-vn","-sn","-dn","-f","null",os.devnull],stderr=subprocess.STDOUT).decode(sys.stdout.encoding)).group(1))

    output_file = os.path.join(output_folder, title+".mp3")
    # Use ffmpeg to convert the temp file to the real thing
    cmd  = [ffmpeg, "-i", dl_output_file.replace("%(ext)s","mp3"), "-f", "lavfi", "-i", "aevalsrc=0|0:d=5", "-y"] # Specify input file and silence source

    filter_cmd = "[0:0]silenceremove=1:0:-50dB:1:1:-50dB[start];[start] [1:0] concat=n=2:v=0:a=1[middle];[middle]"
    if "--legacy-norm" in sys.argv:
        filter_cmd += "volume="+str(gain)+"dB"
    else:
        filter_cmd += "loudnorm=i=-5.0"
    filter_cmd += "[out]"
    
    cmd += ["-filter_complex", filter_cmd] # Apply a filter which, in order: strips silence from either side of the source, concatenates the result with the silence, normalizes the volume.
    cmd += ["-metadata", "artist="+artist,"-metadata","album="+album,"-metadata","comment="+video["id"],"-metadata","title="+title] # Apply metadata
    cmd += ["-map", "[out]", output_file] # Specify output path

    print "Converting "+video["dl_title"]
    call(cmd)
    
def get_videos_for_playlist(playlistId):
    json_str = '{"videos":['+subprocess.check_output([youtube_dl,"-j","--flat-playlist","https://www.youtube.com/playlist?list="+playlistId]).replace("\n",",")[0:-1]+"]}"
    json_array = json.loads(json_str)["videos"]
    ids=[]
    for video in json_array:
        ids.append(video["id"])
    return json_array, ids

def handle_folder(folder):
    current_files = files_in(folder)
    current_videos = []
    for f in current_files:
        ext = os.path.splitext(f)[1]
        if ext != ".mp3":
            if ext == "":
                continue
            if get_input("Non-mp3 detected! Remove file at path "+f+"?", True):
                os.remove(f)
        else:
            metadata = get_file_metadata(f)
            if metadata[1] not in ids and get_input("File not in playlist! Remove file at path "+f+"?", True):
                os.remove(f)
            elif metadata[0] != os.path.splitext(os.path.basename(f))[0] and get_input("Incorrect name detected for "+metadata[0]+"! Correct?", True):
                os.rename(f, os.path.join(folder,metadata[0]+".mp3"))
            else:
                current_videos.append(metadata)
    return current_videos

def update_files_for_playlist(videos,ids,output_path,downloads_dir):
    current_videos = handle_folder(output_path)
    to_download = []
    i = 0
    for v in videos:
        try:
            index_of_v = [item[1] for item in current_videos].index(v["id"])
        except ValueError:
            index_of_v = -1
        if index_of_v == -1:
            v["dl_title"] = get_dl_title_from_title(v)
        else:
            v["dl_title"] = current_videos[index_of_v][0]
        if "--redownload" in sys.argv or "--renorm" in sys.argv or index_of_v == -1:
            to_download.append(i)
        i += 1
    
    for i in to_download:
        download_video(videos[i], output_path, downloads_dir)
        print str(i+1)+" of "+str(len(videos))+" downloaded!"

def convert_videos_to_mono(normalized_output, mono_output):
    handle_folder(mono_output)
    normalized_files = files_in(normalized_output)
    for f in normalized_files:
        if os.path.splitext(f)[1] == "":
            continue
        mono_filename = os.path.join(mono_output, os.path.basename(f))
        if not os.path.exists(mono_filename) or "--remono" in sys.argv or "--renorm" in sys.argv:
            print "Monoizing "+f
            call([ffmpeg, "-i", f, "-b:a", "256k", "-ac", "1", "-y", "-metadata", "album="+album+" [Mono]", mono_filename])
    

require_args(0)
playlist_id = "PLpc_f2Kxcy9VcT6VNSekSgo7DG6lchSqB"
if sys.argv[1][0] != '-':
    playlist_id = sys.argv[1]
videos, ids = get_videos_for_playlist(playlist_id)

create_dir(path,"output")
create_dir(path,"output",playlist_id)
downloads_dir = create_dir(path,"output","downloaded")
normalized_output = create_dir(path,"output",playlist_id,"normalized")
mono_output = create_dir(path,"output",playlist_id,"mono")

update_files_for_playlist(videos, ids, normalized_output, downloads_dir)
convert_videos_to_mono(normalized_output, mono_output)

clean_up()
