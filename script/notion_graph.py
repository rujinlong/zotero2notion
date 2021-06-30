#!/usr/bin/env python

import os
import configparser
import click
from notion.client import NotionClient
import networkx as nx
from pyvis.network import Network
import pandas as pd
import re

def get_zettelkasten_links(page):
    children = page.get_property('children')
    if len(children) != 0:
        edge_items = [[page.title, child.title, page.get_browseable_url(), child.get_browseable_url()] for child in children]
        return edge_items
    
    
def get_backlinks(client, page):
    backlinks = page.get_backlinks()
    edge_items = []
    for backlink in backlinks:
        backlink_url = re.sub(r'#.*', '', backlink.get_browseable_url())
        backlink_page = client.get_block(backlink_url)
        edge_items.append([page.title, backlink_page.title, page.get_browseable_url(), backlink_url])
    return edge_items


def get_ref_links(client, page):
    refs = page.refs
    edge_items = []
    for ref in refs:
        ref_url = re.sub(r'#.*', '', ref.get_browseable_url())
        ref_page = client.get_block(ref_url)
        edge_items.append([ref_page.title, page.title, ref_url, page.get_browseable_url()])
    return edge_items


@click.command()
@click.option("--config", '-c', default="~/github/zotero2notion/config.ini", help="config.ini")
@click.option("--notion_table_url", '-u', help="Notion database url")
@click.option("--fout", '-o', default='notion.html', help="output html file name")
@click.option('--all_nodes/--linked_nodes', default=False, help="Output all nodes or only linked nodes")
@click.option('--backlinks/--no_backlinks', default=False, help="Output backlink nodes")
@click.option('--zotero_refs/--no_zotero_refs', default=False, help="Output zotero ref nodes")
def main(config, notion_table_url, fout, all_nodes, backlinks, zotero_refs):
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
    for page in notion_records:
        edge_zettelkasten = get_zettelkasten_links(page)
        if edge_zettelkasten:
            edge_items = edge_zettelkasten
            for e in edge_zettelkasten:
                nodes += [(e[0], {"title":"<a href='{}', target='_blank'>{}</a>".format(e[2], 'Open'), "color":"red"}),
                          (e[1], {"title":"<a href='{}', target='_blank'>{}</a>".format(e[3], 'Open'), "color":"red"})]
        else:
            edge_items = []

        
        if zotero_refs:
            edge_refs = get_ref_links(client, page)
            edge_items += edge_refs
            for e in edge_refs:
                # source: refs; target: zettelkasten
                nodes += [(e[0], {"title":"<a href='{}', target='_blank'>{}</a>".format(e[2], 'Open'), "color":"green"}),
                          (e[1], {"title":"<a href='{}', target='_blank'>{}</a>".format(e[3], 'Open'), "color":"red"})]

        if backlinks:
            edge_backlinks = get_backlinks(client, page)
            edge_items += edge_backlinks
            for e in edge_backlinks:
                # source: zettelkasten
                nodes += [(e[0], {"title":"<a href='{}', target='_blank'>{}</a>".format(e[2], 'Open'), "color":"red"}),
                          (e[1], {"title":"<a href='{}', target='_blank'>{}</a>".format(e[3], 'Open')})]

        if len(edge_items) > 0:
            edges += [e[:2] for e in edge_items if e[1]!='']

        if all_nodes:
            nodes.append((page.title, {"title":"<a href='{}', target='_blank'>{}</a>".format(page.get_browseable_url(), 'Open')}))
            

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
        node_attr['size'] = degree[node_name] + 3
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
