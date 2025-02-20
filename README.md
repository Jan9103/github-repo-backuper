# GitHub Repository Backuper

This is a tool for creating backups of github repositories.

---

## Github Backup Tool

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

Dependencies: [python3](https://www.python.org/) (3.11 was used for testing), [python3-requests](https://pypi.org/project/requests/)

```sh
python3 github-repo-backuper.py --help

python3 github-repo-backuper.py jan9103 github-repo-backuper
```

**Notice:** The github-API ratelimit seems to be IP-based and using it up might cause
other programs, such as GE-proton download-tools, to temporarely fail.  
This issue can be reduced using `--reserve-rate-limit 10` (or similar).

---

## Webui (basic archive viewer and starter)

This repo also includes a webui for viewing and starting backups.  
The implementation is focused on simplicity and small to medium sized repos.
Larger repos (tested with 4475 compressed issues) can still be viewed, but rendering the issue-list serverside can take several minutes on a overloaded raspberry pi 4.

* [x] User / Organisation list
* [x] Repo list
* [x] Repo overview (README, filelist)
* [x] Issue/PR list (with state, name, label, author, and comment-count)
* [x] Issue/PR detail view (with name, author, labels, assignees, description, reactions, comments, state, lock-state, etc)
* [x] Release list
* [x] Release details
* [ ] Release asset download
* [ ] File explorer
* [ ] Wiki viewer
* [ ] Repo-Project viewer
* [ ] Discussion list
* [ ] Discussion details
* [ ] View commit diffs
* [ ] View commit history
* [x] Start new downloads (with queue)
* [x] All paths are prefixed with `/github` to make it easier to use with a reverse-proxy

### Usage:

The UI is written in the [nu](https://nushell.sh) script language (required).  
[numng](https://github.com/jan9103/numng) can be used to download the dependencies automatically.

Manual dependency installation:

1. `mkdir nulibs`
2. Copy the `webserver` directory from the [webserver.nu-repo](https://github.com/jan9103/webserver.nu) into `nulibs` (used as webserver framework)
3. Copy the `nutils` directory from the [nutils-repo](https://github.com/jan9103/nutils) into `nulibs` (used for escaping html, etc)
3. Copy the `nagoya` directory from the [nagoya-repo](https://github.com/jan9103/nagoya) into `nulibs` (used for multithreading by the download system)

Starting it:

```sh
nu webui.nu

# with download-ui:
nu webui.nu --with-download-ui

# on another port (default is 8080)
nu webui.nu --port 80
```

---

## Other Scripts

usage: `python3 [SCRIPT-NAME] --help`

website | script-name | note(s)
------- | ----------- | -------
<https://code.google.com/archive> | `google-code-archive-backuper.py` | the api is rapidly deteriorating, so its 90% workarounds and might break again

