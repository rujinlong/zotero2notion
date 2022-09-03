#!/usr/bin/env python

import os
import click
import pandas as pd
import urllib
import re
from notion_client import Client
import os
from dateutil import parser
from pyzotero import zotero
import configparser
import bibtexparser
from bibtexparser.bparser import BibTexParser

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

def get_notion_pageID_by_pageName(notion_connect, notion_table_id, page_name):
    query = notion_connect.databases.query(**{
        "database_id": notion_table_id, 
        "filter":{
            "property": "Name", 
            "text":{
                "equals": page_name,
                },
            },
        }
    )
    rst = query['results']
    if len(rst) > 0:
        page_id = rst[0]['id']
    else:
        page_id = ""
    return page_id


def new_row(notion_connect, notion_table_id, zotrec):
    text_items = ["Subject", "Authors", "CAS", "Title", "Journal"]
    url_items = ["Url", "Local_file", "PDF", "Graph"]
    date_items = ["Date_added", "Date_published"]
    num_items = ["Impact_factor"]
    relation_items = ["crossref1"]

    props = {}
    for key in text_items:
        props[key] = {'type': 'rich_text', 'rich_text': [{'type': 'text', 'text': {'content': zotrec[key]},}]}

    for key in url_items:
        props[key] = {'type': 'url', 'url': zotrec[key]}

    for key in date_items:
        props[key] = {'type': 'date', 'date': {'start': zotrec[key], 'end': None}}

    for key in num_items:
        props[key] = {'type': 'number', 'number': zotrec[key]}
    
    for key in relation_items:
        # x[:-4] removes ".pdf" in file name
        page_ids = [get_notion_pageID_by_pageName(notion_connect, notion_table_id, x[:-4]) for x in zotrec[key]]
        relation_pages = [{'id':page_id} for page_id in page_ids if page_id!=""]
        if len(relation_pages) > 0:
            print(relation_pages)
            props[key] = {'type': 'relation', 'relation': relation_pages}
    
    props["Name"] = {"title":[{"text":{"content": zotrec['Name']}}]}
    return props


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
    dfcas = dfcas[['journal', 'CAS', 'Subject']].copy()
    dfcas['journal'] = dfcas.apply(lambda x:str(x['journal']).lower(), axis=1)
    dfcas['Subject'] = dfcas.apply(lambda x:str(x['Subject']).capitalize(), axis=1)

    dfif = pd.read_csv(impact_factor, sep='\t')
    dfif.columns = ['journal', "Impact_factor"]
    dfif['journal'] = dfif.apply(lambda x:x['journal'].lower(), axis=1)
    
    df = dfif.merge(dfcas, on="journal", how="outer").drop_duplicates()
    df.Impact_factor.fillna(0, inplace=True)
    df.CAS.fillna("NA", inplace=True)
    df.Subject.fillna("NA", inplace=True)
    return df.groupby('journal', as_index=False).agg({'Subject' : '; '.join, 'Impact_factor': 'first', 'CAS' : 'first'})


def select_attachment_items(items):
    items_with_attachment = []
    parent_keys = list(set([x['key'] for x in items if not x['data'].get('contentType')]))
    attachment_keys = list(set([x['key'] for x in items if x['data'].get('contentType')=="application/pdf"]))
    for item in items:
        if item['key'] in attachment_keys:
            parent_key = item.get('links')['up']['href'].split('/')[-1]
            # Remove trash items
            if parent_key in parent_keys:
                items_with_attachment.append(item['data'])
    return items_with_attachment


def get_children_title_from_parent_key(zot, parent_key):
    children_title = zot.children(parent_key)[0]['data']['title']
    return children_title

def get_relation_titles(zot, parent):
    relation_info = parent['relations']
    if relation_info.get('dc:relation'):
        relations = relation_info['dc:relation']
        if isinstance(relations, str):
            relations = [relations]
        relation_keys = [x.split('/')[-1] for x in relations]
        relation_titles = [get_children_title_from_parent_key(zot, x) for x in relation_keys]
    else:
        relation_titles = []
    return relation_titles


def add_parent_info(zot, child):
    parent = zot.item(child['parentItem'])['data']
    
    child['Author'] = combine_authors(parent.get('creators'))
    child['Date_published'] = parser.parse(parent.get('date')).astimezone()
    child['Publication Title'] = parent.get('publicationTitle')
    child['Url'] = parent.get('url')
    child['Title'] = parent.get('title')
    child['File Attachments'] = child.get('title')
    child['Date_added'] = parser.parse(child.get('dateAdded')).astimezone()
    child['crossref1'] = get_relation_titles(zot, parent)

    keys = ['Author', 'Date_published', 'Publication Title', 'File Attachments', 'Date_added', 'Url', 'Title', 'crossref1']
    # keys = ['Author', 'Date_published', 'Publication Title', 'File Attachments', 'Date_added', 'Url', 'Title']
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


# Add bibtex to CiteKey database
def new_row_citekey(notion, notion_db_zotero_id, rec):
    props = {}
    page_id = get_notion_pageID_by_pageName(notion, notion_db_zotero_id, rec["pdf_name"][:-4])
    if page_id != "":
        relation_page = [{'id': page_id}]
        if len(relation_page) > 0:
            props["pdf_name"] = {'type': 'relation', 'relation': relation_page}
        
        props["Name"] = {"title":[{"text":{"content": rec['citekey']}}]}
    else:
        props = ""
    return props

def update_citekey(notion, notion_db_citekey_id, notion_db_zotero_id, bibtex, df_new_papers):
    new_papers = df_new_papers["Name"].tolist()
    parser = BibTexParser(common_strings=True)
    parser.ignore_nonstandard_types = True
    parser.common_strings = False
    
    bibs = []
    with open(bibtex, "r") as fh:
        bib_str = fh.read()
    bibdb = bibtexparser.loads(bib_str, parser=parser)
    for bib in bibdb.entries:
        if "file" in bib.keys():
            citekey = bib["ID"]
            pdf_name = bib["file"].split(";")[0].split("/")[-1]
            title = pdf_name[:-4]  # remove .pdf/.PDF extension
            if title in new_papers:
                bibs.append([citekey, pdf_name])

    if len(bibs) > 0:
        df = pd.DataFrame(bibs, columns=["citekey", "pdf_name"])
        bib_recs = df.to_dict(orient="records")

        for rec in bib_recs:
            props = new_row_citekey(notion, notion_db_zotero_id, rec)
            if props != "":
                notion.pages.create(parent={"database_id": notion_db_citekey_id}, properties=props)



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
    bibtex = cfg['Resources']['bibtex']
    notion_token = cfg['Notion']['notion_token']
    notion_table_id = cfg['Notion']['notion_table_id']
    notion_db_citekey_id = cfg['Notion']['notion_db_citekey_id']
    zotero_library_id = cfg['Zotero']['zotero_library_id']
    zotero_api_key = cfg['Zotero']['zotero_api_key']
    pdf_local_folder = cfg['PDFs']['pdf_local_folder']
    pdf_local_url = cfg['PDFs']['pdf_local_url']
    pdf_remote_url = cfg['PDFs']['pdf_remote_url']
    url_connected_papers = cfg['PDFs']['url_connected_papers']
    supplementary_path = cfg['PDFs']['supplementary_path']

#     properties = {'Subject': {'name': 'Subject', 'type': 'text'},
#                 'Authors': {'name': 'Authors', 'type': 'text'},
#                 'Url': {'name': 'Url', 'type': 'url'},
#                 'Local_file': {'name': 'Local_file', 'type': 'url'},
#                 'Title': {'name': 'Title', 'type': 'text'},
#                 'Date_added': {'name': 'Date_added', 'type': 'date', 'date_format': 'YYYY/MM/DD', 'time_format': 'H:mm'},
#                 'PDF': {'name': 'PDF', 'type': 'url'},
#                 'Impact_factor': {'name': 'Impact_factor', 'type': 'number', 'number_format': 'number'},
#                 'CAS': {'name': 'CAS', 'type': 'text'},
#                 'Modified': {'name': 'Modified', 'type': 'last_edited_time'},
#                 'comments': {'name': 'comments', 'type': 'text'},
#                 'Journal': {'name': 'Journal', 'type': 'text'},
#                 'Date_published': {'name': 'Date_published', 'type': 'date', 'date_format': 'YYYY/MM/DD', 'time_format': 'H:mm'}}
    
    # Fetch records in zotero library 
    df = fetch_zotero_records(zotero_library_id, zotero_api_key, zotero_topn)
    print(df.shape)
    # Change journal name to lowercase for easier matching with impact facter and CAS table
    df['journal'] = df.apply(lambda x:journal_lower(x), axis=1)

    # Link records with impact factor and CAS classification
    dfif = merge_IF_CAS(impact_factor, cas)
    tbl = df.merge(dfif, on='journal', how='left')

    # Add extra information based on zotero metadata
    tbl['Date_added'] = tbl.apply(lambda x: str(x['Date_added']), axis=1)
    tbl['Date_published'] = tbl.apply(lambda x: str(x['Date_published']), axis=1)
    tbl['Local_file'] = tbl.apply(lambda x: pdf_url(x, pdf_local_url), axis=1)
    tbl['Name'] = tbl.apply(lambda x: file_name(x), axis=1)
    tbl['Impact_factor'] = tbl.apply(lambda x:round(x['Impact_factor'], 1), axis=1)
    tbl['Authors'] = tbl.apply(lambda x:reformat_names(x['Author']), axis=1)
    tbl.rename(columns={"Publication Title": "Journal"}, inplace=True)
    tbl.Impact_factor.fillna(0, inplace=True)
    tbl.CAS.fillna("NA", inplace=True)
    tbl.Subject.fillna("NA", inplace=True)
    tbl.fillna('', inplace=True)

    # Some journals in zotero are not in CAS or JCR, set them as NA
    # todo: manually check these recores, because most of them are false renamed by zotero
    tbl['CAS'] = tbl.apply(lambda x: x['CAS'] if len(x['CAS'])==2 else 'NA', axis=1)
    tbl['PDF'] = tbl.apply(lambda x: x['Local_file'].replace(pdf_local_url, pdf_remote_url), axis=1)
    tbl['Graph'] = tbl.apply(lambda x: url_connected_papers+urllib.parse.quote(x['Title']), axis=1)

    # Fetch recent 100 records from notion table
    notion = Client(auth=notion_token)
    notion_records = notion.databases.query(**{"database_id": notion_table_id,
                             "sort": [{"timestamp":"Date_added", "direction":"descending"}]})

    # If the database is empty, create necessary columns
    if len(notion_records['results'])==0:
        print("This is an empty notion database, please ensure you set columns properly")
        # ------ TODO: set columns --------
        # Delete all columns in database
        # schema = {}
        # cv.collection.set(path=['schema'], value=schema)

#         schema = cv.collection.get()['schema']
#         columns_existed = [x['name'] for x in schema.values()]
#         columns_to_be_added = {x:properties[x] for x in properties if x not in columns_existed}
        
#         # Create new columns
#         for column in columns_to_be_added:
#             schema[column] = {
#                 "name": properties[column]['name'],
#                 "type": properties[column]['type']
#             }
#         cv.collection.set(path=['schema'], value=schema)
    else:
        literature_existed = [x["properties"]["Name"]['title'][0]['text']['content'] for x in notion_records['results']]
        tbl = tbl[~tbl.Name.isin(literature_existed)]
        print("Updating {} files...".format(tbl.shape[0]))
    

    ## Add to notion
    if len(tbl) > 0:
        recs = tbl.to_dict(orient="records")
        for rec in recs:
            try:
                props = new_row(notion, notion_table_id, rec)
                notion.pages.create(parent={"database_id": notion_table_id}, properties=props)
            except:
                print(props)
    else:
        print("No new records in zotero library!")
    
    # Create folder for supplementary files
    add_supp_dir(pdf_local_folder, supplementary_path)

    # Update CiteKey database
    if len(tbl) > 0:
        if len(bibtex) > 0:
            update_citekey(notion, notion_db_citekey_id, notion_table_id, bibtex, tbl)


if __name__ == '__main__':
    main()
