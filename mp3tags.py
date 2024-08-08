from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, APIC, PictureType
from PIL import Image
import discogs

mp3_tag = {}
default_picture = 'notez3.jpg'


def fill_mp3_tags(number, song_title, fname, cli_params, client):
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
        audio = ID3(fname)
        audio['TPE1'] = TPE1(text=artist)
        audio['TIT2'] = TIT2(text=title)
        audio['TALB'] = TALB(text=album_name)
        audio['TDRC'] = TDRC(text=year)
        picture = discogs.cover_file if found else default_picture
        with open(picture, 'rb') as pic:
            audio['APIC'] = APIC(encoding=3, mime='image/jpeg', type=PictureType.COVER_FRONT, desc=u'Cover', data=pic.read())
        audio.save()
        print(f'{number}: {artist} - {title} [{album_name}] (p){year}')
    return found
