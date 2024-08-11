from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, APIC, PictureType
from mutagen.mp4 import MP4, MP4Cover
from PIL import Image
import discogs


default_picture = 'notez3.jpg'
tags_info = {}


def fill_tags(type, number, song_title, fname, cli_params, client):
    tags_info['artist'] = song_title.split(' - ')[0]
    title_list = song_title.split(' - ')
    tags_info['title'] = ' - '.join(title_list[1:])
    found = discogs.get_album_cover(song_title, client)
    if found:
        album_title, tags_info['year'] = discogs.get_release_info()
        tags_info['album_name'] = ' '.join(album_title.split(' - ')[1:])
    else:
        tags_info['album_name'] = ''
        tags_info['year'] = ''

    if cli_params['test_mode']:
        if cli_params['show_bad_only']:
            if not found:
                print(f"{number}: {tags_info['artist']} - {tags_info['title']}")
        else:
            print(f"{number}: {tags_info['artist']} - {tags_info['title']}  [{tags_info['album_name']} (p){tags_info['year']}]")
    else:
        if type == 'mp3':
            mp3_tags(tags_info, fname, found)
        if type == 'm4a':
            m4a_tags(tags_info, fname, found)
        print(f"{number}: {tags_info['artist']} - {tags_info['title']}  [{tags_info['album_name']} (p){tags_info['year']}]")
    return found

def mp3_tags(tags_info, fname, found):
    audio = ID3(fname)
    audio['TPE1'] = TPE1(text=tags_info['artist'])
    audio['TIT2'] = TIT2(text=tags_info['title'])
    audio['TALB'] = TALB(text=tags_info['album_name'])
    audio['TDRC'] = TDRC(text=tags_info['year'])
    picture = discogs.cover_file if found else default_picture
    with open(picture, 'rb') as pic:
        audio['APIC'] = APIC(encoding=3, mime='image/jpeg', type=PictureType.COVER_FRONT, desc=u'Cover',
                             data=pic.read())
    audio.save()

def m4a_tags(tags_info, fname, found):
    audio = MP4(fname)
    audio["\xa9nam"] = tags_info['title']
    audio["\xa9ART"] = tags_info['artist']
    audio["\xa9alb"] = tags_info['album_name']
    audio["\xa9day"] = tags_info['year']
    picture = discogs.cover_file if found else default_picture
    with open(picture, 'rb') as pic:
        audio["covr"] = [MP4Cover(pic.read(), imageformat=MP4Cover.FORMAT_JPEG)]
    audio.save()
