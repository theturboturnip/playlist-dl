# -*- coding: utf-8 -*-
import subprocess,json,sys,os,re,shutil

class PlaylistDownloader:
    def __init__(self, playlist, output_folders=["./downloads","./playlist"], cmd_locations=["youtube-dl","ffmpeg","ffprobe"], download_status=["NEW", "NEW", "NONE"], metadata_file="", default_metadata=["Artist","Album"], target_volume=-12.0, debug = False):
        self.playlist = playlist
        self.downloads_folder = os.path.abspath(output_folders[0])
        self.output_folder = os.path.abspath(output_folders[1])

        self.youtube_dl = cmd_locations[0]
        self.ffmpeg = cmd_locations[1]
        self.ffprobe = cmd_locations[2]

        self.download_videos = download_status[0]
        self.normalize_videos = download_status[1]
        self.monoize_videos = download_status[2]

        self.metadata = {}
        if metadata_file != None:
            self.metadata_file = os.path.abspath(metadata_file)
            if (os.path.exists(self.metadata_file)):
                with open(self.metadata_file, "r") as f:
                    self.metadata.update(json.loads(f.read()))
            if (os.path.exists(self.metadata_file+".temp")):
                if self.get_input("Temp metadata file found. Use?", is_boolean=True):
                    with open(self.metadata_file+".temp", "r") as f:
                        self.metadata.update(json.loads(f.read()))
                else:
                    os.remove(self.metadata_file+".temp")
        else:
            self.metadata = {}
            self.metadata_file = None
            
        self.default_artist = default_metadata[0]
        self.default_album = default_metadata[1]

        self.target_mean_volume = target_volume

        self.debug = debug

    def create_dir(self,*args):
        to_create = os.path.join(*args)
        if not os.path.exists(to_create):
            os.makedirs(to_create)
        return to_create

    def call(self, *args):
        if (self.debug):
            print subprocess.list2cmdline(args)
            print subprocess.call(args)
        else:
            with open(os.devnull, "w") as devnull:
                subprocess.call(args, stdout=devnull, stderr=devnull)
    def check_output(self, *args):
        if (self.debug):
            print args
            print subprocess.list2cmdline(args)
            try:
                output = subprocess.check_output(args, stderr=subprocess.STDOUT).decode(sys.stdout.encoding)
                print output
                return output
            except subprocess.CalledProcessError as e:
                print "ERROR"
                output = e.output.decode(sys.stdout.encoding)
                print output
                return output
        return subprocess.check_output(args, stderr=subprocess.STDOUT).decode(sys.stdout.encoding)

    def get_input(self, message, is_boolean=False, default=""):
        if is_boolean:
            if default == "" or default:
                message += " (*/n): "
            else:
                message += " (y/*): "
        elif default:
            message += " (type nothing for \""+default+"\", q to quit): "
        else:
            message += " (q to quit): "

        user_input = raw_input(message.encode("utf-8")).strip()
        if is_boolean:
            if default == "" or default:
                if len(user_input) > 0 and user_input[0] == 'n':
                    return False
                return True
            if user_input == "y":
                return True
            return False
        if user_input == "":
            return default
        if user_input == "q":
            self.clean_up()
        return user_input
    def delete_file(self, path, reason):
        if self.get_input("Delete file at "+path+" because ["+reason+"]?", is_boolean=True):
            os.remove(path)
    def files_in(self, path):
        filenames = os.walk(path).next()[2]
        filepaths = [ os.path.join(path,f) for f in filenames]
        return filepaths

    def save_metadata(self):
        print "Saving metadata..."
        if self.metadata_file != None:
            with open(self.metadata_file, "w") as f:
                f.write(json.dumps(self.metadata))
            if os.path.exists(self.metadata_file+".temp"):
                os.remove(self.metadata_file+".temp")
    def update_temp_metadata(self):
        if self.metadata_file != None:
            with open(self.metadata_file+".temp", "w") as f:
                f.write(json.dumps(self.metadata))
    def get_metadata(self, id):
        if id not in self.metadata:
            video_name = None
            for video in self.videos:
                print video["id"]
                print id
                if video["id"] == id:
                    video_name = video["title"].encode("utf-8")
                    break
            if video_name == None:
                sys.exit(1)

            print "Getting metadata for video \""+video_name+"\""
            title = self.get_input("\tTitle")
            album = self.get_input("\tAlbum", default = self.default_album)
            artist = self.get_input("\tArtist", default = self.default_artist)
            self.metadata[id] = { "title": title, "album": album, "artist": artist }

            self.update_temp_metadata()
        return self.metadata[id]
    def get_mp3_metadata(self, *path):
        if (len(path) > 1):
            path = os.path.join(path)
        else:
            path = path[0]
        cmd_output=self.check_output(self.ffprobe, "-i", path, "-loglevel", "error", "-show_entries", "format_tags=title,artist,album,comment", "-of", "default=noprint_wrappers=1:nokey=1").split("\n")
        if len(cmd_output) < 4:
            return "", None
        return cmd_output[0], {"title":cmd_output[1], "artist":cmd_output[2], "album":cmd_output[3]}
    
    def get_videos_in_playlist(self):
        json_str  = '{"videos":['
        json_str += self.check_output(self.youtube_dl, "-j", "--flat-playlist", "https://youtube.com/playlist?list="+self.playlist).replace("\n",",")[0:-1]
        json_str += ']}'
        return json.loads(json_str)["videos"]

    def clean_and_scan_folders(self):
         #creates self.downloaded_ids, self.normalized_ids, and self.monoized_ids. also creates the folders for normalized+monoized output, fills self.metadata and removes non-mp3s/mp3s that aren't in the playlist.
        self.create_dir(self.downloads_folder)
        self.downloaded_ids = set([])
        for f in self.files_in(self.downloads_folder):
            filename = os.path.split(f)[1]
            id, ext = os.path.splitext(filename)
            if id[0] == '.':
                continue
            if (len(id) != 11):
                self.delete_file(f, "Invalid ID")
            elif ext != ".mp3":
                self.delete_file(f, "Non-mp3")
            elif id in self.playlist_ids:
                self.downloaded_ids.add(id)
                
        self.normalized_folder = self.create_dir(self.output_folder)
        self.normalized_ids = set([])
        for f in self.files_in(self.normalized_folder):
            filename = os.path.split(f)[1]
            name, ext = os.path.splitext(filename)
            if name[0] == '.':
                continue
            id, metadata = self.get_mp3_metadata(f)
            if id not in self.playlist_ids:
                self.delete_file(f, "Not in playlist")
            elif (len(id) != 11):
                self.delete_file(f, "Invalid ID")
            elif ext != ".mp3":
                self.delete_file(f, "Non-mp3")
            else:
                if (id not in self.metadata):
                    self.metadata[id] = metadata
                self.normalized_ids.add(id)

        self.monoized_folder = self.create_dir(self.output_folder, "mono")
        self.monoized_ids = set([])
        for f in self.files_in(self.monoized_folder):
            filename = os.path.split(f)[1]
            name, ext = os.path.splitext(filename)
            if name[0] == '.':
                continue
            id, metadata = self.get_mp3_metadata(f)
            if id not in self.playlist_ids:
                self.delete_file(f, "Not in playlist")
            elif (len(id) != 11):
                self.delete_file(f, "Invalid ID")
            elif ext != ".mp3":
                self.delete_file(f, "Non-mp3")
            else:
                if (id not in self.metadata):
                    self.metadata[id] == metadata
                self.monoized_ids.add(id)

    def download_video(self, id):
        output_path = os.path.join(self.downloads_folder, id+".%(ext)s")
        if self.ffmpeg == "ffmpeg":
            self.call(self.youtube_dl, "-x", "--audio-format", "mp3", "-o", output_path, "--prefer-ffmpeg", "https://youtube.com/watch?v="+id)
        else:
            self.call(self.youtube_dl, "-x", "--audio-format", "mp3", "-o", output_path, "--prefer-ffmpeg", "--ffmpeg-location", self.ffmpeg, "https://youtube.com/watch?v="+id)
    def normalize_video(self, id):
        in_path = os.path.join(self.downloads_folder, id+".mp3")
        video_metadata = self.get_metadata(id)

        loudnorm_json = self.check_output(self.ffmpeg, "-i", in_path, "-af", "loudnorm=I="+str(self.target_mean_volume)+":TP=-1.5:LRA=11:print_format=json", "-f", "null", "-")
        loudnorm_json = re.search(r"({(.*\n)+)+}", loudnorm_json).group(0).replace("\n","")
        loudnorm_data = json.loads(loudnorm_json)
        

        cmd = [self.ffmpeg, "-i", in_path, "-f", "lavfi", "-i", "aevalsrc=0|0:d=4", "-y"]
        
        filter_cmd  = "[0:0]silenceremove=1:0:-50dB:1:1:-50dB[start];"
        filter_cmd += "[start] [1:0] concat=n=2:v=0:a=1[middle];"
        filter_cmd += "[middle]loudnorm=I="+str(self.target_mean_volume)+":TP=-1.5:LRA=11:measured_I="+str(loudnorm_data["input_i"])+":measured_LRA="+str(loudnorm_data["input_lra"])+":measured_TP="+str(loudnorm_data["input_tp"])+":measured_thresh="+str(loudnorm_data["input_thresh"])+":offset="+str(loudnorm_data["target_offset"])+":linear=true[out]"
        cmd += ["-lavfi", filter_cmd]

        cmd += ["-metadata", "title="+video_metadata[u"title"]]
        cmd += ["-metadata", "artist="+video_metadata[u"artist"]]
        cmd += ["-metadata", "album="+video_metadata[u"album"]]
        cmd += ["-metadata", "comment="+id]

        out_path = os.path.join(self.normalized_folder, video_metadata[u"title"]+".mp3")
        cmd += ["-map", "[out]", out_path]

        self.call(*cmd)
        
    def monoize_video(self, id):
        video_metadata = self.get_metadata(id)
        in_path = os.path.join(self.normalized_folder, video_metadata["title"]+".mp3")

        cmd = [self.ffmpeg, "-i", in_path, "-b:a", "256k", "-ac", "1", "-y"]

        cmd += ["-map_metadata", "0"]
        cmd += ["-metadata", "album="+video_metadata[u"album"]+" [Mono]"]
        out_path = os.path.join(self.monoized_folder, video_metadata[u"title"]+".mp3")
        cmd += [out_path]

        self.call(*cmd)

    def update_progress_bar(self, label, amount, max_amount, message, length = 80, fill = '█'):
        #if message != "":
            #print "\r"+message+' '*(length+100)
        if max_amount == 0:
            max_amount = 1
        percent = ("{0:.1f}").format(100 * (amount / float(max_amount)))
        filled_length = int(length * amount // max_amount)
        bar = fill * filled_length + '-' * (length - filled_length)
        sys.stdout.write('\r%s: |%s| %s%% Complete\r' % (label, bar, percent)) #, end = '\r')
        sys.stdout.flush()
        
    def run(self):
        print "Getting list of videos in playlist..."
        self.videos = self.get_videos_in_playlist()
        self.playlist_ids = set([])
        for video in self.videos:
            self.playlist_ids.add(video["id"])

        print "Cleaning up music and inferring metadata..."
        self.clean_and_scan_folders()
            
        if self.download_videos == "NONE":
            self.to_download = set([])
        elif self.download_videos == "ALL":
            self.to_download = self.playlist_ids.union(set([]))
        else:
            self.to_download = self.playlist_ids - self.downloaded_ids
            
        if self.normalize_videos == "NONE":
            self.to_normalize = set([])
        elif self.normalize_videos == "ALL":
            self.to_normalize = self.downloaded_ids.union(self.to_download)
        else:
            self.to_normalize = self.downloaded_ids.union(self.to_download) - self.normalized_ids

        if self.monoize_videos == "NONE":
            self.to_monoize = set([])
        elif self.monoize_videos == "ALL":
            self.to_monoize = self.normalized_ids.union(self.to_normalize)
        else:
            self.to_monoize = self.normalized_ids.union(self.to_normalize) - self.monoized_ids

        print "Planning to download "+str(len(self.to_download))+" videos, normalize "+str(len(self.to_normalize))+" mp3s and monoize "+str(len(self.to_monoize))+" mp3s."
        if len(self.to_download) + len(self.to_normalize) + len(self.to_monoize) == 0:
            print "Nothing to do, quitting..."
            self.clean_up()
        if (self.debug):
            print "Downloading: "
            print self.to_download
            print "Normalizing: "
            print self.to_normalize
            print "Monoizing: "
            print self.to_monoize
        if not self.get_input("Continue?", is_boolean=True):
            self.clean_up()

        for id in self.playlist_ids:
            self.get_metadata(id)
        self.save_metadata()
        for id in self.to_download:
            self.download_video(id)
        normalized_videos = 0
        if not self.debug:
            self.update_progress_bar("Normalized", normalized_videos, len(self.to_normalize), "Normalizing...")
        for id in self.to_normalize:
            self.normalize_video(id)
            normalized_videos += 1
            if not self.debug:
                self.update_progress_bar("Normalized", normalized_videos, len(self.to_normalize), self.get_metadata(id)[u"title"])
        monoized_videos = 0
        if not self.debug:
            print ""
            self.update_progress_bar("Monoized", monoized_videos, len(self.to_monoize), "Monoizing...")
        for id in self.to_monoize:
            self.monoize_video(id)
            monoized_videos += 1
            if not self.debug:
                self.update_progress_bar("Monoized", monoized_videos, len(self.to_monoize), self.get_metadata(id)[u"title"])

        self.clean_up()

    def clean_up(self):
        self.save_metadata()
        sys.exit(0)
