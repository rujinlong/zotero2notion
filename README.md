# zotero2notion

Import Zotero library to Notion

## Install

```sh
# using pip
pip install zotero2notion

# or using conda
conda install -c rujinlong zotero2notion
```

## Usage

1. [Create an integration](https://www.notion.so/my-integrations) and find the token

2. Create a new database with following properties and property type; Remove all rows; Copy the database id
   ![](http://i.imgur.com/lkKVTta.png)

3. Obtain your zotero library id and [api key](https://www.zotero.org/settings/keys)

4. Modify `config.txt` file, fill in the information you obtained in step 1-3.

5. Run command,

```sh
# Add most recent 10 papers to notion
zotero2notion -c config.txt -n 10
```

# TODO

- [x] Add configuration file
- [ ] Automatic update (every one hour)
- [ ] Clean code
- [ ] Automatic update (when there is new records in zotero)
