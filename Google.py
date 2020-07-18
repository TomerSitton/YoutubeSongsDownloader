import requests
from bs4 import BeautifulSoup

GOOGLE_SEARCH_RESULTS_ATTRS = {'class': 'r'}
SONG_TAG_ATTRS = {"class": "title"}  # google album search
LENGTH_TAG_ATTRS = {"class": "Li8Y0e fRmlm"}  # google album search

HEADERS_GET = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:49.0) Gecko/20100101 Firefox/49.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}


def URLize_search(query, site=None):
    """
    This function gets the raw data that the user want to search in google, and returns the url of that google search
    :param query: what to search on google
    :type query: str
    :param site: site flag. if want to filter results only from a specific file.
    :type site: str
    :return: The URL of the google search
    """
    if site:
        url_struct = "https://www.google.com/search?q={query}+site:{site}&ie=utf-8&oe=utf-8"
    else:
        url_struct = "https://www.google.com/search?q={query}&ie=utf-8&oe=utf-8"

    url = url_struct.format(query=query, site=site).replace(" ", "+")
    return url


def google_search(query, site=None, headers='default'):
    """
    search something on google.
    :param query: what to search on google
    :param site: site flag. if want to filter results only from a specific file.
    :param headers: request header. default to default header. set None for no header at all.
    :return: the html of the search response
    """
    query_url = URLize_search(query, site)
    if not headers:
        res = requests.get(query_url)
    elif headers == 'default':
        res = requests.get(query_url, headers=HEADERS_GET)
    else:
        res = requests.get(query_url, headers=headers)
    return res.text


def feeling_lucky(query, site=None, headers='default'):
    """
    returns the html of the first google search result
     :param query: what to search on google
    :param site: site flag. if want to filter results only from a specific file.
    :param headers: request header. default to default header. set None for no header at all.
    :return: the html of the first google search result
    """
    res = google_search(query, site, headers)
    soup = BeautifulSoup(res, 'html.parser')
    first_result_link = soup.find(name='div', attrs=GOOGLE_SEARCH_RESULTS_ATTRS).findChild(name='a').get(key='href')

    if not headers:
        res = requests.get(first_result_link)
    elif headers == 'default':
        res = requests.get(first_result_link, headers=HEADERS_GET)
    else:
        res = requests.get(first_result_link, headers=headers)
    return res.text


def get_albums_songs(artist, album):
    """
    Search "<artist>+<album_title>+songs" on google.
    return a dictionary with the songs names as keys and the songs lengths as values
    if failed to find the album, return an empty dict.
    if failed to find the lengths of the songs, return the dict with lengths equal to None.
    :param artist: The artist of the album
    :type artist: str
    :param album: The name of the album
    :type album: str
    :return: A dict of the songs names as keys and lengths as values
    :rtype: dict of {string: string}. for example: {"song_exm": "03:25"}
    """
    search = "{} {} songs".format(artist, album)
    res = google_search(search)
    soup = BeautifulSoup(res, 'html.parser')

    songs = [tag.text for tag in soup.find_all(attrs=SONG_TAG_ATTRS)]
    lengths = [tag.text for tag in soup.find_all(attrs=LENGTH_TAG_ATTRS)]

    if not songs:
        songs_dict = {}
    elif not lengths:
        songs_dict = dict(zip(songs, [None] * len(songs)))
    else:
        songs_dict = dict(zip(songs, lengths))

    return songs_dict
