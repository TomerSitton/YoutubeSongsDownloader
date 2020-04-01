import requests
from bs4 import BeautifulSoup

HEADERS_GET = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:49.0) Gecko/20100101 Firefox/49.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}
SONG_TAG_ATTRS = {"class": "title"}
LENGTH_TAG_ATTRS = {"class": "NmQOSc"}


def find_songs(title, artist):
    query = "{art} {title}".format(art=artist, title=title).replace(" ", "+")
    search = "https://www.google.com/search?q={query}+songs&ie=utf-8&oe=utf-8'".format(query=query)
    res = requests.get(search, headers=HEADERS_GET).text
    soup = BeautifulSoup(res, 'html.parser')

    with open(R"C:\Users\User\git\YoutubeSongsDownloader\{}.html".format(title), 'w', encoding='utf-8') as f:
        f.write(res)

    songs = [tag.text for tag in soup.find_all(attrs=SONG_TAG_ATTRS)]

    if soup.find(attrs=LENGTH_TAG_ATTRS) is not None:
        lengths = [tag.text for tag in soup.find_all(attrs=LENGTH_TAG_ATTRS)]
    else:
        lengths = [None] * len(songs)

    return dict(zip(songs, lengths))


def main():
    params = list()
    params.append(input("Album Title:\n"))
    params.append(input("Album Artist:\n"))
    print(find_songs(title=params[0], artist=params[1]))


if __name__ == "__main__":
    main()