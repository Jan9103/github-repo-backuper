# GitHub Repository Backuper

This is a tool for creating backups of github repositories.

Supported informations:

* [x] git (including lfs)
* [x] Issues (including comments, close-state, assignees, labels, etc)
* [x] Pull-Requests (including git base/head, comments, close/merge-state, assignees, labels, etc)
* [x] Releases (including assets)
* [x] Wiki
* [ ] GitHub-Actions results
* [ ] Discussions
* [ ] Projects

Example usecases:

* You suspect a repo might be taken offline soon (Yuzu, I-Soon, etc) and want to keep the full history
* You don't trust GitHub and want a local backup.
* You want to migrate to a different platform and want to copy your data (no this does not upload).

Features:

* No github account needed
* Structured and machine readable output
* Arguments can configure what gets downloaded
* Increments of existing backups are possible (and are faster than new backups)
* It handles ratelimits (by waiting once its reached) and pagination
