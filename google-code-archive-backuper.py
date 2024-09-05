#!/usr/bin/env python3
import requests
import json
import gzip
import subprocess
from os import path, makedirs, listdir, unlink,chdir
from typing import Any, List
from datetime import datetime
from tempfile import TemporaryDirectory
from copy import deepcopy
from zipfile import ZipFile
from shutil import move


def _format_url(
    bucket: str = "google-code-archive",
    domain: str = "code.google.com",
    project: str = "earthsurfer",
    file: str = "project.json",
) -> str:
    return f"https://storage.googleapis.com/{bucket}/v2/{domain}/{project}/{file}"


def archive(
    project_name: str,
    domain: str = "code.google.com",
    do_gzip: bool = True,
) -> None:
    '''
    Note: it gets converted into a github-similar format

    if you want to archive <https://code.google.com/archive/p/earthsurfer/> call archive("earthsurfer")
    the "domain" argument can be "code.google.com", "eclipselabs.org", or "apache-extras.org"
    '''
    base_path: str = path.join(".", "google-code", domain, project_name)
    makedirs(base_path, exist_ok=True)
    base_path = path.abspath(base_path)

    response: requests.Response = requests.get(_format_url(domain=domain, project=project_name, file="project.json"))
    response.raise_for_status()
    project_meta = response.json()
    _write_gzipable_json(path.join(base_path, "original_project.json"), project_meta, do_gzip=do_gzip)

    issue_id: int = 1
    makedirs(path.join(base_path, "issues"), exist_ok=True)
    while True:
        response = requests.get(_format_url(domain=domain, project=project_name, file=f"issues/issue-{issue_id}.json"))
        if response.status_code != 200:
            break
        issue = response.json()
        _write_gzipable_json(
            path.join(base_path, "issues", f"{issue['id']}.json"),
            {
                "title": issue["summary"],
                "state": {
                    "new": "open",
                    "accepted": "closed",
                }[issue["status"].lower()],
                "labels": issue["labels"],
                "reactions": {"+1": issue["stars"]},
                "comments": [{
                    "user": comment["commenterId"],  # TODO: figure out how to get name (especially since this id is project specific (wtf google))
                    "body": comment["content"],
                    "created_at": datetime.fromtimestamp(comment["timestamp"]).strftime('%Y-%m-%dT%H:%M:%SZ'),  # dont ask me weather `timestamp` is creation or edit date..
                } for comment in issue["comments"]],
            },
            do_gzip=do_gzip,
        )
        issue_id += 1
    del issue_id

    # the git clone is completely borked and in general 90% dosnt work.
    # this source-code (+ sometimes history) is the only working method i found (except for svndump, which only works with svn repos)

    with TemporaryDirectory() as tmpdir:
        zip_file = path.join(tmpdir, "source.zip")
        _download_file(
            _format_url(bucket="google-code-archive-source", domain=domain, project=project_name, file="source-archive.zip"),
            zip_file,
            gzip_result=False,
        )
        start_dir: str = deepcopy(str(path.curdir))
        chdir(tmpdir)  # "zf.extractall" "pwd" argument does not work (thanks python)
        with ZipFile(zip_file, "r") as zf:
            zf.extractall()
        chdir(start_dir)
        subdir_name: str = [i for i in listdir(tmpdir) if i != "source.zip"][0]
        if path.isdir(gitdir := path.join(tmpdir, subdir_name, ".git")):
            subprocess.run(
                ["git", "clone", "--mirror", gitdir, "git"],
                cwd=base_path,
            )
        else:
            move(zip_file, path.join(base_path, "google-code-archive-source.zip"))
                

    # WIKIs dont even work on the website https://code.google.com/archive/p/earthsurfer/wikis

    # DOWNLOADs dont even work on the website https://code.google.com/archive/p/earthsurfer/downloads


def _download_file(url: str, local_file: str, gzip_result: bool = False) -> None:
    """
    gzip_result will just gzip the result without questions.
        change the filename and check for duplicate compression at the other end.
    """
    # https://stackoverflow.com/a/16696317
    with requests.get(url, stream=True) as r:
        r.raise_for_status()  # TODO: handle
        if gzip_result:
            with gzip.open(local_file, "wb") as fp:
                for chunk in r.iter_content(chunk_size=8192):
                    fp.write(chunk)
        else:
            with open(local_file, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
    


def _write_gzipable_json(filepath: str, jsondata: Any, do_gzip: bool = True) -> None:
    if do_gzip:
        with gzip.open(f"{filepath}.gz", "wt") as fp:
            json.dump(jsondata, fp)
    else:
        with open(filepath, "w") as fp:
            json.dump(jsondata, fp)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        prog="github-repo-backuper",
        description="Back up a github repository",
    )
    parser.add_argument("project_name", help="Name of the repository. Example: earthsurfer", type=str)
    parser.add_argument("--domain", type=str, default="code.google.com", help="Domain it was published under")
    args = parser.parse_args()
    archive(project_name=args.project_name, domain=args.domain, do_gzip=True)
    
