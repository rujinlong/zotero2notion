# zotero2notion

Import Zotero library to Notion 

## Install

1. Clone or download repo 
2. [Install conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/#regular-installation), then run the following code,

```sh
conda env create -f environment.yml
conda activate zotero2notion
pip install notion-client
```

## Usage

1. [Create an integration](https://www.notion.so/my-integrations) and find the token

2. Create a new database with following properties and property type; Remove all rows; Copy the database id
    ![](http://i.imgur.com/lkKVTta.png)

3. Obtain your zotero library id and [api key](https://www.zotero.org/settings/keys)

4. Modify `config.ini.sample` file, rename it to `config.ini` or make a copy

5. Run command,

```sh
# Add most recent 100 papers to notion
./script/zotero2notion.py -c config.ini -n 100
```

# TODO

- [x] Add configuration file
- [ ] Automatic update (every one hour)
- [ ] Clean code
- [ ] Automatic update (when there is new records in zotero)
