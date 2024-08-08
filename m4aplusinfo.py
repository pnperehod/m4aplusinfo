import os, sys
import configparser
import discogs
import mp4tags
import mp3tags
from fuzzy_compare import logging, fuzzy_compare
import time
import argparse

oauth2_info = {'consumer_key': '',
               'consumer_secret': '',
               'oauth_token': '',
               'oauth_token_secret': ''}
debug_level = 0
TIMEOUT = 5         # seconds
description = """
Utility to update downloaded music file with
additional info and cover images
"""
cli_params = {'source_dir': '',
              'test_mode': False,
              'show_bad_only': False}

def config_read():
    global debug_level
    config = configparser.ConfigParser()
    config.read('config.ini')
    try:
        oauth2_info['consumer_key'] = config['authentication']['consumer_key']
        oauth2_info['consumer_secret'] = config['authentication']['consumer_secret']
        oauth2_info['oauth_token'] = config['authentication']['oauth_token']
        oauth2_info['oauth_token_secret'] = config['authentication']['oauth_token_secret']
        debug_level = int(config['parameters']['debug_level'])
    except:
        sys.exit(f"Can't read config file or syntax error")

def cli_args():
    parser = argparse.ArgumentParser(prog='arguments', description=description,
                                     epilog='(c) nnn 2024')
    parser.add_argument('-t', action='store_true', help='Test mode')
    parser.add_argument('-b', action='store_true', help='Show not found only')
#    parser.add_argument('-n', nargs='+', type=int, help='process only this numbers')
    parser.add_argument('source_dir', type=str, help='directory with music files')

    args = parser.parse_args()
    return args

def main():
    config_read()
    args = cli_args()
    cli_params['source_dir'] = args.source_dir
    cli_params['test_mode'] = True if args.t else False
    cli_params['show_bad_only'] = True if args.b else False
    client = discogs.connect_oauth(oauth2_info)

    logging(debug_level)
    bads = goods = 0

    for dirpath, dirnames, fnames in os.walk(cli_params['source_dir'], True):
        for fname in fnames:
            name, extension = os.path.splitext(fname)
            if '_' not in name:
                continue
            number = name.split('_')[0]  # file names like 00NN_artistname - songname.ext
            song_title = name.split('_')[1]
            full_name = os.path.join(dirpath, fname)
            if extension == '.m4a':
                found = mp4tags.fill_mp4_tags(number, song_title, full_name, cli_params, client)
            elif extension == '.mp3':
                found = mp3tags.fill_mp3_tags(number, song_title, full_name, cli_params, client)
            else:
                continue
            goods = goods + 1 if found else goods
            bads = bads + 1 if not found else bads
            time.sleep(TIMEOUT)

    print(f'Processed: {goods+bads}, Found: {goods}, Not found: {bads}')




if __name__ == '__main__':
    main()
