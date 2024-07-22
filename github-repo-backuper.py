# Github-Repo-Backuper
# Copyright (C) 2024  Jan9103
#
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along with this program.  If not, see <http://www.gnu.org/licenses/>.


import argparse
import subprocess
import requests
import json
import logging
import gzip
from typing import Optional, List, Dict, Any
from time import sleep, time, strftime, gmtime
from math import floor
from os import makedirs, path
from sys import stdout


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
log_handler = logging.StreamHandler(stdout)
log_handler.setLevel(logging.DEBUG)
log_formatter = logging.Formatter('%(asctime)s::%(name)s::%(levelname)s: %(message)s')
log_handler.setFormatter(log_formatter)
logger.addHandler(log_handler)
del log_handler, log_formatter


GITHUB_HEADERS: Dict[str, str] = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": f"Github-Repo-Backuper <https://github.com/Jan9103/github-repo-backuper> (python requests {requests.__version__})",
    "Time-Zone": "Europe/London",  # we convert everything to gmt -> no need to handle timezones
}

ALREADY_COMPRESSED_CONTENT_TYPES: List[str] = [
    "application/gzip",
    "application/octet-stream",
    "application/zip",
]
ALREADY_COMPRESSED_FILE_EXTENSIONS: List[str] = [
    "zip",
    "gz",
    "bz",
    "jar",
    "cbz",
    "7z",
    "rar",
    "sitx",
]


class GithubRepoBackuper:
    def __init__(
        self,
        repo_owner: str = "",  # = "" makes **args possible without linting issues
        repo_name: str = "",
        prune: bool = False,
        detailed_prs: bool = False,
        include_lfs: bool = False,
        include_releases: bool = False,
        include_wiki: bool = False,
        gzip: bool = False,
        last_backup: Optional[str] = None,
    ) -> None:
        assert repo_owner != "" and repo_name != ""
        logger.debug(f"created GithubRepoBackuper for {repo_owner}/{repo_name}")
        self._detailed_prs: bool = detailed_prs
        self._include_lfs: bool = include_lfs
        self._do_prune: bool = prune
        self._last_backup: Optional[str] = last_backup
        self._repo_name: str = repo_name
        self._repo_owner: str = repo_owner
        self._start_time: Optional[str] = None
        self._include_releases: bool = include_releases
        self._include_wiki: bool = include_wiki
        self._gzip = gzip

        if path.exists(path.join("github", repo_owner, repo_name, "ghrb.json")):
            logger.debug("found existing ghrb.json")
            with open(path.join("github", repo_owner, repo_name, "ghrb.json"), "r") as fp:
                ghrb = json.load(fp)
            if last_backup is None:
                self._last_backup = ghrb.get("last_backup")

    def start_backup(self) -> None:
        logger.info(f"Starting backup of {self._repo_owner}/{self._repo_name}")
        # better duplicate check than no check for a issue on next run
        self._start_time = _datetime_for_github()
        self._download_issues()
        self._download_git()
        if self._include_releases:
            self._download_releases()
        if self._include_wiki:
            self._download_git(wiki=True)
        with open(path.join("github", self._repo_owner, self._repo_name, "ghrb.json"), "w") as fp:
            json.dump({
                "last_backup": self._start_time,
            }, fp)

    def _download_issues(self) -> None:
        logger.info("Starting issue backuper")
        makedirs(path.join("github", self._repo_owner, self._repo_name, "issues"), exist_ok=True)
        # 100 per page is limit and the rate-limit counts requests, not requested data amount
        next: Optional[str] = f'https://api.github.com/repos/{self._repo_owner}/{self._repo_name}/issues?per_page=100'
        if self._last_backup is not None:
            next += f"&since={self._last_backup}"
        next += "&state=all"  # open is default
        while next is not None:
            resp: requests.Response = _gh_get(next)
            resp.raise_for_status()  # TODO: handle
            self._save_issues(resp.json())
            next = None
            try:
                for link_str in resp.headers["Link"].split(", "):
                    url, rel = link_str.split("; rel=", 1)
                    if rel == '"next"':
                        next = url[1:-1]  # cut < and >
            except Exception:  # key error, not a string, etc -> does not contain next
                return

    def _save_issues(self, parsed_json: List[Dict[str, Any]]) -> None:
        for issue in parsed_json:
            logger.debug(f"found issue: {issue['number']}")
            output_issue: Dict[str, Any] = {
                "active_lock_reason": issue.get("active_lock_reason"),
                "assignees": issue.get("assignees"),
                "author_association": issue.get("author_association"),
                "body": issue.get("body"),
                "closed_at": issue.get("closed_at"),
                "created_at": issue.get("created_at"),
                "draft": issue.get("draft"),
                "reactions": _prettify_reactions(issue.get("reactions")),
                "labels": [i["name"] for i in (issue.get("labels") or []) if "name" in i],
                "locked": issue.get("locked"),
                "state": issue.get("state"),
                "title": issue.get("title"),
                "user": issue.get("user", {}).get("login"),
                "comments": (_get_issue_comments(issue.get("comments_url")) if (issue.get("comments") or 0) > 0 else []),
                **({
                    "is_pull_request": True,
                    "merged_at": issue["pull_request"].get("merged_at"),
                } if "pull_request" in issue else {"is_pull_request": False}),
            }

            if self._detailed_prs and output_issue["is_pull_request"]:
                output_issue = {**output_issue, **_get_pr_details(issue.get("pull_request", {}).get("url"))}

            self.write_gzipable_json(
                path.join("github", self._repo_owner, self._repo_name, "issues", f"{issue['number']}.json"),
                output_issue,
            )
            # TODO: save user info if new

    def _download_git(self, wiki: bool = False) -> None:
        logger.info("backing up git..")
        dirname: str = "wiki" if wiki else "git"
        if path.exists(path.join("github", self._repo_owner, self._repo_name, dirname)):
            logger.info(f"incremental {'wiki ' if wiki else ''}git backup using fetch..")
            subprocess.run(
                ["git", "fetch", "--all", *(["--prune"] if self._do_prune else [])],
                cwd=path.join(path.curdir, "github", self._repo_owner, self._repo_name, dirname),
            )
        else:
            logger.info(f"initial {'wiki ' if wiki else ''}git backup using clone..")
            subprocess.run(
                [
                    "git", "clone", "--mirror",
                    f"https://github.com/{self._repo_owner}/{self._repo_name}{'.wiki' if wiki else ''}.git",
                    dirname
                ],
                cwd=path.join(path.curdir, "github", self._repo_owner, self._repo_name),
            )
        if self._include_lfs:
            logger.info(f"downloading {'wiki ' if wiki else ''}git-lfs")
            subprocess.run(
                ["git", "lfs", "fetch", "--all"],
                cwd=path.join(path.curdir, "github", self._repo_owner, self._repo_name, dirname),
            )

    def _download_releases(self) -> None:
        logger.info("Downloading releases")
        makedirs(path.join("github", self._repo_owner, self._repo_name, "releases"), exist_ok=True)
        # 100 per page is limit and the rate-limit counts requests, not requested data amount
        next: Optional[str] = f'https://api.github.com/repos/{self._repo_owner}/{self._repo_name}/releases?per_page=100'
        while next is not None:
            resp: requests.Response = _gh_get(next)
            resp.raise_for_status()  # TODO: handle
            self._save_releases(resp.json())
            next = None
            try:
                for link_str in resp.headers["Link"].split(", "):
                    url, rel = link_str.split("; rel=", 1)
                    if rel == '"next"':
                        next = url[1:-1]  # cut < and >
            except Exception:  # key error, not a string, etc -> does not contain next
                return

    def _save_releases(self, response_json: Any) -> None:
        for release in response_json:
            id: int = release["id"]
            output_release: Dict[str, Any] = {
                "tag_name": release.get("tag_name"),
                "name": release.get("name"),
                "is_draft": release.get("draft"),
                "is_prerelease": release.get("prerelease"),
                "created_at": release.get("created_at"),
                "published_at": release.get("published_at"),
                "body": release.get("body"),
                "reactions": _prettify_reactions(release.get("reactions")),
                "assets": [
                    {
                        "content_type": asset.get("content_type"),
                        "download_count": asset.get("download_count"),
                        "name": asset.get("name"),
                    } for asset in (release.get("assets") or [])
                ]
            }
            dir = path.join("github", self._repo_owner, self._repo_name, "releases", str(id))
            if path.exists(dir):
                continue
            makedirs(dir)
            self.write_gzipable_json(path.join(dir, "release.json"), output_release)
            for asset in release.get("assets", []):
                gz: bool = (
                    self._gzip
                    and asset["content_type"] not in ALREADY_COMPRESSED_CONTENT_TYPES
                    and asset['name'].rsplit(".", 1)[-1].lower() not in ALREADY_COMPRESSED_FILE_EXTENSIONS
                )
                _download_file(
                    asset["browser_download_url"],
                    path.join(dir, f"{asset['name']}.gz" if gz else asset["name"]),
                    gz
                )

    def write_gzipable_json(self, filepath: str, jsondata: Any) -> None:
        if self._gzip:
            with gzip.open(f"{filepath}.gz", "wt") as fp:
                json.dump(jsondata, fp)
        else:
            with open(filepath, "w") as fp:
                json.dump(jsondata, fp)


def _get_pr_details(url: Optional[str]) -> Dict[str, Any]:
    if url is None:
        return {}
    resp = _gh_get(url)
    resp.raise_for_status()  # TODO: handle
    pr = resp.json()
    return {
        "merge_commit_sha": pr.get("merge_commit_sha"),
        "requested_reviewers": pr.get("requested_reviewers"),
        "head": {
            "gh_repo": ((pr.get("head") or {}).get("repo") or {}).get("full_name"),
            "ref": (pr.get("head") or {}).get("ref"),
        },
        "base": (pr.get("base") or {}).get("ref"),
        "merged": pr.get("merged"),
        "merged_by": (pr.get("merged_by") or {}).get("login"),
    }


def _get_issue_comments(url: Optional[str]) -> List[Dict[str, Any]]:
    if url is None:
        return []
    output: List[Dict[str, Any]] = []
    resp = _gh_get(url)
    resp.raise_for_status()  # TODO: handle
    for comment in resp.json():
        output.append({
            "author_association": comment.get("author_association"),
            "body": comment.get("body"),
            "created_at": comment.get("created_at"),
            "updated_at": comment.get("updated_at"),
            "reactions": _prettify_reactions(comment.get("reactions")),
            "user": (comment.get("user") or {}).get("login"),
        })
    return output


def _prettify_reactions(reactions: Optional[Dict[str, Any]]) -> Dict[str, int]:
    """drops api-urls, and redundant info"""
    if not isinstance(reactions, dict):
        return {}
    return {k: v for k, v in reactions.items() if isinstance(v, int) and k != "total_count" and v > 0}


def _handle_ratelimit(resp: requests.Response) -> None:
    if resp.headers["X-RateLimit-Remaining"] == "0":
        # +10 in case the local clock is off by something
        sleep_seconds: int = int(resp.headers["X-RateLimit-Reset"]) - floor(time()) + 10
        logger.info(f"Hit ratelimet. waiting for reset (~{sleep_seconds // 60}mins)..")
        sleep(sleep_seconds)


def _datetime_for_github() -> str:
    return strftime("%Y-%m-%dT%H:%M:%SZ", gmtime())


def _gh_get(url: str) -> requests.Response:
    logger.debug(f"HTTP GET {url}")
    resp = requests.get(url, headers=GITHUB_HEADERS)
    _handle_ratelimit(resp)
    return resp


def _download_file(url: str, local_file: str, gzip_result: bool = False) -> None:
    """
    gzip_result will just gzip the result without questions.
        change the filename and check for duplicate compression at the other end.
    """
    # https://stackoverflow.com/a/16696317
    logger.debug(f"Downloading {url} to {local_file}")
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


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="github-repo-backuper",
        description="Back up a github repository",
    )
    parser.add_argument("repo_owner", help="Name of the repository owner. Example: torvalds")
    parser.add_argument("repo_name", help="Name of the repository. Example: linux")
    parser.add_argument("--prune", action="store_true", help="Prune the git repository if this is a increment.")
    parser.add_argument("--detailed-prs", action="store_true", help="Store detailed PR information.")
    parser.add_argument("--include-lfs", action="store_true", help="Include git-lfs (requires git-lfs to be installed).")
    parser.add_argument("--include-releases", action="store_true", help="include github releases.")
    parser.add_argument("--include-wiki", action="store_true", help="include github wiki.")
    parser.add_argument("--gzip", action="store_true", help="gzip files whereever possible to reduce filesize.")
    args = parser.parse_args()._get_kwargs()
    del parser
    logger.debug("arguments: " + "; ".join({f"{k}: {v}" for k, v in args}))
    GithubRepoBackuper(**{k: v for k, v in args}).start_backup()


if __name__ == "__main__":
    main()
