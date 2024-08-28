from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TCON, TPUB, COMM, TRCK, APIC, PictureType
from mutagen.mp4 import MP4, MP4Cover
from PIL import Image
import io

import discogs

tags_info = {}
user_agent = 'detektor_radio'
cover_file = 'cover.jpg'
default_picture = 'notez3.jpg'


def fill_tags(type, number, song_title, fname, cli_params, client):
    found = discogs.get_album_cover(song_title, client)
    release_info = discogs.get_release_info()

    if cli_params['test_mode']:
        if cli_params['show_bad_only']:
            if not found:
                print(f"{number}: {release_info['artist']} - {release_info['song']}")
        else:
            print(f"{number}: {release_info['artist']} - {release_info['song']}  [{release_info['title']} (p){release_info['year']}]")
    else:
        if type == 'mp3':
            mp3_tags(number, release_info, fname, found, client)
        if type == 'm4a':
            m4a_tags(number, release_info, fname, found, client)
        print(f"{number}: {release_info['artist']} - {release_info['song']}  [{release_info['title']} (p){release_info['year']}]")
    return found

def mp3_tags(number, release_info, fname, found, client):
    audio = ID3(fname)
    audio.delall('APIC')
    audio['TPE1'] = TPE1(text=release_info['artist'])
    audio['TIT2'] = TIT2(text=release_info['song'])
    audio['TALB'] = TALB(text=release_info['title'])
    audio['TDRC'] = TDRC(text=release_info['year'])
    audio['TCON'] = TCON(text=release_info['genre'])
    audio['TPUB'] = TPUB(text=release_info['label'])
    audio['COMM'] = COMM(text=release_info['url'])
    audio['TRCK'] = TRCK(text=number)
    picture = get_picture(release_info, client) if found else default_picture
    with open(picture, 'rb') as pic:
        audio['APIC'] = APIC(encoding=3, mime='image/jpeg', type=PictureType.COVER_FRONT, desc=u'Cover',
                             data=pic.read())
    audio.save(fname)

def m4a_tags(number, release_info, fname, found, client):
    audio = MP4(fname)
    audio.delete()
    audio["\xa9nam"] = release_info['song']
    audio["\xa9ART"] = release_info['artist']
    audio["\xa9alb"] = release_info['title']
    audio["\xa9day"] = release_info['year']
    audio["\xa9gen"] = release_info['genre']
    audio["cprt"] = release_info['label']
    audio["\xa9cmt"] = release_info['url']
    audio["trkn"] = [(int(number), 0)]
    picture = get_picture(release_info, client) if found else default_picture
    with open(picture, 'rb') as pic:
        audio["covr"] = [MP4Cover(pic.read(), imageformat=MP4Cover.FORMAT_JPEG)]
    audio.save(fname)

def get_picture(release_info, client):
    cover_image = release_info['cover_image']
    artist = release_info['artist']
    song = release_info['song']
    try:
        resp, content = client.request(cover_image, headers={'User-Agent': user_agent})
    except Exception as e:
        if discogs.debug_error:
            print(f"Unable to download image {cover_image}, error {e}")
            return
    img = Image.open(io.BytesIO(content))
    if discogs.debug_img_show:
        img.show()
    if discogs.debug_img_save:
        try:
            img.save(artist + ' - ' + song + '.jpg')
        except:  # OSError:
            if discogs.debug_error:
                print(f"Can't write {artist + ' - ' + song + '.jpg'} file")
    try:
        img.save(cover_file)
    except:  # OSError:
        print(f"Can't write cover file")
    return cover_file

