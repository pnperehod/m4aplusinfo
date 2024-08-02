from mutagen.mp4 import MP4, MP4Cover
from PIL import Image
import discogs

mp4_tag = {}
default_picture = 'notez3.jpg'


def fill_mp4_tags(number, song_title, fname, cli_params, client):
    artist = song_title.split(' - ')[0]
    title_list = song_title.split(' - ')
    title = ' - '.join(title_list[1:])
    found = discogs.get_album_cover(song_title, client)
    if found:
        album_name, year = discogs.get_release_info()
    else:
        album_name = ''
        year = ''

    if cli_params['test_mode']:
        if cli_params['show_bad_only']:
            if not found:
                print(f'{number}: {artist} - {title}')
        else:
            print(f'{number}: {artist} - {title}  [{album_name} (p){year}]')
    else:
        audio = MP4(fname)
        audio["\xa9nam"] = title
        audio["\xa9ART"] = artist
        audio["\xa9alb"] = album_name
        audio["\xa9day"] = year
        picture = discogs.cover_file if found else default_picture
        with open(picture, 'rb') as pic:
            audio["covr"] = [MP4Cover(pic.read(), imageformat=MP4Cover.FORMAT_JPEG)]
        audio.save()
        print(f'{number}: {artist} - {title} [{album_name}] (p){year}')
    return found
