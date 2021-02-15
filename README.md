# notion_zotero

Import Zotero library to Notion 

## Requirements

- Python 3
- [notion-py](https://github.com/jamalex/notion-py)
- [pyzotero](https://github.com/urschrei/pyzotero)
- pandas
- click


## Usage

1. Clone or download repo 

2. Create a database with following columns in Notion, and copy the database url

![zotero_db_in_notion](./imgs/zotero_db.png)

3. Obtain the `token_v2` value by inspecting your browser cookies on a logged-in session on Notion.so

4. Obtain your zotero library id and api key

5. Run command

```sh
zotero2notion.py -i ../data/impact_factor_2020.tsv \
    -c ../data/cas2019.tsv \
    -t "<notion_token>" \
    -u "<notion_table_url>" \
    -l "<zotero_library_id>" \
    -k "<zotero_api_key>" \
    -n <zotero_topn>
```

![zotero](./imgs/zotero.png)

# TODO

- Add configuration file
- Automatic update (every one hour)
- Clean code
- Automatic update (when there is new records in zotero)
