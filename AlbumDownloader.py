import requests
from bs4 import BeautifulSoup
import re


def find_songs(title, artist, first_song, songs_amount):
    query = "{art} {title}".format(art=artist, title=title).replace(" ", "+")
    search = "http://www.google.com/search?q={query}+songs".format(query=query)
    res = requests.get(search).text
    soup = BeautifulSoup(res)

    with open(R"C:\Users\User\git\YoutubeSongsDownloader\{}.html".format(title), 'w') as f:
        f.write(res)

    navigate_string = soup.find(text=re.compile(first_song, re.IGNORECASE))
    first_song = navigate_string.title()
    if navigate_string is None:
        print("could not find that first song... sure its this? {}".format(first_song))
        raise ValueError
    else:
        parent = navigate_string.find_parent()
        while not parent.has_attr("class"):
            parent = parent.find_parent()
        parent_class = " ".join(parent.get("class"))
        tags = [tag.text for tag in soup.find_all(attrs={'class' : parent_class})]
        songs = [song for song in tags[tags.index(first_song): tags.index(first_song) + songs_amount]]

    return songs

def main():
    params = list()
    params.append(input("Album Title:\n"))
    params.append(input("Album Artist:\n"))
    params.append(input("first song name:\n"))
    params.append(input("number of songs:\n"))
    print(find_songs(title=params[0], artist=params[1], first_song=params[2], songs_amount=int(params[3])))




if __name__ == "__main__":
    main()