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

1. Create a new database, then remove all rows in it

2. Copy the database url

3. Obtain the `token_v2` value by inspecting your browser cookies on a logged-in session on Notion.so

4. Obtain your zotero library id and api key

5. Modify `config.ini.sample` file, rename it to `config.ini` or make a copy

5. Run command,

```sh
cd scripts

# Add most recent 10 papers to notion
./zotero2notion.py -c config.ini -n 10
```

![zotero](./imgs/zotero.png)

# TODO

- [x] Add configuration file
- [ ] Automatic update (every one hour)
- [ ] Clean code
- [ ] Automatic update (when there is new records in zotero)
