import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
import youtube_dl
import ffmpeg

#TODO - use youtubedl for the video length, title, viewcount etc...?

MODE = 'DEBUG'

HEADERS_GET = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:49.0) Gecko/20100101 Firefox/49.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}
GOOGLE_SONG_TAG_ATTRS = {"class": "title"}
#GOOGLE_LENGTH_TAG_ATTRS = [{"class": "NmQOSc"}, {"class": "ooYbic"}]
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


def download_song(song_title, artist, length=None):
    query = 'https://www.youtube.com/results?search_query={artist}+{title}+lyrics'.format(artist=artist,
                                                                                          title=song_title)
    chosen = None
    for i in range(3):
        try:
            res = requests.get(query).text  # not using headers intentionally - returns easier to handle data without it
            soup = BeautifulSoup(res, 'html.parser')
            chosen = choose_video(soup, song_title, artist, length)
            break
        except Exception as e:
            print("{} failed. trying again...".format(song_title))

    if MODE == 'DEBUG':
        try:
            with open(r"C:\Users\User\git\YoutubeSongsDownloader\search_query={artist}+{title}+lyrics.html".format(artist=artist, title=song_title), 'w', encoding='utf-8') as f:
                f.write(res)
        except:
            pass

    if chosen is None:
        print("cant find or parse {} on youtube".format(song_title))
        return

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': r'C:\Users\User\Downloads\youtube\{artist}-{title}.mp3'.format(title=song_title, artist=artist),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192'
            }],
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([chosen])


def __score_video_name__(soup, song_title, artist, num_of_choices):
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
    return [n for n in range(num_of_choices * 2, 0, -2)]


def __score_video_length__(soup, wanted_length, num_of_choices):
    tags = [tag for tag in soup.find_all(attrs=YOUTUBE_ITEM_ATTRS)][0:num_of_choices]
    delta = [9999] * num_of_choices
    accepted_seconds_error = 10
    if wanted_length is not None:
        time_format = '%M:%S'
        if wanted_length.count(':') == 2:
            time_format = '%H:' + time_format
        wanted_time = datetime.strptime(wanted_length, time_format)
        item_times = [tag.text.split('- Duration:')[1].strip().strip('.') if '- Duration:' in tag.text else None for tag in tags]
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
    score = [x + y for x, y in zip(score, __score_video_length__(soup, wanted_length, num_of_choices))]
    score = [x + y for x, y in zip(score, __score_video_views_count__(soup, num_of_choices))]

    items_hrefs = ['https://www.youtube.com/{}'.format(tag.find_next('a', href=True).get('href')) for tag in tags]
    print("item hrefs: {}".format(items_hrefs))
    print("score:{}".format(score))
    print('\n\n')

    return items_hrefs[score.index(max(score[::-1]))]


def main():
    album_title = input("Album Title:\n")
    artist = input("Album Artist:\n")
    songs_dict = find_album_songs(album_title, artist)

    print("songs dict: {}\n".format(songs_dict))

    for song_title in songs_dict:
        download_song(song_title, artist, length=songs_dict[song_title])


if __name__ == "__main__":
    main()
