#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import glob
from math import ceil
from multiprocessing import Process
import os
import re
import requests
import sys
import time
from urllib.parse import urlparse


DEFAULT_FILENAME = 'file'
DEFAULT_PROCESS_NUM = 10


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('URI', help='URI want to download resource.')
    parser.add_argument('-n', type=int, help='Number of process will be forked.')
    parser.add_argument('-o', help='Output file name.')

    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args()
    uri = args.URI
    if args.n:
        process_num = args.n
    else:
        process_num = DEFAULT_PROCESS_NUM
    print('Number of process: {}'.format(process_num))

    res = requests.head(uri)

    # get information from header
    content_length = int(res.headers.get('Content-Length'))
    content_disposition = res.headers.get('Content-Disposition')
    accept_ranges = res.headers.get('Accept-Ranges')
    if process_num > content_length:
        chunk_size = 1
    else:
        chunk_size = ceil(content_length / process_num)

    if args.o:
        filename = args.o
    # get filename from Content-Disposition header
    elif content_disposition:
        regex = re.compile(r'filename="(.+)"')
        match_obj = regex.search(content_disposition)
        if match_obj:
            filename = match_obj.group(1)
        else:
            filename = DEFAULT_FILENAME + str(time.time()).replace('.', '')
    else:
        component = urlparse(uri)
        if component.path:
            filename = component.path.split('/')[-1]
        else:
            filename = DEFAULT_FILENAME + str(time.time()).replace('.', '')

    start = 0
    end = start + chunk_size
    if accept_ranges and accept_ranges != 'none':
        processes = []
        for i in range(process_num):
            p = Process(target=download, args=(uri, i, start, end))
            processes.append(p)
            p.start()

            start = end + 1
            end = start + chunk_size
            if end >= content_length:
                end = content_length
        # wait all process finish
        while True:
            if not any([p.is_alive() for p in processes]):
                break
            time.sleep(0.1)
    else:
        print('{} cannot range request.'.format(uri), file=sys.stderr)
        sys.exit(0)

    combine(filename)


def download(uri, index, start, end):
    headers = {'Range': 'bytes={}-{}'.format(start, end)}
    res = requests.get(uri, headers=headers)

    if res.status_code == 206:
        # Success
        with open('data.{}'.format(index), 'wb') as f:
            f.write(res.content)
    else:
        # Failure
        # TODO: resend request
        print('failure', file=sys.stderr)


def combine(filename):
    files = glob.glob('data.*')

    with open(filename, 'wb') as wf:
        for file in files:
            with open(file, 'rb') as rf:
                wf.write(rf.read())
            os.remove(file)


if __name__ == '__main__':
    main()
