def URLize_search(query):
    """
    This function gets the raw data that the user want to search on YouTube, and returns the url of that YouTube search
    :param query: what to search on YouTube
    :type query: str
    :return: The URL of the google search
    """
    url = 'https://www.youtube.com/results?search_query={query}'.format(query=query).replace(" ", "+")
    return url
