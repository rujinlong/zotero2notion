#!/usr/bin/env python

import os
import click
import pandas as pd
import re
from notion_client import Client
import os
import configparser



def update_row(notion_connect, notion_table_id, zotrec):
    relation_items = ["crossref1"]

    props = {}
    for key in relation_items:
        # x[:-4] removes ".pdf" in file name
        page_ids = [get_notion_pageID_by_pageName(notion_connect, notion_table_id, fname[:-4]) for fname in zotrec[key]]
        relation_pages = [{'id':page_id} for page_id in page_ids if page_id!=""]
        if len(relation_pages) > 0:
            print(relation_pages)
            props[key] = {'type': 'relation', 'relation': relation_pages}
    
    props["Name"] = {"title":[{"text":{"content": zotrec['Name']}}]}
    return props


@click.command()
@click.option("--config", '-c', default="~/github/zotero2notion/config.ini", help="config.ini")
@click.option("--zotero_export", '-e', help="Zotero exported file")
def main(config, zotero_export):
    """
    Usage:
    
    update_crossref.py -c config.ini -e exported.txt
    """

    # Read config file
    config = os.path.expanduser(config)
    cfg = configparser.ConfigParser()
    cfg.read(config)
    impact_factor = cfg['Resources']['impact_factor']
    cas = cfg['Resources']['cas']
    notion_token = cfg['Notion']['notion_token']
    notion_table_id = cfg['Notion']['notion_table_id']
    zotero_library_id = cfg['Zotero']['zotero_library_id']
    zotero_api_key = cfg['Zotero']['zotero_api_key']
    pdf_local_folder = cfg['PDFs']['pdf_local_folder']
    pdf_local_url = cfg['PDFs']['pdf_local_url']
    pdf_remote_url = cfg['PDFs']['pdf_remote_url']
    supplementary_path = cfg['PDFs']['supplementary_path']

    df_parent2child =
    df_parent2relations = 
    df_child2relations = df_parent2child.merge(df_parent2relations, on="parent", how="inner")


    # Fetch records in zotero library 
    df = fetch_zotero_records(zotero_library_id, zotero_api_key, zotero_topn)
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
            props = new_row(notion, notion_table_id, rec)
            notion.pages.create(parent={"database_id": notion_table_id}, properties=props)
    else:
        print("No new records in zotero library!")
    
    # Create folder for supplementary files
    add_supp_dir(pdf_local_folder, supplementary_path)


if __name__ == '__main__':
    main()
