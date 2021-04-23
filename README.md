# zotero2notion

Import Zotero library to Notion 

## Install

1. Clone or download repo 
2. [Install conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/#regular-installation), then run the following code,

```sh
conda env create -f environment.yml
conda activate zotero2notion
pip install notion
```

## Usage

1. Create a database with following columns in Notion, and copy the database url

![zotero_db_in_notion](./imgs/zotero_db.png)

2. Obtain the `token_v2` value by inspecting your browser cookies on a logged-in session on Notion.so

3. Obtain your zotero library id and api key

4. Run command,

```sh
cd scripts
./zotero2notion.py -i ../data/impact_factor_2020.tsv \
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
