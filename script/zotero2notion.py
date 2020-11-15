#!/usr/bin/env python

import click
import pandas as pd
import urllib
import re


def file_name(x):
    return re.sub(r'.pdf$', '', x['File Attachments'].split('/')[-1])


def pdf_url(x):
    fname = x['File Attachments'].split('/')[-1]
    url = "http://jinlong.local:8668/zotero_papers/" + urllib.parse.quote(fname)
    return url


def journal_lower(x):
    try:
        journal = x['Publication Title'].lower()
    except:
        journal = "na"
    return journal


def add_day_to_date(date):
    if date.count("-") == 0:
        date += "-01-01"
    elif date.count("-") == 1:
        date += "-01"
    return date


@click.command()
@click.option("--zotero_export", '-z', help="zotero_export.csv")
@click.option("--impact_factor", '-i', help="impact_factor_2020.tsv")
@click.option("--fout", '-o', help="notion_import.csv")
def main(zotero_export, impact_factor, fout):
    """
    zotero2notion.py -z zotero_export.csv -i impact_factor_2020.tsv -o notion_import.csv
    """
    df = pd.read_csv(zotero_export)
    
    dfif = pd.read_csv(impact_factor, sep='\t')
    dfif.columns = ['journal', "Impact_factor"]
    dfif['journal'] = dfif.apply(lambda x:x['journal'].lower(), axis=1)
    
    
    df['PDF'] = df.apply(lambda x: pdf_url(x), axis=1)
    df['Name'] = df.apply(lambda x: file_name(x), axis=1)
    df['journal'] = df.apply(lambda x:journal_lower(x), axis=1)
    
    tbl = df.merge(dfif, on='journal', how='left')
    tbl['Impact_factor'] = tbl.apply(lambda x:round(x['Impact_factor'], 1), axis=1)
    tbl['Date_added'] = tbl.apply(lambda x:x['Date Added'].split(' ')[0], axis=1)
    tbl['Date_published'] = tbl.apply(lambda x:add_day_to_date(x['Date'].split(' ')[0]), axis=1)
    tbl.rename(columns={"Publication Title": "Journal"}, inplace=True)
    clms = ['Name', 'Impact_factor', 'Journal', 'PDF', 'Url', 'Date_published', 'Date_added', 'Title']
    tbl[clms].to_csv(fout, index=False)
    

if __name__ == '__main__':
    main()
