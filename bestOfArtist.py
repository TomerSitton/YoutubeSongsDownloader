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


def fromTopTen(artist, how_many):
    """

    :param artist: the name of the artist
    :type artist: str
    :param how_many: how many albums the user wants to download
    :type how_many: int
    :return: a list of (album, artist) with all the albums or None if nothing found
    """

    to_return = []
    search = "https://www.google.com/search?q={artist}+albums+site:https://www.thetoptens.com/".format(
        artist=artist)
    res = requests.get(search, headers=HEADERS_GET).text
    soup = BeautifulSoup(res, 'html.parser')

    all_results_names = [tag.text for tag in soup.find_all(
        attrs={"class": "LC20lb DKV0Md"})]  # the name that google shows in the results page
    if not all_results_names:
        return None

    first_results_name = str(all_results_names[0])
    if "album" not in first_results_name.lower() or artist.lower() not in first_results_name.lower():  # checks if the first result have "album" and the artist name in it
        return None

    tag = [tag for tag in soup.find_all(attrs={"class": "r"})][0]
    items_href = tag.find_next('a', href=True).get('href')  # gets the href of the first result

    print(items_href)
    res = requests.get(items_href, headers=HEADERS_GET).text
    soup = BeautifulSoup(res, 'html.parser')
    albums = [tag.findChild(name='b').text for tag in
              soup.find_all(attrs={"class": "i hasimage image100"})]  # gets the albums in order

    if len(albums) < how_many:
        actual_how_many = len(albums)
        print("we were able to locate only {} albums and not {}".format(actual_how_many, how_many))
    else:
        actual_how_many = how_many

    [to_return.append((albums[i], artist)) for i in range(actual_how_many)]  # move only the number of albums wanted into the to_return
    print(to_return)
    print("from The Top Ten")
    return to_return


def fromMetacritic(artist, how_many):
    """

    :param artist: the name of the artist
    :type artist: str
    :param how_many: how many albums the user wants to download
    :type how_many: int
    :return: a list of (album, artist) with all the albums or None if nothing found
    """

    to_return = []
    query = "{artist}".format(artist=artist).replace(" ", "-").replace("&", "and")
    search = "https://www.metacritic.com/person/{query}?filter-options=music&sort_options=metascore&num_items=100".format(
        query=query)
    res = requests.get(search, headers=HEADERS_GET).text
    soup = BeautifulSoup(res, 'html.parser')
    albums = [tag.findChild(name='a').text for tag in soup.find_all(attrs={"class": "title brief_metascore"})] # gets the albums in order
    print(albums)
    gamesOrMusic = [tag.text for tag in soup.find_all(attrs={"class": "active"})] # is the page is about music or game

    if albums and gamesOrMusic and gamesOrMusic[0] == "Music":

        if len(albums) < how_many:
            actual_how_many = len(albums)
            print("we were able to locate only {} albums and not {}".format(actual_how_many, how_many))
        else:
            actual_how_many = how_many

        [to_return.append((albums[i], artist)) for i in range(actual_how_many)]  # move only the number of albums wanted into the to_return
        print(to_return)

        print("from Metacritic")
        return to_return


def fromRateYourMusic(artist, how_many):
    """

     :param artist: the name of the artist
     :type artist: str
     :param how_many: how many albums the user wants to download
     :type how_many: int
     :return: a list of (album, artist) with all the albums or None if nothing found
     """

    to_return = []
    query = artist.lower().replace(" ", "_")
    search = "https://rateyourmusic.com/artist/{query}".format(query=query)
    res = requests.get(search, headers=HEADERS_GET).text.split('disco_header_top')
    soup = BeautifulSoup(res[1], 'html.parser')
    albums = [tag.text for tag in soup.find_all(attrs={"class": "album"})] #get the albums
    rating = [tag.text for tag in soup.find_all(attrs={"class": "disco_avg_rating"})] #get the rating by the albums order
    albums = [album for _, album in sorted(zip(rating, albums))] #sorting the albums by the rating
    albums.reverse()
    if len(albums) < how_many:
        actual_how_many = len(albums)
        print("we were able to locate only {} albums and not {}".format(actual_how_many, how_many))
    else:
        actual_how_many = how_many

    [to_return.append((albums[i], artist)) for i in range(actual_how_many)]
    print(to_return)
    print("from Rate Your Music")
    return to_return


def getTheBestOfArtist(artist, how_many):
    top_ten = fromTopTen(artist, how_many)
    if top_ten is not None and input("are you ok with this (y/n):\n").lower() == "y":
        return top_ten

    metacritic = fromMetacritic(artist, how_many)
    if metacritic is not None and input("are you ok with this (y/n):\n").lower() == "y":
        return metacritic

    rate_your_music = fromRateYourMusic(artist, how_many)
    if rate_your_music is not None and input("are you ok with this (y/n):\n").lower() == "y":
        return rate_your_music
    return None
