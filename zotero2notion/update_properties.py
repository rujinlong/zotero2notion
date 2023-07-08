#!/usr/bin/env python

import configparser
import urllib

import click
from notion_client import Client


def notion_db_query(client, notion_table_id, cursur=None):
    if cursur is None:
        notion_records = client.databases.query(**{"database_id": notion_table_id})
    else:
        notion_records = client.databases.query(
            **{"database_id": notion_table_id, "start_cursor": cursur}
        )
    return notion_records


@click.command()
@click.option("--config", "-c", help="config.ini")
def main(config):
    """
    Usage:

    update_properties.py -c config.ini
    """

    # Read config file
    cfg = configparser.ConfigParser()
    cfg.read(config)
    notion_token = cfg["Notion"]["notion_token"]
    notion_table_id = cfg["Notion"]["notion_table_id"]
    url_connected_papers = cfg["PDFs"]["url_connected_papers"]

    notion = Client(auth=notion_token)
    cursor = 1
    while cursor:
        if cursor == 1:
            cursor = None
        notion_records = notion_db_query(notion, notion_table_id, cursor)

        for nr in notion_records["results"]:
            if nr["properties"]["Graph"]["url"] is None:
                title = nr["properties"]["Title"]["rich_text"][0]["plain_text"]
                print(title)
                try:
                    url = urllib.parse.quote(title)
                    notion.pages.update(
                        nr["id"],
                        properties={
                            "Graph": {"type": "url", "url": url_connected_papers + url}
                        },
                    )
                except:
                    continue

        cursor = notion_records["next_cursor"]


if __name__ == "__main__":
    main()
