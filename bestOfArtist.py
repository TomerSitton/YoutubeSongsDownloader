import requests
from bs4 import BeautifulSoup

HEADERS_GET = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}
METACRITIC_ALBUMS_TAG_ATTRS = {"class": "title brief_metascore"}
RATE_YOUR_MUSIC_ALBUMS_TAG_ATTRS = {"class": "album"}
RATE_YOUR_MUSIC_RATING_TAG_ATTRS = {"class": "disco_avg_rating"}
METACRITIC_ACTIVE_TAG_ATTRS = {"class": "active"}


def fromTopTen(artist, howMany):
    toReturn = []
    search = "https://www.google.com/search?q={artist}+albums+site:https://www.thetoptens.com/".format(
        artist=artist)
    res = requests.get(search, headers=HEADERS_GET).text
    soup = BeautifulSoup(res, 'html.parser')

    name = [tag.text for tag in soup.find_all(attrs={"class": "LC20lb DKV0Md"})]
    if not name:
        return None

    name = name[0]
    tag = [tag for tag in soup.find_all(attrs={"class": "r"})][0]
    items_hrefs = tag.find_next('a', href=True).get('href')

    if "album" not in name.lower():
        return None

    print(items_hrefs)
    res = requests.get(items_hrefs, headers=HEADERS_GET).text
    soup = BeautifulSoup(res, 'html.parser')
    albums = [tag.text for tag in soup.find_all(attrs={"class": "i hasimage image100"})]
    if len(albums) < howMany:
        stuff = len(albums)
    else:
        stuff = howMany

    for i in range(stuff):
        albums[i] = albums[i].split('\n')[1]
        albums[i] = albums[i].split(" ", 1)[1]
        toReturn.append((albums[i], artist))
    print("from The Top Ten")
    return toReturn


def fromMetacritic(artist, howMany):
    toReturn = []
    query = "{artist}".format(artist=artist).replace(" ", "-").replace("&", "and")
    search = "https://www.metacritic.com/person/{query}?filter-options=music&sort_options=metascore&num_items=100".format(
        query=query)
    res = requests.get(search, headers=HEADERS_GET).text
    soup = BeautifulSoup(res, 'html.parser')
    albums = [tag.text for tag in soup.find_all(attrs=METACRITIC_ALBUMS_TAG_ATTRS)]
    gamesOrMusic = [tag.text for tag in soup.find_all(attrs=METACRITIC_ACTIVE_TAG_ATTRS)]
    print(gamesOrMusic)
    if albums and gamesOrMusic and gamesOrMusic[0] == "Music":
        if len(albums) < howMany:
            stuff = len(albums)
        else:
            stuff = howMany
        for i in range(stuff):
            albums[i] = albums[i][4:]
            albums[i] = albums[i][:-1]
            toReturn.append((albums[i], artist))
        print("from Metacritic")
        return toReturn


def fromRateYourMusic(artist, howMany):
    toReturn = []
    query = artist.lower().replace(" ", "_")
    search = "https://rateyourmusic.com/artist/{query}".format(query=query)
    res = requests.get(search, headers=HEADERS_GET).text
    res = res.split('disco_header_top')
    soup = BeautifulSoup(res[1], 'html.parser')
    albums = [tag.text for tag in soup.find_all(attrs=RATE_YOUR_MUSIC_ALBUMS_TAG_ATTRS)]
    rating = [tag.text for tag in soup.find_all(attrs=RATE_YOUR_MUSIC_RATING_TAG_ATTRS)]
    z = [album for _, album in sorted(zip(rating, albums))]
    z.reverse()
    if len(z) < howMany:
        stuff = len(z)
    else:
        stuff = howMany
    for i in range(stuff):
        toReturn.append((z[i], artist))
    print("from Rate Your Music")
    return toReturn


def getTheBestOfArtist(artist, howMany):
    j = fromTopTen(artist, howMany)
    if j is not None:
        return j
    j = fromMetacritic(artist, howMany)
    if j is not None:
        return j
    j = fromRateYourMusic(artist, howMany)
    if j is not None:
        return j


if __name__ == '__main__':
    print(getTheBestOfArtist("green day", 5))
