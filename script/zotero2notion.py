#!/usr/bin/env python

import os
import click
import pandas as pd
import urllib
import re
import notion
from notion.client import NotionClient
import os
from dateutil import parser
from pyzotero import zotero
import pytz
from tzlocal import get_localzone
import configparser


def file_name(x):
    return re.sub(r'.pdf$', '', x['File Attachments'].split('/')[-1])


def pdf_url(x, pdf_local_url):
    fname = x['File Attachments'].split('/')[-1]
    fname_split_by_dot = fname.split('.')
    fname_prefix = '.'.join(fname_split_by_dot[:-1])
    fname_suffix = fname_split_by_dot[-1][:3]
    fname_corrected = '{}.{}'.format(fname_prefix, fname_suffix)
    url = pdf_local_url + urllib.parse.quote(fname_corrected)
    return url


def journal_lower(x):
    # Sometimes zotero add an extra "the" at the begining of the journal name. It should be removed
    journal = re.sub(r'^the ', '', x['Publication Title'])
    try:
        journal = journal.lower()
    except:
        journal = "na"
    return journal


def add_day_to_date(date):
    if date.count("-") == 0:
        date += "-01-01"
    elif date.count("-") == 1:
        date += "-01"
    return date


def combine_authors(creators):
    authors = []
    if len(creators) > 0:
        for creator in creators:
            lastName = creator.get('lastName')
            firstName = creator.get('firstName')
            if lastName and firstName:
                author = lastName.strip() + ', ' + firstName.strip()
                authors.append(author)
        Author = '; '.join(authors)
        return Author


def reformat_name(name):
    new_name = [x.strip() for x in name.split(',')]
    new_name.reverse()
    return " ".join(new_name)


def reformat_names(names):
    # sometimes names is empty
    if len(str(names)) > 5:
        names_list = [name.replace('.', ' ').strip() for name in names.split(';')]
        names_list_new = [reformat_name(name) for name in names_list]
        return ";".join(names_list_new)
    else:
        return ""


def add_row(cv, x, pdf_local_url, pdf_remote_url):
    row = cv.collection.add_row()
    row.name = x['Name']
    row.impact_factor = x['Impact_factor']
    row.journal = x['Journal']
    row.local_file = x['Local_file']
    row.pdf = row.local_file.replace(pdf_local_url, pdf_remote_url)
    row.url = x['Url']
    row.date_published = notion.collection.NotionDate(x['Date_published'])
    row.date_added = notion.collection.NotionDate(x['Date_added'])
    row.title = x['Title']
    row.authors = x['Authors']
    row.cas = x['Cas']
    row.subject = x['Subject']


def add_supp_dir(pdf_local_folder, supplementary_file_path):
    """
    Create folder to store supplementary materials
    """
    pdf_local_folder = os.path.abspath(os.path.expanduser(pdf_local_folder))
    supplementary_file_path = os.path.abspath(os.path.expanduser(supplementary_file_path))
    os.chdir(supplementary_file_path)
    pdfs = os.listdir(pdf_local_folder)
    fnames = [x for x in pdfs if '-' in x]
    for x in fnames:
        os.makedirs(x[:-4], exist_ok=True)


def merge_IF_CAS(impact_factor, cas):
    dfcas = pd.read_csv(cas, sep='\t')
    dfcas = dfcas[['journal', 'Cas', 'Subject']].copy()
    dfcas['journal'] = dfcas.apply(lambda x:str(x['journal']).lower(), axis=1)
    dfcas['Subject'] = dfcas.apply(lambda x:str(x['Subject']).capitalize(), axis=1)

    dfif = pd.read_csv(impact_factor, sep='\t')
    dfif.columns = ['journal', "Impact_factor"]
    dfif['journal'] = dfif.apply(lambda x:x['journal'].lower(), axis=1)
    
    df = dfif.merge(dfcas, on="journal", how="outer").drop_duplicates()
    df.Impact_factor.fillna(0, inplace=True)
    df.Cas.fillna("NA", inplace=True)
    df.Subject.fillna("NA", inplace=True)
    return df.groupby('journal', as_index=False).agg({'Subject' : '; '.join, 'Impact_factor': 'first', 'Cas' : 'first'})


def select_attachment_items(items):
    items_with_attachment = []
    for item in items:
        data = item.get('data')
        attachment = data.get('contentType')
        if attachment == "application/pdf":
            items_with_attachment.append(data)
    return items_with_attachment


def add_parent_info(zot, child):
    parent = zot.item(child['parentItem'])['data']
    
    child['Author'] = combine_authors(parent.get('creators'))
    child['Date_published'] = parser.parse(parent.get('date'))
    child['Publication Title'] = parent.get('publicationTitle')
    child['Url'] = parent.get('url')
    child['Title'] = parent.get('title')
    child['File Attachments'] = child.get('filename')
    child['Date_added'] = parser.parse(child.get('dateAdded')).astimezone()

    keys = ['Author', 'Date_published', 'Publication Title', 'File Attachments', 'Date_added', 'Url', 'Title']
    return {k:child[k] for k in keys}


def fetch_zotero_records(library_id, api_key, topn):
    zot = zotero.Zotero(library_id, "user", api_key)
    zot.add_parameters(sort="dateAdded", direction="desc", limit=topn*2)
    items = zot.items()
    children = select_attachment_items(items)
    
    recs = []
    for child in children:
        recs.append(add_parent_info(zot, child))
    
    if len(recs) == 1:
        df = pd.DataFrame.from_records(recs, index=[0])
    elif len(recs) > 1:
        df = pd.DataFrame.from_records(recs)
    return df


def filter_new_zotero_recs(time_notion, title_notion, rec_zotero):
    time_zotero = rec_zotero["Date_added"]
    title_zotero = file_name(rec_zotero)
    
    if title_zotero == title_notion:
        update = False
    # If zotero records are newser than notion latest records
    elif time_zotero > time_notion:
        update = True
    else:
        update = False
    return update


@click.command()
@click.option("--config", '-c', default="~/github/zotero2notion/config.ini", help="config.ini")
@click.option("--zotero_topn", '-n', type=int, help="Fetch n most recent records in zotero to compare with the most recent records in Notion")
def main(config, zotero_topn):
    """
    Usage:
    
    zotero2notion.py -c config.ini -n <zotero_topn>
    """

    # Read config file
    config = os.path.expanduser(config)
    cfg = configparser.ConfigParser()
    cfg.read(config)
    impact_factor = cfg['Resources']['impact_factor']
    cas = cfg['Resources']['cas']
    notion_token = cfg['Notion']['notion_token']
    notion_table_url = cfg['Notion']['notion_table_url']
    zotero_library_id = cfg['Zotero']['zotero_library_id']
    zotero_api_key = cfg['Zotero']['zotero_api_key']
    pdf_local_folder = cfg['PDFs']['pdf_local_folder']
    pdf_local_url = cfg['PDFs']['pdf_local_url']
    pdf_remote_url = cfg['PDFs']['pdf_remote_url']
    supplementary_path = cfg['PDFs']['supplementary_path']

    properties = {'Subject': {'name': 'Subject', 'type': 'text'},
                'Authors': {'name': 'Authors', 'type': 'text'},
                'Url': {'name': 'Url', 'type': 'url'},
                'Local_file': {'name': 'Local_file', 'type': 'url'},
                'Title': {'name': 'Title', 'type': 'text'},
                'Date_added': {'name': 'Date_added', 'type': 'date', 'date_format': 'YYYY/MM/DD', 'time_format': 'H:mm'},
                'PDF': {'name': 'PDF', 'type': 'url'},
                'Impact_factor': {'name': 'Impact_factor', 'type': 'number', 'number_format': 'number'},
                'CAS': {'name': 'CAS', 'type': 'text'},
                'Modified': {'name': 'Modified', 'type': 'last_edited_time'},
                'comments': {'name': 'comments', 'type': 'text'},
                'Journal': {'name': 'Journal', 'type': 'text'},
                'Date_published': {'name': 'Date_published', 'type': 'date', 'date_format': 'YYYY/MM/DD', 'time_format': 'H:mm'}}
    
    # Fetch records in zotero library 
    df = fetch_zotero_records(zotero_library_id, zotero_api_key, zotero_topn)
    print("Updating {} files...".format(df.shape[0]))

    # Fetch records in notion table
    client = NotionClient(token_v2=notion_token)
    cv = client.get_collection_view(notion_table_url)
    notion_records = cv.collection.get_rows(sort=[{"direction": "descending", 
                                                   "property": "Date_added"}])

    # If the database is empty, create necessary columns
    if len(notion_records)==0:
        # Delete all columns in database
        # schema = {}
        # cv.collection.set(path=['schema'], value=schema)

        schema = cv.collection.get()['schema']
        columns_existed = [x['name'] for x in schema.values()]
        columns_to_be_added = {x:properties[x] for x in properties if x not in columns_existed}
        
        # Create new columns
        for column in columns_to_be_added:
            schema[column] = {
                "name": properties[column]['name'],
                "type": properties[column]['type']
            }
        cv.collection.set(path=['schema'], value=schema)
    else:
        notion_latest = notion_records[0]
        # time_notion = pytz.UTC.localize(notion_latest.date_added.start)
        mytz = pytz.timezone(get_localzone().zone)
        time_notion = mytz.localize(notion_latest.date_added.start)
        title_notion = notion_latest.name
        df['update'] = df.apply(lambda x:filter_new_zotero_recs(time_notion, title_notion, x), axis=1)
        df = df[df['update']==True]
    
    
    if len(df) > 0:
        # Change journal name to lowercase for easier matching with impact facter and CAS table
        df['journal'] = df.apply(lambda x:journal_lower(x), axis=1)

        # Link records with impact factor and CAS classification
        dfif = merge_IF_CAS(impact_factor, cas)
        tbl = df.merge(dfif, on='journal', how='left')

        # Add extra information based on zotero metadata
        tbl['Local_file'] = tbl.apply(lambda x: pdf_url(x, pdf_local_url), axis=1)
        tbl['Name'] = tbl.apply(lambda x: file_name(x), axis=1)
        tbl['Impact_factor'] = tbl.apply(lambda x:round(x['Impact_factor'], 1), axis=1)
        tbl['Authors'] = tbl.apply(lambda x:reformat_names(x['Author']), axis=1)
        tbl.rename(columns={"Publication Title": "Journal"}, inplace=True)
        tbl.Impact_factor.fillna(0, inplace=True)
        tbl.Cas.fillna("NA", inplace=True)
        tbl.Subject.fillna("NA", inplace=True)
        tbl.fillna('', inplace=True)

        # Some journals in zotero are not in CAS or JCR, set them as NA
        # todo: manually check these recores, because most of them are false renamed by zotero
        tbl['Cas'] = tbl.apply(lambda x: x['Cas'] if len(x['Cas'])==2 else 'NA', axis=1)

        ## Add to notion
        recs = tbl.to_dict(orient="records")
        for rec in recs:
            add_row(cv, rec, pdf_local_url, pdf_remote_url)
    else:
        print("No new records in zotero library!")
    
    # Create folder for supplementary files
    add_supp_dir(pdf_local_folder, supplementary_path)


if __name__ == '__main__':
    main()
