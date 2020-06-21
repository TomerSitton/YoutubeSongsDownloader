import re
from datetime import datetime
from os import remove as removefile
from shutil import move as movefile

import ffmpeg
import requests
import youtube_dl
from bs4 import BeautifulSoup

# TODO - use youtubedl for the video length, title, viewcount etc...?
from bestOfArtist import getTheBestOfArtist

# MODE = 'DEBUG'
MODE = 'PRO'

HEADERS_GET = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:49.0) Gecko/20100101 Firefox/49.0',
    # 'User-Agent': 'Mozilla/5.0 (Linux; Android 7.0; SAMSUNG SM-G950F Build/NRD90M) AppleWebKit/537.36 (KHTML, like '
    #             'Gecko) SamsungBrowser/5.2 Chrome/51.0.2704.106 Mobile Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}
GOOGLE_SONG_TAG_ATTRS = {"class": "title"}
# GOOGLE_LENGTH_TAG_ATTRS = [{"class": "NmQOSc"}, {"class": "ooYbic"}]
GOOGLE_LENGTH_TAG_ATTRS = {"class": "Li8Y0e fRmlm"}
YOUTUBE_ITEM_ATTRS = {"class": "yt-lockup-title"}
YOUTUBE_VIEWS_ATTRS = {"class": "yt-lockup-meta-info"}


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

    if MODE == 'DEBUG':
        with open(R"C:\Users\User\git\YoutubeSongsDownloader\{}.html".format(album_title), 'w', encoding='utf-8') as f:
            f.write(res)

    songs = [tag.text for tag in soup.find_all(attrs=GOOGLE_SONG_TAG_ATTRS)]

    if soup.find(attrs=GOOGLE_LENGTH_TAG_ATTRS) is not None:
        lengths = [tag.text for tag in soup.find_all(attrs=GOOGLE_LENGTH_TAG_ATTRS)]
    else:
        lengths = [None] * len(songs)

    return dict(zip(songs, lengths))


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
    if tags is []:
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


def download_song(song_title, artist, wanted_length=None, output_dir=r"C:\Users\User\Music"):
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
    query = 'https://www.youtube.com/results?search_query={artist}+{title}+lyrics'.format(artist=artist,
                                                                                          title=song_title)
    chosen = None
    for i in range(3):
        try:
            res = requests.get(query).text  # not using headers intentionally - returns easier to handle data without it
            soup = BeautifulSoup(res, 'html.parser')
            chosen = choose_video(soup, song_title, artist, wanted_length)
            break
        except Exception as e:
            print("filed finding/paresing {} . trying again...".format(song_title))

    if chosen is None:
        print("cant find or parse {} on youtube".format(song_title))
        try:
            with open(r"C:\Users\User\git\YoutubeSongsDownloader\search_query={artist}+{title}+lyrics.html".format(
                    artist=artist, title=song_title), 'w', encoding='utf-8') as f:
                f.write(res)
        except:
            pass
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

    for i in range(3):
        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                ydl.download([chosen])
            output_file = r'{out_dir}\{artist}-{title}.mp3'.format(out_dir=output_dir, title=song_title, artist=artist)
            break
        except Exception as e:
            output_file = None
            print("{} failed. trying again...".format(song_title))

    return output_file


def add_mp3_metadata(file, title='Unknown', album='Unknown', artist='Unknown', index=0):
    print("{} {} {} {}".format(title, album, artist, index))
    if title is 'Unknown':
        title = file.split('\\')[-1].split('.')[0]
    tmp_file = file.split('.mp3')[0] + '-tmp.mp3'
    movefile(file, tmp_file)
    kwargs = {
        'metadata:g:0': "title={}".format(title),
        'metadata:g:1': "artist={}".format(artist),
        'metadata:g:2': "album={}".format(album),
        'metadata:g:3': "track={}".format(index)
    }
    out = (
        ffmpeg
            .input(tmp_file)
            .output(file, **kwargs)
    )
    out.run()
    removefile(tmp_file)


def recieve_album_request():
    usage_msg = """
        Hi there!
        This program is designed to download full albums from youtube!
        Enter the name of the artist and the album.
        When finished - press enter!
        """
    print(usage_msg)

    albums = []

    if input("do u want specific albums or best of artist (1 for specific, 2 for best of) \n") == '1':
        album_title = input("Album Title:(Enter to exit)\n")
        artist = input("Album Artist:\n")

        while album_title is not "" and artist is not "":
            albums.append((album_title, artist))
            album_title = input("Album Title:(Enter to exit)\n")
            if album_title is not "":
                artist = input("Album Artist:(Enter to exit)\n")

        return albums
    else:
        artist = input("Artist:\n")
        howMany = int(input("how many albums do you want from that artist\n"))

        while artist is not "":
            albums += getTheBestOfArtist(artist, howMany)
            artist = input("Artist:(Enter to exit)\n")
        return albums


def main():
    albums = recieve_album_request()
    print(albums)
    for album_title, artist in albums:
        songs_dict = find_album_songs(album_title, artist)

        print("songs dict: {}\n".format(songs_dict))

        for i, song_title in enumerate(songs_dict):
            song_path = download_song(song_title, artist, wanted_length=songs_dict[song_title], output_dir=r"C:\Users\talsi\Desktop\music from tomer")
            if song_path is None:
                print("failed download {}. please try again later".format(song_title))
                continue
            # add_mp3_metadata(file=song_path, title=song_title, album=album_title, artist=artist, index=i + 1)


if __name__ == "__main__":
    main()
