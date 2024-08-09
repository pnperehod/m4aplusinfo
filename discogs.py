import json
import io
import time
import fuzzy_compare

from PIL import Image
import oauth2 as oauth

base_url = 'https://api.discogs.com/database/search?q='
top_url = 'https://api.discogs.com/'
cover_file = 'cover.jpg'
release_url = 'https://api.discogs.com/releases/'
discogs_error = 'Error getting information from Discogs.com'
proper_formats = ['lp', 'ep', 'cd', 'cdr', 'file', 'vinyl']
unproper_formats = ['compilation', 'sampler', 'single', '7\"', '12\"', '45 rpm', 'vhs']
delimiters = [' and ', ',', ';', ' / ', ' f/']
user_agent = 'detektor_radio'
release_info = {'album_name': '', 'year': ''}
requests_counter = 0
allowed_delta = 6
artist_found = False
lower_limit = 52
MaxRating = 200


def connect_oauth(oauth_info):
    # create oauth Consumer and Client objects using
    consumer = oauth.Consumer(oauth_info['consumer_key'], oauth_info['consumer_secret'])
    token = oauth.Token(oauth_info['oauth_token'], oauth_info['oauth_token_secret'])
    client = oauth.Client(consumer, token)
    return client

def site_request(url, uagent, client):
    global requests_counter
    tries = 5
    while tries > 0:
        try:
            requests_counter = requests_counter + 1
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
        search_url = base_url + '+'.join(artist.split()) + '+' + '+'.join(title.split()) + '&type=master' + '&page=1&per_page=100'
    else:
        search_url = base_url + '+'.join(artist.split()) + '+' + '+'.join(title.split()) + '&type=all' + '&page=1&per_page=100'
    resp, content = site_request(search_url, user_agent, client)
    return resp, content


def no_comma(str):
    is_comma = str.find(',')
    if is_comma != -1:
        str = str[is_comma + 1:].strip() + ' ' + str[:is_comma].strip()
    return str


def no_brackets(str, brackets):              # brackets is a string of 2 symbols, like '()'
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
#     str = unidec.unidecode(str)
    str = str.lower()
    return str.strip()


def correct_artist_name(str):
    str = correct_name(str)
    if str.lower().find('the ') == 0:                # если The в начале имени
        str = str[3:]     # убирает начальное The в имени
#    str = no_comma(str)
    str = str[:-1] if (len(str) > 0) and ('*' == str[-1]) else str
    return str.strip()


def is_proper_format(media_type):
    for f in proper_formats:
        if f in media_type:
            return True
    return False

def same_artist(artist, release_artist):
    if artist == release_artist:
        return MaxRating
    if artist in release_artist:
        return lower_limit + (len(artist)/len(release_artist))*100
    rating = fuzzy_compare.fuzzy_compare(artist, release_artist)
    if rating > lower_limit:
        return rating
    return 0

def same_media(type_f, media_type):
    for format in media_type:
        if type_f in format.lower():
            return True
    return False


def proper_media_format(media_type):
    for format in media_type:
        format = format.lower()
        if format in unproper_formats:
            return False
    for format in media_type:
        format = format.lower()
        if format in proper_formats:
            return True
    return False

def get_proper_release(artist, title, release, client):
    items = int(release['pagination']['items'])
    per_page = int(release['pagination']['per_page'])
    variants = items if items < per_page else per_page
    year_min = 9999
    max_rating = 0
    max_artist_rating = 1
    champion = ''
    pointer = -1
    for i in range(variants):
        try:
            year = int(release['results'][i]['year'])
            media_type = release['results'][i]['format']
            release_artist = release['results'][i]['title']
        except:
            continue

        if not proper_media_format(media_type):
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

        main_artist = release_artist.split(' - ')[0]
        main_artist = correct_artist_name(main_artist)
        artist = correct_artist_name(artist)

        creators = same_artist(artist, main_artist)


        if (creators >= max_artist_rating):
            checked, rating = check_title(title, id, master, client)
            if (not checked) or (rating < max_rating):
                continue
            champion = main_artist
            max_artist_rating = creators
            max_rating = rating
            if year < year_min:
                year_min = year
                pointer = i
            if rating  == MaxRating:
                break
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


def check_title(title, idr, master, client):
    resp, content = get_release(idr, master, client)
    if content == None:
        return False, 0
    release = json.loads(content.decode('utf-8'))
    title = title.lower()
    for song in release['tracklist']:      # простое совпадение названий песен
        cur_song = correct_name(song['title'])
        if cur_song == title:
            return True, MaxRating
        if smart_compare(cur_song, title):      # совпадение части названия
            return True, MaxRating / 2
        rating = fuzzy_compare.fuzzy_compare(cur_song, title)
        if rating > lower_limit:
            return True, rating
    return False, 0

def smart_compare(song, title): # version 2
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
        print(discogs_error)
        return False, artist_web
    release = json.loads(content.decode('utf-8'))
    if release['pagination']['items'] == 0:
#        return False, artist_web
        for delim in delimiters:
            if delim in artist_web:  # hack to cover tracks made by several
                sub_artist = artist_web.split(delim)[0].strip()  # artists in collaboration
                resp, content = search_artist(sub_artist, client)  # Such albums falls in discographies
                if content == None:  # of both artists, we take only the first
                    print(discogs_error)
                    return False
                else:
                    release = json.loads(content.decode('utf-8'))
                    artist_web = sub_artist
                    break
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

def select_album(artist, title, client):
    pointer = -1
    found = False
    for master in (True, False):
        if pointer != -1 or found:
            break
        resp, content = do_the_search(artist, title, master, client)
        if content ==None:
            print(f"No info for {artist} - {title}")
            return False, pointer, []
        release = json.loads(content.decode('utf-8'))
        if release['pagination']['items'] == 0:
            continue
        else:
            pointer = get_proper_release(artist, title, release, client)
            if pointer == -1:  # ничего не нашли
                continue
            else:
                found = True
                break
    return found, pointer, release

# ---------------------------------------------------
def get_album_cover(song_title, client):
    global requests_counter, release_info

    requests_counter = 0

    if '-' not in song_title:
        print(f"No info for {song_title}")
        return False

    artist = song_title.split(' - ')[0]
    title_list = song_title.split(' - ')
    title = ' - '.join(title_list[1:])
    artist_web = correct_artist_name(artist)
    title_web = correct_name(title)
    if artist_web == '' or title_web == '':
        print(f"No info for {artist + ' - ' + title}")
        return False

#--------------- есть ли такой артист -----------------
    found, artist_web = find_true_artist(artist_web, client)
    if not found:
        print(f'artist {artist} not found')
        return False
#--------------------------------------------------------

# -------------------  release check ---------------------
    found, pointer, release = select_album(artist_web, title_web, client)
    if (not found) or (pointer == -1):
        print(f"No info for {song_title}")
        return False

    cover_image = release['results'][pointer]['cover_image']
    try:
        aaa = release['results'][pointer]['title']
        release_info['album_name'] = aaa
    except:
        release_info['album_name'] = ''
    try:
        yyy = release['results'][pointer]['year']
        release_info['year'] = yyy
    except:
        release_info['year'] = ''

#    with open(artist_web + ' - ' + title_web + '_a' + '.json', 'w') as js:
#        json.dump(release, js)

    try:
        resp, content = client.request(cover_image, headers={'User-Agent': user_agent})
    except Exception as e:
        print(f'Unable to download image {cover_image}, error {e}')
        return False

#    print(f'requests_counter={requests_counter}  artist:{artist} title:{title} album:{album} year: {year}')
    img = Image.open(io.BytesIO(content))
 #   img.show()
    try:
        img.save(cover_file)
    except: # OSError:
        print(f"Can't write cover file")
    return True

def get_release_info():
    return release_info['album_name'], release_info['year']