#!/usr/bin/env python3
# pylint: disable=consider-using-f-string
"""Download Shutterfly address book, format using Pandas, save as csv file."""
import argparse
import collections
import configparser
import sys
import time

import pandas
import requests

# Shutterfly website framework
SFLY_SITE = {
    'uid': {
        'url':
        'https://api2.shutterfly.com/usersvc/api/users/v1/uid/URLUSERID',
        'apikey': 'xbqGCOubdkYYypwETOHerYcReO5MUYdm'
    },
    'contacts': {
        'url': 'https://api2.shutterfly.com/v1/addressbook/URLUSERID/contacts',
        'apikey': 'atZ2n8KI5db0zd4rtJ5ieRY99VG5uQV4'
    }
}
# Future: Authorization via AWS Cognito, indirect through Shutterfly,
# with ReCAPTCHA (opaque and challenging).
SFLY_AUTH_URL = 'https://api2.shutterfly.com/usersvc/api/v1/authenticate'
SFLY_CLIENTID = 't8oiif52mece6bleeas2pof0n'
SFLY_USERPOOLID = 'us-east-1_TmHzoQ69j'


def load_config(config_file):
    """Load Shutterfly credentials and output sorting from file."""
    config = configparser.ConfigParser()
    config.read(config_file)
    if not config.has_option('URL', 'UserID') or not config.has_option(
            'Headers', 'Bearer'):
        print("Request failed, error loading configuration file.")
        sys.exit(404)
    url_userid = config['URL']['UserID']
    headers_bearer = config['Headers']['Bearer']
    if len(url_userid) != 12:
        print("UserID unexpected length.")
    if len(headers_bearer) < 1200:
        print("Bearer token unexpected length.")
    if 'Bearer' not in headers_bearer:
        headers_bearer = 'Bearer ' + headers_bearer
    try:
        columns_sorting_order = config['Columns']['sorting_order'].split('\n')
        columns_sorting_order = [line for line in columns_sorting_order if line.strip() != '']
    except KeyError:
        columns_sorting_order = None
    return url_userid, headers_bearer, columns_sorting_order


def get_sfly(query_type, url_user_id, bearer_token):
    """Download from Shutterfly website uid or contacts data."""
    if query_type == 'contacts':
        params = {
            'pageSize': '-1',
            'sort': 'lastName',
            'startIndex': '0',
            'ts': str(int(time.time()))
        }
    else:
        params = {}
    headers = {
        'content-type': 'application/json',
        'authorization': bearer_token,
        'SFLY-apikey': SFLY_SITE[query_type]['apikey']
    }
    response = requests.get(SFLY_SITE[query_type]['url'].replace(
        'URLUSERID', url_user_id),
                            timeout=5,
                            params=params,
                            headers=headers)
    if response.status_code == 401:
        print("Request failed, update Bearer token.")
        sys.exit(401)
    if response.status_code == 500:
        print("Request failed, error in UserID.")
        sys.exit(500)
    return response.json()


def match_pairs(xin, yin):
    """Match pairs from two lists."""
    xsorted = collections.deque(sorted(xin))
    ysorted = collections.deque(sorted(yin))
    while xsorted and ysorted:
        if xsorted[0] == ysorted[0]:
            yield xsorted.popleft(), ysorted.popleft()
        elif xsorted[0] < ysorted[0]:
            yield xsorted.popleft(), 'N/A'
        else:  # xsorted[0] > ysorted[0]
            yield 'N/A', ysorted.popleft()
    for xremain in xsorted:
        yield xremain, 'N/A'
    for yremain in ysorted:
        yield 'N/A', yremain


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        prog=__file__.rsplit('/', maxsplit=1)[-1],
        description='Download Shutterfly address book and save as .csv file.',
        epilog=
        'Instructions for Shutterfly credentials in example configuration .ini file.')
    parser.add_argument('-c',
                        '--config',
                        metavar='CONFIG_FILE',
                        default=__file__.replace('.py', '.ini'),
                        help='default: %(default)s')
    parser.add_argument('-o',
                        '--output',
                        metavar='OUTPUT_FILE',
                        default=__file__.replace(
                            parser.prog, 'shutterfly_address_book.csv'),
                        help='default: %(default)s')
    args = parser.parse_args()
    print("Requesting Shutterfly access.")
    userid, bearer, output_column_sorting_order = load_config(args.config)
    username = get_sfly('uid', userid, bearer)['fullName']
    print("Requesting address book for {}.".format(username))
    address_book = get_sfly('contacts', userid, bearer)['items']
    full_address = pandas.json_normalize(address_book, record_path='addresses')
    everything_else = pandas.json_normalize(address_book).drop(['addresses'],
                                                               axis='columns')
    df = pandas.concat([full_address, everything_else], axis='columns')
    df.replace([''], [None], inplace=True)
    df.dropna(how='all', axis='columns', inplace=True)
    rows, columns = df.shape
    if rows == len(address_book):
        print("Entries successfully imported:", rows)
    else:
        print("Entries don't match address book:", rows, len(address_book))
    if output_column_sorting_order:
        if columns != len(output_column_sorting_order):
            print("Non-empty columns ({}) don't match sorting index ({}):".format(
                columns, len(output_column_sorting_order)))
            width = max(len(x) for x in df.columns)
            print("{0:>{width}} {1}".format("Shutter dfly column",
                                            "Sorting index",
                                            width=width))
            for pair in match_pairs(df.columns, output_column_sorting_order):
                print("{0:>{width}} {1}".format(*pair, width=width))
        df = df.reindex(output_column_sorting_order, axis='columns')
        SORTED = " (sorted per config file)"
    else:
        SORTED = ""
    print("Columns with row count{}:".format(SORTED))
    print(df.count())
    df.sort_values(by=['lastName', 'firstName'], inplace=True)
    df.to_csv(args.output, header=True, index=False)
    print("Saved address book to {}".format(args.output))
