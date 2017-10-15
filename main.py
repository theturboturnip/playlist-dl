#!/usr/bin/env python 2.7
import subprocess,json,sys,os,re,shutil

path = os.path.dirname(os.path.abspath(sys.argv[0]))
nullfile = open(os.devnull, "w")

def call(args):
    subprocess.call(args, stdout=nullfile, stderr=nullfile)

def require_args(arg_count):
    if len(sys.argv) < arg_count + 1:
        print "Not enough args!"
        exit(1)

def clean_up():
    shutil.rmtree(os.path.join(path,"temp"))
    quit()
        
def create_dir(*args):
    to_create = os.path.join(*args)
    print to_create
    if not os.path.exists(to_create):
        os.makedirs(to_create)
        
def files_in(*args):
    folder_path = os.path.join(*args)
    filenames = os.walk(folder_path).next()[2]
    to_return = []
    for filename in filenames:
        to_return.append(os.path.join(folder_path,filename))
    return to_return

def get_file_metadata(path):
    output = subprocess.check_output(["ffprobe","-i",path,"-loglevel","error","-show_entries","format_tags=title,comment","-of","default=noprint_wrappers=1:nokey=1"],stderr=subprocess.STDOUT).decode(sys.stdout.encoding).split("\n")
    return output
    
def get_dl_title_from_title(video_title):
    dl_title = raw_input("Title for '"+video_title+"'?: ")
    if dl_title.strip() == "":
        return video_title
    if dl_title.strip().lower() == "quit":
        clean_up()
    return dl_title.strip()

def download_video(video, output_folder_name, make_mono = False):
    title=get_dl_title_from_title(video["title"])
    dl_output_file = os.path.join(path,"temp",video["title"]+".%(ext)s")
    print "Downloading",video["title"],"to",dl_output_file

    call(["youtube-dl","-x","--audio-format","mp3","-o",dl_output_file,"--prefer-ffmpeg", "https://youtube.com/watch?v="+video["id"]])

    #normalize
    vol_regex = re.compile(r"mean_volume: (-?[0-9]+.[0-9]+) dB")
    gain = -25.0/float(vol_regex.search(subprocess.check_output(["ffmpeg","-i",dl_output_file.replace("%(ext)s","mp3"),"-af","volumedetect","-vn","-sn","-dn","-f","null","/dev/null"],stderr=subprocess.STDOUT).decode(sys.stdout.encoding)).group(1))

    output_file = os.path.join(path,"output",output_folder_name,title+".mp3")
    # Use ffmpeg to convert the temp file to the real thing
    cmd  = ["ffmpeg", "-i", dl_output_file.replace("%(ext)s","mp3"), "-f", "lavfi", "-i", "aevalsrc=0|0:d=2"] # Specify input file and silence source
    cmd += ["-filter_complex", "[0:0]silenceremove=1:0:-50dB:1:1:-50dB[start];[start] [1:0] concat=n=2:v=0:a=1[middle];[middle]volume="+("%.2f" % gain)+"dB[out]"] # Apply a filter which, in order: strips silence from either side of the source, concatenates the result with the silence, applies a gain to normalize the mean volume to -25dB.
    if make_mono:
        cmd += ["-ac","1"] # Make channels = 1
    cmd += ["-metadata", "artist=Shoji Meguro","-metadata","album=Persona"+(" [Mono]" if make_mono else ""),"-metadata","comment="+video["id"],"-metadata","title="+title] # Apply metadata
    cmd += ["-map", "[out]", output_file] # Specify output path

    #print subprocess.list2cmdline(cmd)
    print "Converting from "+dl_output_file+" to "+output_file
    call(cmd)
    
def get_videos_for_playlist(playlistId):
    json_str = '{"videos":['+subprocess.check_output(["youtube-dl","-j","--flat-playlist","https://www.youtube.com/playlist?list="+playlistId]).replace("\n",",")[0:-1]+"]}"
    json_array = json.loads(json_str)["videos"]
    ids=[]
    for video in json_array:
        ids.append(video["id"])
    return json_array, ids #PLpc_f2Kxcy9VcT6VNSekSgo7DG6lchSqB

def update_files_for_playlist(videos,ids,folder_name):
    current_files = files_in(path,"output",folder_name)
    current_videos = []
    for f in current_files:
        if os.path.splitext(f)[1] != ".mp3":
            if raw_input("Non-mp3 detected! Remove file at path "+f+"? :") == "y":
                os.remove(f)
        else:
            metadata = get_file_metadata(f)
            if metadata[1] not in ids and raw_input("Remove file at path "+f+"? :") == "y":
                os.remove(f)
            else:
                current_videos.append(metadata[1])
    to_download = []
    i = 0
    for v in videos:
        if v["id"] not in current_videos:
            to_download.append(i)
        i += 1
    for i in to_download:
        download_video(videos[i], folder_name, folder_name=="mono")
    

require_args(0)
videos, ids = get_videos_for_playlist("PLpc_f2Kxcy9VcT6VNSekSgo7DG6lchSqB")

create_dir(path,"output")
create_dir(path,"temp")
create_dir(path,"output","normalized")
create_dir(path,"output","mono")

update_files_for_playlist(videos, ids, "normalized")

delete_dir(path,"temp")
