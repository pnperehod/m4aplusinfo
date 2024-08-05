import json
import io
import time

from PIL import Image
import oauth2 as oauth
import unidecode as unidec
import fuzzy_compare

base_url = 'https://api.discogs.com/database/search?q='
release_url = 'https://api.discogs.com/releases/'
top_url = 'https://api.discogs.com/'
cover_file = 'cover.jpg'
user_agent = 'detektor_radio'
viewer = None
release_info = {'album_name': '', 'year': ''}
proper_formats = ['lp', 'ep', 'cd', 'cdr', 'file', 'vinyl', 'compilation', 'sampler']
allowed_delta = 6
lower_limit = 52
MaxRating = 150
artist_found = False


def connect_oauth(oauth_info):
    # create oauth Consumer and Client objects using
    consumer = oauth.Consumer(oauth_info['consumer_key'], oauth_info['consumer_secret'])

    token = oauth.Token(key=oauth_info['oauth_token'], secret=oauth_info['oauth_token_secret'])
    client = oauth.Client(consumer, token)
    return client


def site_request(url, uagent, client):
    tries = 5
    while tries > 0:
        try:
            resp, content = client.request(url, headers={'User-Agent': uagent})
        except Exception as e:
            print(e)
            tries = tries - 1
            time.sleep(3)
            continue
        break
    if tries == 0:
        return None, None
    if resp['status'] != '200':
        return None, None
    return resp, content


def do_the_search(artist, title, master, client):
    if master:
        search_url = base_url + '+'.join(artist.split()) + '+' + '+'.join(
            title.split()) + '&type=master' + '&page=1&per_page=100'
    else:
        search_url = base_url + '+'.join(artist.split()) + '+' + '+'.join(
            title.split()) + '&type=release' + '&page=1&per_page=100'
    resp, content = site_request(search_url, user_agent, client)
    return resp, content


def no_comma(str):
    is_comma = str.find(',')
    if is_comma != -1:
        str = str[is_comma + 1:].strip() + ' ' + str[:is_comma].strip()
    return str


def no_brackets(str, brackets):  # brackets is a string of 2 symbols, like '()'
    open_bracket = str.find(brackets[0])
    close_bracket = str.find(brackets[1])
    if open_bracket != -1 and close_bracket != -1:
        str = str[:open_bracket].strip() + str[close_bracket + 1:]
    return str


def correct_name(str):
    str = str.replace('&', 'and')
    str = str.replace("\'", '%27')
    str = str.split('|')[1] if '|' in str else str
    # убирает все, что в скобках
    str = no_brackets(str, '[]')
    str = no_brackets(str, '()')
#    str = unidec.unidecode(str)
    str = str.lower()
    return str.strip()


def correct_artist_name(str):
    str = correct_name(str)
    #    if str.find('The') == 0:                # если The в начале имени
    #        str = str.replace('The', '', 1)     # убирает начальное The в имени
    #    str = no_comma(str)
    str = str[:-1] if (len(str) > 0) and ('*' == str[-1]) else str
    return str.strip()


def is_proper_format(media_type):
    for f in proper_formats:
        if f in media_type:
            return True
    return False


def same_artist(artist, release_artist):
    if artist in release_artist:
        return True
    if fuzzy_compare.fuzzy_compare(artist, release_artist) > lower_limit:
        return True
    return False


def get_proper_release(artist, title, release, media_format, albums_only, client):
    items = int(release['pagination']['items'])
    per_page = int(release['pagination']['per_page'])
    variants = items if items < per_page else per_page
    year_min = 9999
    pointer = -1
    for i in range(variants):
        try:
            year = int(release['results'][i]['year'])
            media_type = release['results'][i]['format']
            main_artist = release['results'][i]['title']
        except:
            continue
        try:
            master = True
            id = release['results'][i]['master_id']
        except:
            master = False
            id = release['results'][i]['release_id']
        if id == 0:
            master = False
            id = release['results'][i]['id']

        main_artist = main_artist.split(' - ')[0]
        main_artist = correct_artist_name(main_artist)
        artist = correct_artist_name(artist)
        for med in range(len(media_type)):
            media_type[med] = media_type[med].lower()

        if media_format == 'compilation' or media_format == 'sampler':
            creators = (same_artist(artist, main_artist) or (main_artist == 'various'))
        else:
            creators = (same_artist(artist, main_artist))

        consider_albums = (not albums_only) or ('album' in media_type)
        if ((media_format in media_type) and ('compilation' not in media_type)) and consider_albums:
            formats_filter = True
        elif (media_format == 'compilation') and (media_format in media_type):
            formats_filter = True
        else:
            formats_filter = False

        if creators:
            if (year < year_min) and formats_filter:
                if check_title(title, id, master, client) == False:
                    continue
                year_min = year
                pointer = i
            else:
                continue
    return pointer


def search_artist(artist, client):
    artist = correct_name(artist)
    search_url = base_url + '+'.join(artist.split()) + '&type=artist'
    resp, content = site_request(search_url, user_agent, client)
    return resp, content


def get_release(id, master, client):
    if master:
        search_url = top_url + 'masters/' + str(id)
    else:
        search_url = top_url + 'releases/' + str(id)
    resp, content = site_request(search_url, user_agent, client)
    return resp, content


def check_title(title, id, master, client):
    resp, content = get_release(id, master, client)
    if content == None:
        return False
    release = json.loads(content.decode('utf-8'))
    for song in release['tracklist']:  # простое совпадение названий песен
        cur_song = correct_name(song['title'])
        if cur_song == title:
            return True
        if smart_compare(cur_song, title):
            return True
        if fuzzy_compare.fuzzy_compare(cur_song, title) > lower_limit:
            return True
    return False


def smart_compare(song, title):
    song_length = len(song)
    title_length = len(title)
    if abs(title_length - song_length) > allowed_delta:
        return False
    occur = 0
    for i in range(len(title), 0, -1):
        cur_length = len(title[:i])
        if (cur_length < allowed_delta) or abs(cur_length - song_length) > allowed_delta:
            return False
        got_it = song.find(title[:i])
        if got_it == -1:
            continue
        else:
            occur = got_it
            return True
    return False

def find_true_artist(artist_web, client):
    resp, content = search_artist(artist_web, client)
    if content == None:
        return False, artist_web
    release = json.loads(content.decode('utf-8'))
    if release['pagination']['items'] == 0:
        return False, artist_web

    rating = 1
    champion = artist_web
    mirror_artist = no_comma(artist_web)
    for who_is_this in release['results']:
        who_is_web = correct_artist_name(who_is_this['title'])
        if artist_web == who_is_web:
            rating = MaxRating
            champion = who_is_web
            continue
        if mirror_artist == who_is_web:
            champion = who_is_web
            rating = MaxRating
            continue
        f_rating = fuzzy_compare.fuzzy_compare(who_is_web, artist_web)
        if f_rating > lower_limit:
            if f_rating > rating:
                rating = f_rating
                champion = who_is_web
                continue
    return True, correct_artist_name(champion)


def get_album_cover(song_title, client):
    if '-' not in song_title:
        print(f"No info for {song_title}")
        return False

    title_list = song_title.split(' - ')
    artist = title_list[0]
    title = ' - '.join(title_list[1:])
    artist_web = correct_artist_name(artist)
    title_web = correct_name(title)
    if artist_web == '' or title_web == '':
        print(f"No info for {artist + ' - ' + title}")
        return False

    # --------------- есть ли такой артист -----------------
    found, artist_web = find_true_artist(artist_web, client)
    if not found:
        print(f'artist {artist} not found')
        return False
  # ---------------------------------------------------

    pointer = -1
    found = False
    for master in (True, False):
        if pointer != -1 or found: break
        resp, content = do_the_search(artist_web, title_web, master, client)
        if content == None:
            print(f"No info for {song_title}")
            return False
        release = json.loads(content.decode('utf-8'))
        if release['pagination']['items'] == 0:
            continue
        else:
            for albums_only in (True, False):
                if pointer != -1 or found: break
                for media_format in proper_formats:
                    pointer = get_proper_release(artist_web, title_web, release, media_format, albums_only, client)
                    if pointer == -1:  # ничего не нашли
                        continue
                    else:
                        found = True
                        break

    # -------------------  release check ---------------------

    if pointer == -1:
        return False
    cover_image = release['results'][pointer]['cover_image']
    try:
        release_info['album_name'] = release['results'][pointer]['title']
    except:
        release_info['album_name'] = ''
    try:
        release_info['year'] = release['results'][pointer]['year']
    except:
        release_info['year'] = ''

    try:
        resp, content = client.request(cover_image, headers={'User-Agent': user_agent})
    except Exception as e:
        print(f'Unable to download image {cover_image}, error {e}')
        return False
    img = Image.open(io.BytesIO(content))
    try:
        img.save(cover_file)
    except OSError:
        print(f'Cant write file {cover_file} for {song_title}')
    return True


def get_release_info():
    return release_info['album_name'], release_info['year']
