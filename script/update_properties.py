#!/usr/bin/env python

import click
import configparser
from notion.client import NotionClient


@click.command()
@click.option("--config", '-c', help="config.ini")
def main(config):
    """
    Usage:
    
    update_properties.py -c config.ini
    """

    # Read config file
    cfg = configparser.ConfigParser()
    cfg.read(config)
    notion_token = cfg['Notion']['notion_token']
    notion_table_url = cfg['Notion']['notion_table_url']
    pdf_local_url = cfg['PDFs']['pdf_local_url']
    pdf_remote_url = cfg['PDFs']['pdf_remote_url']

    # Fetch records in notion table
    client = NotionClient(token_v2=notion_token)
    cv = client.get_collection_view(notion_table_url)
    notion_records = cv.collection.get_rows(sort=[{"direction": "descending", 
                                                   "property": "Date_added"}])
    for nr in notion_records:
        nr.local_file = nr.local_file.replace("http://jinlong.local:8668/zotero_papers/", pdf_local_url)
        nr.pdf = nr.local_file.replace(pdf_local_url, pdf_remote_url)

if __name__ == '__main__':
    main()
