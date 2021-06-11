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
    if len(children) != 0:
        return [[x.title, child.title, x.get_browseable_url(), child.get_browseable_url()] for child in children]


@click.command()
@click.option("--config", '-c', default="~/github/zotero2notion/config.ini", help="config.ini")
@click.option("--notion_table_url", '-u', help="Notion database url")
@click.option("--fout", '-o', default='notion.html', help="output html file name")
@click.option('--all_nodes/--linked_nodes', default=False, help="Output all nodes or only linked nodes")
def main(config, notion_table_url, fout, all_nodes):
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
        edge_items = get_edges(item)
        if edge_items:
            edges += [e[:2] for e in edge_items if e[1]!='']
            for e in edge_items:
                nodes += [(e[0], {"title":"<a href='{}', target='_blank'>{}</a>".format(e[2], 'Open')}),
                          (e[1], {"title":"<a href='{}', target='_blank'>{}</a>".format(e[3], 'Open')})]
        if all_nodes:
            nodes.append((item.title, {"title":"<a href='{}', target='_blank'>{}</a>".format(item.get_browseable_url(), 'Open')}))
            

    # Unique nodes
    nodes_added = {}
    nodes_nr = []
    for n in nodes:
        if n[0]!='' and n[0] not in nodes_added.keys():
            nodes_added[n[0]] = n
            nodes_nr.append(n)
    
    # df = pd.DataFrame(edges).to_csv('a.tsv', index=False, header=False, sep='\t')
    # Create tmp graph
    g = nx.Graph()
    g.add_nodes_from(nodes_nr)
    g.add_edges_from(edges)
    degree = dict(g.degree)

    # Add degree
    nodes2 = []
    for node in nodes_nr:
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

    pv.show_buttons(filter_='layout')
    # pv.toggle_physics(False)
    pv.show(fout)


if __name__ == '__main__':
    main()
