import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

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


def find_album_songs(title, artist):
    query = "{art} {title}".format(art=artist, title=title).replace(" ", "+")
    search = "https://www.google.com/search?q={query}+songs&ie=utf-8&oe=utf-8'".format(query=query)

    res = requests.get(search, headers=HEADERS_GET)
    print(res)
    res = res.text

    soup = BeautifulSoup(res, 'html.parser')

    with open(R"C:\Users\User\git\YoutubeSongsDownloader\{}.html".format(title), 'w', encoding='utf-8') as f:
        f.write(res)

    songs = [tag.text for tag in soup.find_all(attrs=GOOGLE_SONG_TAG_ATTRS)]

    if soup.find(attrs=GOOGLE_LENGTH_TAG_ATTRS) is not None:
        lengths = [tag.text for tag in soup.find_all(attrs=GOOGLE_LENGTH_TAG_ATTRS)]
    else:
        lengths = [None] * len(songs)

    return dict(zip(songs, lengths))


def download_song(title, artist, length=None):
    query = 'https://www.youtube.com/results?search_query={artist}+{title}+lyrics'.format(artist=artist, title=title)
    chosen = None
    for i in range(3):
        try:
            res = requests.get(query).text  # not using headers intentionally - returns easier to handle data without it
            soup = BeautifulSoup(res, 'html.parser')
            chosen = choose_item(soup, title, artist, length)
            break
        except Exception as e:
            raise e
            #print("{} failed. trying again...".format(title))

    try:
        with open(r"C:\Users\User\git\YoutubeSongsDownloader\search_query={artist}+{title}+lyrics.html".format(artist=artist, title=title), 'w', encoding='utf-8') as f:
            f.write(res)
    except:
        pass

    if chosen is None:
        print("cant find or parse {} on youtube".format(title))
        return




def choose_item(soup, title, artist, wanted_length=None, num_of_choises=3):
    if num_of_choises > 5:
        print ("no more than 5 options")
        raise ValueError

    print("wanted data: {} {} {}".format(title, artist, wanted_length))

    tags = [tag for tag in soup.find_all(attrs=YOUTUBE_ITEM_ATTRS)][0:num_of_choises]
    if tags == []:
        print("NO VIDEOS FOUND FOR SONG: {}".format(title))
        return

    score = [n for n in range(num_of_choises * 2, 0, -2)]

    item_names = [tag.text.split('- Duration:')[0] for tag in tags]
    forbidden_words = re.compile('.*\W(cover|live)\W.*', re.IGNORECASE)
    for i, name in enumerate(item_names):
        if title.lower() in name.lower():
            score[i] += 1
        if artist.lower() in name.lower():
            score[i] += 0.5
        if forbidden_words.match(name):
            score[i] -= 9999

    print("item names: {}".format(item_names))



    delta = [9999] * num_of_choises
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

    for i in range(len(score)):
        if delta[i] == 9999 and wanted_length is not None:
            score[i] -= 9999
        elif delta[i] == 9999 and wanted_length is None:
            pass
        elif delta[i] == min(delta) or delta[i] < accepted_seconds_error:
            score[i] += 5

    print("delta = {}".format(delta))


    item_views_text = [tag.text.split('ago')[-1] if 'views' in tag.text else '0 views' for tag in soup.find_all(attrs=YOUTUBE_VIEWS_ATTRS)][0:num_of_choises]
    item_views = [int(string.split(' ')[0].replace(',', '')) for string in item_views_text]


    for i in range(len(score)):
        if item_views[i] == max(item_views):
            score[i] += 2
        elif item_views[i] == 0:
            score[i] -= 9999

    print("views: {}".format(item_views))

    items_hrefs = ['https://www.youtube.com/{}'.format(tag.find_next('a', href=True).get('href')) for tag in tags]


    print("item hrefs: {}".format(items_hrefs))
    print("score:{}".format(score))
    print('\n\n')

    return items_hrefs[score.index(max(score[::-1]))]


def main():
    album_title = input("Album Title:\n")
    artist = input("Album Artist:\n")
    songs = find_album_songs(album_title, artist)

    print("songs: {}\n".format(songs))

    for song in songs:
        download_song(song, artist, length=songs[song])


if __name__ == "__main__":
    main()