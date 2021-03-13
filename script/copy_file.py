#!/usr/bin/env python

import click
import os
import pandas as pd
import shutil


@click.command()
@click.option("--fin", '-i', help="input file name")
@click.option("--save_dir", '-s', help="output directory name")
def main(fin, save_dir):
    """
    Usage:
        copy_file.py -i flist.txt -s newdir

    """
    flist = pd.read_csv(fin, names=['fname'])

    paper_dir = "/Users/allen/Dropbox/zotero_papers/"
    papers = os.listdir(paper_dir)
    df = pd.DataFrame(papers, columns=['paper'])
    df['fname'] = df.apply(lambda x:'.'.join(x['paper'].split('.')[:-1]), axis=1)

    tbl = flist.merge(df, on='fname', how='left')

    try:
        os.mkdir(save_dir)
    except:
        pass

    fpath = [os.path.join(paper_dir, x) for x in tbl.paper]
    for fname in fpath:
        shutil.copy(fname, save_dir)


if __name__ == '__main__':
    main()
