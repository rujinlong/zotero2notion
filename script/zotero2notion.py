#!/usr/bin/env python

import click
import pandas as pd
import urllib
import re
import notion
from notion.client import NotionClient
import datetime


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


def add_row(cv, x):
    row = cv.collection.add_row()
    row.name = x['Name']
    row.impact_factor = x['Impact_factor']
    row.journal = x['Journal']
    row.pdf = x['PDF']
    row.url = x['Url']
    Tadded = [int(i) for i in x['Date_added'].split('-')]
    Tpublished = [int(i) for i in x['Date_published'].split('-')]
    row.date_published = notion.collection.NotionDate(datetime.date(Tpublished[0], Tpublished[1], Tpublished[2]))
    row.date_added = notion.collection.NotionDate(datetime.date(Tadded[0], Tadded[1], Tadded[2]))
    row.title = x['Title']


@click.command()
@click.option("--zotero_export", '-z', help="zotero_export.csv")
@click.option("--impact_factor", '-i', help="impact_factor_2020.tsv")
@click.option("--token", '-t', help="token_v2")
@click.option("--table_url", '-u', help="table url")
@click.option('--checkdup/--no-checkdup', default=False, help="Check duplication")
def main(zotero_export, impact_factor, token, table_url, checkdup):
    """
    zotero2notion.py -z zotero_export.csv -i impact_factor_2020.tsv -t <token_v2> -u <table_url>
    """

    ## Link paper to impact factor
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
    tbl.Impact_factor.fillna(0, inplace=True)
    tbl.fillna('', inplace=True)
    # clms = ['Name', 'Impact_factor', 'Journal', 'PDF', 'Url', 'Date_published', 'Date_added', 'Title']
    # tbl[clms].to_csv(fout, index=False)

    ## Add to notion
    recs = tbl.to_dict(orient="records")

    # Get notion table
    client = NotionClient(token_v2=token)
    cv = client.get_collection_view(table_url)

    if checkdup:
        # List existed records
        recs_exist = [x.name for x in cv.collection.get_rows()]
        # Delete records which already exists in table
        recs_add = [x for x in recs if x['Name'] not in recs_exist]
    else:
        recs_add = recs

    # Add new rows
    for rec in recs_add:
        add_row(cv, rec)
    

if __name__ == '__main__':
    main()
