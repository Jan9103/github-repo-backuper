# GitHub Repository Backuper

This is a tool for creating backups of github repositories.

## Backup

### Supported informations:

* [x] git (including lfs)
* [x] Issues (including comments, close-state, assignees, labels, etc)
* [x] Pull-Requests (including git base/head, comments, close/merge-state, assignees, labels, etc)
* [x] Releases (including assets)
* [x] Wiki
* [x] Repo-Projects
* [ ] GitHub-Actions results
* [ ] Discussions
* [ ] Org-Projects

### Download Features:

* No github account needed, but possible for [faster downloads](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api)
* Structured and machine readable output
* Arguments can configure what gets downloaded
* Increments of existing backups are possible (and are faster than new backups)
* It handles ratelimits (by waiting once its reached) and pagination
* Optional on-save compression of result (`--gzip`)

### Usage:

Dependencis: [python3](https://www.python.org/) (3.11 was used for testing), [python3-requests](https://pypi.org/project/requests/)

```sh
python3 github-repo-backuper.py --help

python3 github-repo-backuper.py jan9103 github-repo-backuper
```

## Webui

This repo also includes a webui for viewing (and maybe in the future starting) backups.

* [x] User / Organisation list
* [x] Repo list
* [x] Repo overview (README, filelist)
* [x] Issue/PR list (with state, name, label, author, and comment-count)
* [x] Issue/PR detail view (with name, author, labels, assignees, description, reactions, comments, state, lock-state, etc)
* [ ] Release list
* [ ] File explorer
* [ ] Wiki viewer
* [ ] Repo-Project viewer
* [ ] Discussion list
* [ ] Discussion details

### Usage:

The UI is written in the [nu](https://nushell.sh) script language (required).  
[numng](https://github.com/jan9103/numng) can be used to download the dependencies automatically.

Manual dependency installation:

1. `mkdir nulibs`
2. `curl "https://raw.githubusercontent.com/Jan9103/webserver.nu/main/webserver/mod.nu" -o nulibs/webserver.nu`
3. Copy the `nutils` directory from the [nutils-repo](https://github.com/jan9103/nutils) into `nulibs`

Starting it:

```sh
nu webui.nu
```
