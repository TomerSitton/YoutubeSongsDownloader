import Google
from bs4 import BeautifulSoup
import re

DOMAIN = "en.wikipedia.org"


def get_albums_songs(artist, album):
    """
    Search "<artist>+<album_title>+songs" in wikipedia.
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
    res = Google.feeling_lucky("{art} {album}".format(art=artist, album=album), site=DOMAIN)
    soup = BeautifulSoup(res, 'html.parser')

    tracklist_table = soup.find(name='table', attrs={'class', 'tracklist'})
    songs_dict = _parse_tracklist(tracklist_table)

    return songs_dict



def _parse_tracklist(tracklist_table):
    """
    This function parses the tracklist table.
    It return a dictionary with the songs names as keys and the songs lengths as values
    if the table does not contain songs, return an empty dict.
    if the table does not contain lengths of the songs, return the dict with lengths equal to None.
    :param tracklist_table:
    :return:
    """
    songs_dict = {}
    table_headers = [th.text for th in tracklist_table.find(name='tr').find_all('th')]
    if 'Title' in table_headers:
        title_column_index = table_headers.index('Title')
        if 'Length' not in table_headers:
            for row in tracklist_table.find_all(name='tr'):
                columns = row.find_all(name='td')
                if len(columns) == len(table_headers):  # if song (and not summary of table)
                    title_regex = re.compile(r'\w.*')

                    titles = columns[title_column_index].get_text(separator='======').split('======')
                    title_match = list(
                        filter(lambda title_try: title_try is not None,
                               [title_regex.match(txt.strip('"')) for txt in titles]))[
                        0]
                    title = title_match.string.strip('\n')
                    songs_dict[title] = None
        else:
            length_column_index = table_headers.index('Length')
            for row in tracklist_table.find_all(name='tr'):
                columns = row.find_all(name='td')
                if len(columns) == len(table_headers):  # if song (and not summary of table)
                    title_regex = re.compile(r'\w.*')

                    titles = columns[title_column_index].get_text(separator='======').split('======')
                    title_match = list(
                        filter(lambda title_try: title_try is not None,
                               [title_regex.match(txt.strip('"')) for txt in titles]))[
                        0]
                    title = title_match.string.strip('\n')

                    length_regex = re.compile(r'\d{1,2}:\d{1,2}')
                    lengths = columns[length_column_index].get_text(separator='======').split('======')
                    length_match = \
                        list(filter(lambda len_try: len_try is not None,
                                    [length_regex.match(txt.strip('"')) for txt in lengths]))[
                            0]
                    length = length_match.string.strip('\n')
                    songs_dict[title] = length

    return songs_dict

