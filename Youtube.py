import requests


HEADERS_GET = {
    'User-Agent': ('Mozilla/5.0 (X11; Linux x86_64) '
     'AppleWebKit/537.36 (KHTML, like Gecko) '
     'Chrome/57.0.2987.110 '
     'Safari/537.36'),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}



def URLize_search(query):
    """
    This function gets the raw data that the user want to search on YouTube, and returns the url of that YouTube search
    :param query: what to search on YouTube
    :type query: str
    :return: The URL of the google search
    """
    url = 'https://www.youtube.com/results?search_query={query}'.format(query=query).replace(" ", "+")
    return url


def youtube_search(query, headers='default'):
    """
    search something on YouTube.
    :param query: what to search on YouTube
    :param headers: request header. default to default header. set None for no header at all.
    :return: the html of the search response
    """
    query_url = URLize_search(query)
    if not headers:
        res = requests.get(query_url)
    elif headers == 'default':
        res = requests.get(query_url, headers=HEADERS_GET)
    else:
        res = requests.get(query_url, headers=headers)
    return res.text
