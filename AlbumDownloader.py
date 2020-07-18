from os.path import expanduser
import re
from datetime import datetime
from tkinter.filedialog import askdirectory
import requests
import youtube_dl
from bs4 import BeautifulSoup
from mutagen.id3 import ID3, TPE1, TIT2, TPE2, TRCK, TALB, TORY, TYER, ID3NoHeaderError, USLT, TCON, Encoding
from pydub import AudioSegment
import Google
import Wikipedia
import Youtube

HEADERS_GET = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:49.0) Gecko/20100101 Firefox/49.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

YOUTUBE_ITEM_ATTRS = {"class": "yt-lockup-title"}  # youtube song search
YOUTUBE_VIEWS_ATTRS = {"class": "yt-lockup-meta-info"}  # youtube song search
GOOGLE_DATE_ATTRS = {"class": "Z0LcW"}  # google album year search



def find_album_songs(album_title, artist):
    """
    Search "<artist>+<album_title>+songs" on google.
    if search did not get the expected html result, or the result does not contain the lengths of the songs,
    search the "<artist>+<album_title>+songs" on Wikipedia.
    return a dictionary with the songs names as keys and the songs lengths as values.
    if failed to find the album in both google and Wikipedia, return an empty dict.
    if failed to find the lengths of the songs in both google and Wikipedia, lengths will be None.

    :param album_title: The name of the album
    :type album_title: str
    :param artist: The artist of the album
    :type artist: str
    :return: A dict of the songs names as keys and lengths as values
    :rtype: dict of {string: string}. for example: {"song_exm": "03:25"}
    """
    songs_dict = Google.get_albums_songs(artist, album_title)

    if not songs_dict:
        songs_dict = Wikipedia.get_albums_songs(artist, album_title)
    elif None in songs_dict.values():
        wiki_songs_dict = Wikipedia.get_albums_songs(artist, album_title)
        if wiki_songs_dict:
            if None not in wiki_songs_dict.values():
                songs_dict = wiki_songs_dict

    return songs_dict


def __score_video_name__(soup, song_title, artist, num_of_choices):
    """
    give score to the videos by their title.
    artist in video name grants 0.5 points, and song_title grants 1 point.
    Forbidden words in the video's title grants -9999 points.
    Forbidden words:
        1. cover
        2. live
    :param soup: the soup of the youtube request
    :type soup: BeautifulSoup object
    :param song_title: the title of the song
    :type song_title: str
    :param artist: the artist of the song
    :type artist: str
    :param num_of_choices: the number of videos to choose from
    :type num_of_choices: int
    :return: list of scores of the videos. sorted as the videos are sorted in the youtube search result.
    :rtype: list of ints
    """
    forbidden_words = re.compile('.*\W(cover|live)\W.*', re.IGNORECASE)
    score = [0] * num_of_choices
    tags = [tag for tag in soup.find_all(attrs=YOUTUBE_ITEM_ATTRS)][0:num_of_choices]
    item_names = [tag.text.split('- Duration:')[0] for tag in tags]
    for i, name in enumerate(item_names):
        if song_title.lower() in name.lower():
            score[i] += 1
        if artist.lower() in name.lower():
            score[i] += 0.5
        if forbidden_words.match(name):
            score[i] -= 9999
    return score


def __score_video_position__(num_of_choices):
    """
    give score to the videos by there position in the youtube search.
    the last video gets 2 points, the next one gets 4, 6, 8....
    :param num_of_choices: the number of videos to choose from
    :type num_of_choices: int
    :return: list of scores of the videos. sorted as the videos are sorted in the youtube search result.
    :rtype: list of ints
    """
    return [n for n in range(num_of_choices * 2, 0, -2)]


def __score_video_length__(soup, num_of_choices, wanted_length=None, accepted_seconds_error=10):
    """
    give score to the videos by their lengths.
    if wanted_length given, the videos which:
        1. its length is closest to the wanted_length
        2. the diff between its length and wanted_length is lower or equals to accepted_seconds_error
    will get a score of 5.
    if wanted_length given, all other videos will get -9999 score.
    if wanted_length not given, score will be 0 for all videos.
    :param soup: the soup of the youtube request
    :type soup: BeautifulSoup object
    :param wanted_length: The desired length of the song. example: "2:15"
    :type wanted_length: str
    :param num_of_choices: the number of videos to choose from
    :type num_of_choices: int
    :return: list of scores of the videos. sorted as the videos are sorted in the youtube search result.
    :rtype: list of ints
    """
    tags = [tag for tag in soup.find_all(attrs=YOUTUBE_ITEM_ATTRS)][0:num_of_choices]
    delta = [9999] * num_of_choices
    if wanted_length is not None:
        time_format = '%M:%S'
        if wanted_length.count(':') == 2:
            time_format = '%H:' + time_format
        wanted_time = datetime.strptime(wanted_length, time_format)
        item_times = [tag.text.split('- Duration:')[1].strip().strip('.') if '- Duration:' in tag.text else None for tag
                      in tags]
        for i, time in enumerate(item_times):
            if time is None:
                delta[i] = 9999
                continue
            time_format = '%M:%S'
            if time.count(':') == 2:
                time_format = '%H:' + time_format
            option_time = datetime.strptime(time, time_format)
            delta[i] = (max(wanted_time, option_time) - min(wanted_time, option_time)).seconds

    score = [0] * num_of_choices
    for i in range(len(score)):
        if delta[i] == 9999 and wanted_length is not None:
            score[i] -= 9999
        elif delta[i] == 9999 and wanted_length is None:
            pass
        elif delta[i] == min(delta) or delta[i] < accepted_seconds_error:
            score[i] += 5
    return score


def __score_video_views_count__(soup, num_of_choices):
    """
    give score to the videos by their views count.
    the item with the max views count get 2 points.
    the other items get 0 points.
    item with no views field (indicating its a playlist) gets -9999 points.
    :param soup: the soup of the youtube request
    :type soup: BeautifulSoup object
    :param num_of_choices: the number of videos to choose from
    :type num_of_choices: int
    :return: list of scores of the videos. sorted as the videos are sorted in the youtube search result.
    :rtype: list of ints
    """
    score = [0] * num_of_choices
    item_views_text = [tag.text.split('ago')[-1] if 'views' in tag.text else '0 views' for tag in
                       soup.find_all(attrs=YOUTUBE_VIEWS_ATTRS)][0:num_of_choices]
    item_views = [int(string.split(' ')[0].replace(',', '')) for string in item_views_text]

    for i in range(len(score)):
        if item_views[i] == max(item_views):
            score[i] += 2
        elif item_views[i] == 0:
            score[i] -= 9999

    return score


def choose_video(soup, song_title, artist, wanted_length=None, num_of_choices=3):
    """
    gets a soup of a youtube song search and song data, and returns the url of the most relevant video from the top
    num_of_choices videos.
    The decision is based on some parameters:
        1. The position of the video in the youtube search (they have relevance algorithms to)
        2. The name of the video
        3. The diff between the length of the video and the wanted_length of the song
        4. The number of views of the video
    :param soup: the soup of the youtube request
    :type soup: BeautifulSoup object
    :param song_title: the title of the song
    :type song_title: str
    :param artist: the artist of the song
    :type artist: str
    :param wanted_length: The desired length of the song. example: "2:15"
    :type wanted_length: str
    :param num_of_choices:
    :param num_of_choices: the number of videos to choose from. not more than 5.
    :type num_of_choices: int
    """
    if num_of_choices > 5:
        print("no more than 5 options")
        raise ValueError

    print("wanted data: {} {} {}".format(song_title, artist, wanted_length))

    tags = [tag for tag in soup.find_all(attrs=YOUTUBE_ITEM_ATTRS)][0:num_of_choices]
    if not tags:
        print("NO VIDEOS FOUND FOR SONG: {}".format(song_title))
        return

    score = [0] * num_of_choices
    score = [x + y for x, y in zip(score, __score_video_position__(num_of_choices))]
    score = [x + y for x, y in zip(score, __score_video_name__(soup, song_title, artist, num_of_choices))]
    score = [x + y for x, y in zip(score, __score_video_length__(soup, num_of_choices, wanted_length))]
    score = [x + y for x, y in zip(score, __score_video_views_count__(soup, num_of_choices))]

    items_hrefs = ['https://www.youtube.com/{}'.format(tag.find_next('a', href=True).get('href')) for tag in tags]

    print("item hrefs: {}".format(items_hrefs))
    print("score:{}".format(score))
    print('\n\n')

    return items_hrefs[score.index(max(score[::-1]))]


def download_song(song_title, artist, output_dir, wanted_length=None):
    """
    searches for "song" on youtube and download the most relevant result to output_dir.
    returns the path to the new downloaded file. None if download failed.
    :param song_title: the title of the song
    :type song_title: str
    :param artist: the artist of the song
    :param wanted_length: The desired length of the song. example: "2:15"
    :type wanted_length: str
    :param output_dir: the dir to save the downloaded file in
    :return:
    """
    query = Youtube.URLize_search('{artist} {title} lyrics'.format(artist=artist,title=song_title))

    res = requests.get(query).text  # not using headers intentionally - returns easier to handle data without it
    soup = BeautifulSoup(res, 'html.parser')
    chosen = choose_video(soup, song_title, artist, wanted_length)

    if chosen is None:
        print("cant find or parse {} on youtube".format(song_title))
        with open(r"C:\Users\User\git\YoutubeSongsDownloader\search_query={artist}+{title}+lyrics.html".format(
                artist=artist, title=song_title), 'w', encoding='utf-8') as f:
            f.write(res)
        return

    output_file = r'{out_dir}\{artist}-{title}.mp3'.format(out_dir=output_dir, title=song_title, artist=artist)

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_file,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192'
        }]
    }

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([chosen])
        output_file = r'{out_dir}\{artist}-{title}.mp3'.format(out_dir=output_dir, title=song_title, artist=artist)
    except Exception as e:
        print("e= " + str(e))
        if str(e) in "ERROR: ffprobe/avprobe and ffmpeg/avconv not found. Please install one.":
            output_file = r'{out_dir}\{artist}-{title}.mp3'.format(out_dir=output_dir, title=song_title,
                                                                   artist=artist)
            print("no ffprobe? check if works even without")
            raise e
        else:
            print("exception in youtube-dl")
            raise e

    return output_file


def add_mp3_metadata(file_path, title='Unknown', artist='Unknown', album='Unknown', index=0, year=""):
    """
    adds tags for the mp3 file (artist, album etc.)
    :param file_path: the path of the mp3 file that was downloaded
    :type file_path: str
    :param title: the title of the song
    :type title: str
    :param artist: the artist of the song
    :type artist: str
    :param album: the album that the song is part of
    :type album: str
    :param index: the index of the song in the album
    :type index: str
    :param year: the year of release of the song/ album
    :type year: str
    :return: None
    """

    try:
        print("replacing the file...")
        AudioSegment.from_file(file_path).export(file_path, format='mp3')
        print("writing tags on file...")
        print("{} {} {} {}".format(title, album, artist, index))
    except FileNotFoundError as e:
        print("failed to convert {} to mp3 because file not found: {}".format(title, e))
        return
    except Exception as e:
        print("unhandled exception in converting {} to mp3: {}".format(title, e))
        raise e

    if title is 'Unknown':
        title = file_path.split('\\')[-1].split('.')[0]
    try:
        audio = ID3(file_path)
    except ID3NoHeaderError:
        audio = ID3()

    audio.add(TIT2(encoding=3, text=title))
    audio['TIT2'] = TIT2(encoding=Encoding.UTF8, text=title)  # title
    audio['TPE1'] = TPE1(encoding=Encoding.UTF8, text=artist)  # contributing artist
    audio['TPE2'] = TPE2(encoding=Encoding.UTF8, text=artist)  # album artist
    audio['TALB'] = TALB(encoding=Encoding.UTF8, text=album)  # album
    audio['TRCK'] = TRCK(encoding=Encoding.UTF8, text=str(index))  # track number
    audio['TORY'] = TORY(encoding=Encoding.UTF8, text=str(year))  # Original Release Year
    audio['TYER'] = TYER(encoding=Encoding.UTF8, text=str(year))  # Year Of Recording

    audio.save(file_path)


def receive_album_request():
    """
    This function receives the sets of album and artist the user wants to download, and returns a list of them.
    :return: list of tuples of artist and album. [(artist0, album0), (artist1, album1), (artist2, album2)]
    :rtype: list of tuples of strings. [(str,str),(str,str),(str,str)]
    """
    usage_msg = """
        Hi there!
        This program is designed to download full albums from youtube!
        Enter the name of the artist and the album.
        When finished - press enter!
        """
    print(usage_msg)

    albums = []

    album_title = input("Album Title:(Enter to exit)\n")
    artist = input("Album Artist:\n")

    while album_title is not "" and artist is not "":
        albums.append((artist, album_title))
        album_title = input("Album Title:(Enter to exit)\n")
        if album_title is not "":
            artist = input("Album Artist:(Enter to exit)\n")

    return albums


def main():
    albums = receive_album_request()
    output_dir = expanduser("~\\Music")

    failed_downloads = {(artist, album): [] for (artist, album) in albums}

    for artist, album in albums:
        songs_dict = find_album_songs(album, artist)

        print("songs dict: {}\n".format(songs_dict))

        for i, song_title in enumerate(songs_dict):
            song_path = download_song(song_title, artist, output_dir=output_dir, wanted_length=songs_dict[song_title])
            if song_path is None:
                failed_downloads[(artist, album)].append(song_title)
                continue
            add_mp3_metadata(file_path=song_path, title=song_title, album=album, artist=artist, index=i + 1)

    print("FAILED downloads: {}".format(failed_downloads))


if __name__ == "__main__":
    main()
