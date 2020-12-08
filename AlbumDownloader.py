import re
from datetime import datetime
from os.path import expanduser

import requests
import youtube_dl
from bs4 import BeautifulSoup
from googleapiclient.discovery import build as youtube_build
from mutagen.id3 import ID3, TPE1, TIT2, TPE2, TRCK, TALB, TORY, TYER, ID3NoHeaderError, Encoding
from pydub import AudioSegment

import important.APIKey as api

HEADERS_GET = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:49.0) Gecko/20100101 Firefox/49.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}
GOOGLE_SONG_TAG_ATTRS = {"class": "title"}  # google album search
GOOGLE_LENGTH_TAG_ATTRS = {"class": "Li8Y0e fRmlm"}  # google album search
YOUTUBE_ITEM_ATTRS = {"class": "yt-lockup-title"}  # youtube song search
YOUTUBE_VIEWS_ATTRS = {"class": "yt-lockup-meta-info"}  # youtube song search
GOOGLE_DATE_ATTRS = {"class": "Z0LcW"}  # google album year search
GOOGLE_SEARCH_RESULTS_ATTRS = {'class': 'yuRUbf'}

api_key = api.api_key


def find_album_songs_wiki(album_title, artist, google_songs=[]):
    """
    Search "<artist>+<album_title>+songs" in wikipedia.
    return a dictionary with the songs names as keys and the songs lengths
    as values (if no length tag in the google search, lengths will be None).
    :param album_title: The name of the album
    :type album_title: str
    :param artist: The artist of the album
    :type artist: str
    :return: A dict of the songs names as keys and lengths as values
    :rtype: dict of {string: string}. for example: {"song_exm": "03:25"}
    """
    query = "{art} {title}".format(art=artist, title=album_title).replace(" ", "+")
    search = "https://www.google.com/search?q={query}+site:en.wikipedia.org&ie=utf-8&oe=utf-8".format(query=query)
    res = requests.get(search, headers=HEADERS_GET).text
    soup = BeautifulSoup(res, 'html.parser')

    try:
        first_result_link = soup.find(name='div', attrs=GOOGLE_SEARCH_RESULTS_ATTRS).findChild(name='a').get(key='href')
    except AttributeError:
        print(f"couldn't find album {album_title} by {artist} on wikipedia")
        return
    res = requests.get(first_result_link, headers=HEADERS_GET).text
    with open(r"C:\Users\User\Music\{album}.html".format(album=album_title), "w", encoding='UTF-8') as f:
        f.write(res)

    soup = BeautifulSoup(res, 'html.parser')

    tracklist_table = soup.find(name='table', attrs={'class', 'tracklist'})
    table_headers = [th.text for th in tracklist_table.find(name='tr').find_all('th')]
    title_column_index = table_headers.index('Title')
    length_column_index = table_headers.index('Length')

    wiki_songs_dict = {}
    for row in tracklist_table.find_all(name='tr')[1::]:
        columns = row.find_all(name='th') + row.find_all(name='td')
        if len(columns) == len(table_headers):
            title_regex = re.compile(r'\w.*')
            length_regex = re.compile(r'\d{1,2}:\d{1,2}')

            titles = columns[title_column_index].get_text(separator='======').split('======')
            title_match = list(
                filter(lambda title_try: title_try is not None, [title_regex.match(txt.strip('"')) for txt in titles]))[
                0]
            title = title_match.string.strip('\n')

            lengthes = columns[length_column_index].get_text(separator='======').split('======')
            length_match = \
                list(filter(lambda len_try: len_try is not None,
                            [length_regex.match(txt.strip('"')) for txt in lengthes]))[
                    0]
            length = length_match.string.strip('\n')
            wiki_songs_dict[title] = length

    return wiki_songs_dict


def find_album_songs(album_title, artist):
    """
    Search "<artist>+<album_title>+songs" in google.
    return a dictionary with the songs names as keys and the songs lengths
    as values (if no length tag in the google search, lengths will be None).
    :param album_title: The name of the album
    :type album_title: str
    :param artist: The artist of the album
    :type artist: str
    :return: A dict of the songs names as keys and lengths as values
    :rtype: dict of {string: string}. for example: {"song_exm": "03:25"}
    """
    query = "{art} {title}".format(art=artist, title=album_title).replace(" ", "+")
    search = "https://www.google.com/search?q={query}+songs&ie=utf-8&oe=utf-8'".format(query=query)
    res = requests.get(search, headers=HEADERS_GET).text
    soup = BeautifulSoup(res, 'html.parser')

    songs = [tag.text for tag in soup.find_all(attrs=GOOGLE_SONG_TAG_ATTRS)]

    if soup.find(attrs=GOOGLE_LENGTH_TAG_ATTRS) is not None:
        lengths = [tag.text for tag in soup.find_all(attrs=GOOGLE_LENGTH_TAG_ATTRS)]
        songs_dict = dict(zip(songs, lengths))

    else:
        songs_dict = find_album_songs_wiki(album_title, artist, google_songs=songs)

    return songs_dict


def find_song_info(song_and_artists):
    """
   Search "<song_title>+<artist>+album" in google.
   return list of tuples of the album names and lengths of the song
   (if no length tag in the google search, lengths will be None
   if no album tag in the google search, album will be the song's name).
   :param song_and_artists: list of tuples with the songs name and artists
   :type song_and_artists: list
   :return: A list of tuples of the album names and lengths of the song
   :rtype: lst of (string, string). for example: [("album_exm", "03:25")]
   """
    output = []
    for song, artist in song_and_artists:
        query = f"{song} {artist}".replace(" ", "+")
        search = "https://www.google.com/search?q={query}+album&ie=utf-8&oe=utf-8'".format(query=query)
        res = requests.get(search, headers=HEADERS_GET).text
        soup = BeautifulSoup(res, 'html.parser')
        album = soup.find_all(attrs={"class": "FLP8od"})
        if not album:
            album = song
        else:
            album = album[0].text.split("/")[0]
        print(album)
        length = None
        album_info = find_album_songs(album, artist)
        for name in album_info:
            if song.lower() in name.lower():
                length = album_info[name]
                break
        output.append((album, length))
    return output


def __score_video_name__(item_names, song_title, artist, num_of_choices):
    """
    give score to the videos by their title.
    artist in video name grants 0.5 points, and song_title grants 1 point.
    Forbidden words in the video's title grants -9999 points.
    Forbidden words:
        1. cover
        2. live
    :param item_names: the list of the titles of the first 3 songs
    :type item_names: list
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


def __score_video_length__(item_times, num_of_choices, wanted_length=None, accepted_seconds_error=10):
    """
    give score to the videos by their lengths.
    if wanted_length given, the videos which:
        1. its length is closest to the wanted_length
        2. the diff between its length and wanted_length is lower or equals to accepted_seconds_error
    will get a score of 5.
    if wanted_length given, all other videos will get -9999 score.
    if wanted_length not given, score will be 0 for all videos.
    :param item_times: the list of times taken from the first 3 songs, Minutes:Seconds
    :type item_times: list
    :param wanted_length: The desired length of the song. example: "2:15"
    :type wanted_length: str
    :param num_of_choices: the number of videos to choose from
    :type num_of_choices: int
    :return: list of scores of the videos. sorted as the videos are sorted in the youtube search result.
    :rtype: list of ints
    """
    delta = [9999] * num_of_choices
    if wanted_length is not None:
        time_format = '%M:%S'
        if wanted_length.count(':') == 2:
            time_format = '%H:' + time_format
        wanted_time = datetime.strptime(wanted_length, time_format)
        wanted_seconds = wanted_time.second + wanted_time.minute * 60 + wanted_time.hour * 3600

        for i in range(len(item_times)):
            if item_times[i].split(":")[1] == "":
                item_times[i] += "0"
            elif item_times[i].split(":")[0] == "":
                item_times[i] = "0" + item_times[i]

        print(f"item_times= {item_times}")
        item_times = [int(length.split(":")[0]) * 60 + int(length.split(":")[1]) for length in item_times]

        for i, time in enumerate(item_times):
            if time is None:
                delta[i] = 9999
                continue
            delta[i] = max(wanted_seconds, time) - min(wanted_seconds, time)

    score = [0] * num_of_choices
    for i in range(len(score)):
        if delta[i] == 9999 and wanted_length is not None:
            score[i] -= 9999
        elif delta[i] == 9999 and wanted_length is None:
            pass
        elif delta[i] == min(delta) or delta[i] < accepted_seconds_error:
            score[i] += 5
    return score


def __score_video_views_count__(item_views, num_of_choices):
    """
    give score to the videos by their views count.
    the item with the max views count get 2 points.
    the other items get 0 points.
    item with no views field (indicating its a playlist) gets -9999 points.
    :param item_views: the list of the views from the first 3 songs
    :type video_items: list
    :param num_of_choices: the number of videos to choose from
    :type num_of_choices: int
    :return: list of scores of the videos. sorted as the videos are sorted in the youtube search result.
    :rtype: list of ints
    """
    score = [0] * num_of_choices

    for i in range(len(score)):
        if item_views[i] == max(item_views):
            score[i] += 2
        elif item_views[i] == 0:
            score[i] -= 9999

    return score


def choose_video(video_items, song_title, artist, wanted_length=None):
    """
    gets video items of a youtube songs that came from a search and song data, and returns the url of the most relevant
    video.
    The decision is based on some parameters:
        1. The position of the video in the youtube search (they have relevance algorithms to)
        2. The name of the video
        3. The diff between the length of the video and the wanted_length of the song
        4. The number of views of the video
    :param video_items: the list of youtube videos from youtube api
    :type video_items: list
    :param song_title: the title of the song
    :type song_title: str
    :param artist: the artist of the song
    :type artist: str
    :param wanted_length: The desired length of the song. example: "2:15"
    :type wanted_length: str
    """
    num_of_choices = len(video_items)

    if num_of_choices > 5:
        print("no more than 5 options")
        raise ValueError

    print("wanted data: {} {} {}".format(song_title, artist, wanted_length))

    if not video_items:
        print("NO VIDEOS FOUND FOR SONG: {}".format(song_title))
        return
    score = [0] * num_of_choices
    score = [x + y for x, y in zip(score, __score_video_position__(num_of_choices))]
    score = [x + y for x, y in zip(score, __score_video_name__([video["snippet"]["title"] for video in video_items],
                                                               song_title, artist, num_of_choices))]
    score = [x + y for x, y in zip(score, __score_video_length__(
        [video_item["contentDetails"]["duration"].strip("PTS").replace("M", ":") if "M" in video_item["contentDetails"][
            "duration"] else "0:" + video_item["contentDetails"]["duration"].strip('PTS') for video_item in
         video_items], num_of_choices,
        wanted_length))]

    score = [x + y for x, y in zip(score, __score_video_views_count__(
        [video["statistics"]["viewCount"] for video in video_items], num_of_choices))]

    items_hrefs = ['https://www.youtube.com/watch?v={}'.format(video["id"]) for video in video_items]

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

    youtube = youtube_build(serviceName='youtube', version='v3', developerKey=api_key)
    request = youtube.search().list(part="snippet", maxResults=3,
                                    q="{artist} {title} lyrics".format(artist=artist, title=song_title), type="video")
    respond = request.execute()
    items = respond['items']
    ids = ",".join([i["id"]["videoId"] for i in items])
    videos = youtube.videos().list(part="snippet,contentDetails,statistics", id=ids).execute()
    videoItems = videos["items"]

    chosen = choose_video(videoItems, song_title, artist, wanted_length)

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

    for i in range(3):
        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([chosen])
            output_file = r'{out_dir}\{artist}-{title}.mp3'.format(out_dir=output_dir, title=song_title, artist=artist)
            break
        except Exception as e:
            print("e= " + str(e))
            if str(e) in "ERROR: ffprobe/avprobe and ffmpeg/avconv not found. Please install one.":
                output_file = r'{out_dir}\{artist}-{title}.mp3'.format(out_dir=output_dir, title=song_title,
                                                                       artist=artist)
                break
            else:
                output_file = None
                print("{} failed. trying again...".format(song_title))

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
    :type index: int
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
        return

    if title is 'Unknown':
        title = file_path.split('\\')[-1].split('.')[0]
    try:
        audio = ID3(file_path)
    except ID3NoHeaderError as e:
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
    msg = """        
        Enter the name of the album and the artist.
        When finished - press enter!
        """
    print(msg)
    albums = []

    album_title = input("Album Title:(Enter to exit)\n")
    artist = input("Album Artist:\n")

    while album_title is not "" and artist is not "":
        albums.append((album_title, artist))
        album_title = input("Album Title:(Enter to exit)\n")
        if album_title is not "":
            artist = input("Album Artist:(Enter to exit)\n")

    return albums


def receive_songs_request():
    msg = """        
        Enter the name of the song and the artist.
        When finished - press enter!
        """
    print(msg)
    songs = []

    song_title = input("Song Title:(Enter to exit)\n")
    artist = input("Artist:\n")

    while song_title is not "" and artist is not "":
        songs.append((song_title, artist))
        song_title = input("Song Title:(Enter to exit)\n")
        if song_title is not "":
            artist = input("Album Artist:(Enter to exit)\n")

    return songs


def receive_requests():
    """
    make sure what the user wants, to download songs or to download full albums

    :return: true and list of tuples with albums and artists if want to download albums
            false and list of tuples with songs and artists if want to download songs
    :rtype tuple
    """
    usage_msg = """
        Hi there!
        This program is designed to download full albums or single songs from youtube!
        """
    print(usage_msg)
    albumsOrSongs = "a"
    while not albumsOrSongs == '1' and not albumsOrSongs == '2':
        albumsOrSongs = input("Do you want to download full albums or single songs?\n(1 or 2): ")
    if albumsOrSongs == '1':
        return True, receive_album_request()
    else:
        return False, receive_songs_request()


def handle_albums(albums, output_dir):
    for album_title, artist in albums:
        songs_dict = find_album_songs(album_title, artist)
        if songs_dict is None:
            continue
        print("songs dict: {}\n".format(songs_dict))

        for i, song_title in enumerate(songs_dict):
            song_path = download_song(song_title, artist, output_dir=output_dir, wanted_length=songs_dict[song_title])
            if song_path is None:
                print("failed download {}. please try again later".format(song_title))
                continue
            add_mp3_metadata(file_path=song_path, title=song_title, album=album_title, artist=artist, index=i + 1)


def handle_songs(songs, output_dir):
    songs_info = find_song_info(songs)
    if songs_info is None:
        pass
    print("songs dict: {}\n".format(songs_info))
    i = 0
    for album, length in songs_info:
        song_title = songs[i][0]
        song_artist = songs[i][1]
        song_path = download_song(song_title, song_artist, output_dir=output_dir, wanted_length=length)
        if song_path is None:
            print("failed download {}. please try again later".format(song_title))
            continue
        add_mp3_metadata(file_path=song_path, title=song_title, album=album, artist=song_artist)
        i += 1


def main():
    wantsAlbums, toDownload = receive_requests()
    output_dir = expanduser("~\\Music")
    if wantsAlbums:
        handle_albums(toDownload, output_dir)
    else:
        handle_songs(toDownload, output_dir)


if __name__ == "__main__":
    main()
