#!/usr/bin/env python

import os
import configparser
import click
from notion.client import NotionClient
import networkx as nx
from pyvis.network import Network
import pandas as pd


def get_edges(x):
    children = x.get_property('children')
    if len(children) > 0:
        if len(children[0].title) > 0:
            return [[x.title, child.title] for child in children]


@click.command()
@click.option("--config", '-c', default="~/github/zotero2notion/config.ini", help="config.ini")
@click.option("--notion_table_url", '-u', help="Notion database url")
@click.option("--fout", '-o', default='notion.html', help="output html file name")
def main(config, notion_table_url, fout):
    config = os.path.expanduser(config)
    cfg = configparser.ConfigParser()
    cfg.read(config)
    notion_token = cfg['Notion']['notion_token']
    
    # Read notion database
    client = NotionClient(token_v2=notion_token)
    cv = client.get_collection_view(notion_table_url)
    notion_records = cv.collection.get_rows()

    # Extract nodes and edges
    edges = []
    nodes = []
    for item in notion_records:
        nodes.append((item.title, {"title":"<a href='{}', target='_blank'>{}</a>".format(item.get_browseable_url(), 'Open')}))
        edge_item = get_edges(item)
        if edge_item:
            edges += edge_item
    
#    df = pd.DataFrame(edges).to_csv('a.tsv', index=False, header=False, sep='\t')
    # Create tmp graph
    g = nx.Graph()
    g.add_nodes_from(nodes)
    g.add_edges_from(edges)
    degree = dict(g.degree)

    # Add degree
    nodes2 = []
    for node in nodes:
        node_name = node[0]
        node_attr = node[1]
        node_attr['size'] = degree[node_name] + 5
        nodes2.append((node[0], node_attr))
    
    # Create final graph
    g = nx.DiGraph()
    g.add_nodes_from(nodes2)
    g.add_edges_from(edges)
    
    # Convert to pyvis network
    pv = Network(height='750px', width='100%', directed=True)
    pv.from_nx(g)

    pv.show_buttons(filter_='nodes')
    # pv.toggle_physics(False)
    pv.show(fout)


if __name__ == '__main__':
    main()
