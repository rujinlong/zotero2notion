#!/usr/bin/env python

import click
import pandas as pd
import re


def extract_articleID_and_filename(record):
    record_items = record.split('\n')
    ref_id = "@" + re.search('{(.+?),', record_items[0]).group(1)
    item_file = [x for x in record_items if x.startswith('\tfile = {')]
    if len(item_file) > 0:
        item_file = item_file[0]
        notion_Name = re.search(r'\tfile = {(.+?).pdf:/Users', item_file, re.IGNORECASE).group(1)
    else:
        notion_Name = None
        
    return ref_id, notion_Name


@click.command()
@click.option("--notion_draft", '-i', help="Notion exported markdown file")
@click.option("--bibtex", '-r', help='Zotero exported bibtex file')
@click.option('--manuscript', '-o', help="Output file in markdown format")
def main(notion_draft, bibtex, manuscript):
    with open(bibtex, 'r') as fh:
        ref = fh.read()
        items = [x for x in ref.split('\n@') if len(x)>10]
    
    rst = []
    for record in items:
        ref_id, notion_Name = extract_articleID_and_filename(record)
        if notion_Name != None:
            rst += [[ref_id, notion_Name, record]]
    
    df = pd.DataFrame(rst, columns=['ref_id', 'notion_Name', 'bibtex_rec'])
    recs = df.to_dict(orient="records")
    
    # replace in draft
    with open(notion_draft, "r") as fh:
        draft = fh.read()
        draft = re.sub(r'\(https://www.notion.so/[\w\"\'+-]*\)', '', draft)
    
    references = []
    for rec in recs:
        if rec['notion_Name'] in draft:
            draft = draft.replace(rec['notion_Name'], rec['ref_id'])
            references.append('@'+rec['bibtex_rec'])
    
    draft = re.sub(r'\],[\s]+\[@', '; @', draft)
    with open(manuscript, 'w') as fh:
        fh.write(draft)

    with open(manuscript+".bibtex", 'w') as fh:
        fh.write('\n'.join(references))
        

if __name__ == '__main__':
    main()
