use nulib/webserver.nu format_http
use nulib/webserver.nu start_webserver
use nulib/webserver.nu http_redirect
use nulib/nutils/html.nu

const JSON = "application/json;charset=UTF-8"
const HTML = "text/html;charset=UTF-8"

const HTML_HEAD = ([
  '<!DOCTYPE HTML><html><head>'
  '<style>'
  'html {background-color:wheat;}'
  'pre {background-color:lightgray;border-radius:15px;padding:15px;white-space:pre-wrap;}'
  'span.label {padding:5px;border-radius:5px;margin-left:2px;}'
  'table.issues td {border-top:1px solid black;padding:7px;}'
  'div.reactions>span {background-color:gray;border-radius:2px;padding:2px;margin-left:2px;color:white;}'
  'div.comment {border:1px solid black;border-radius:15px;padding:15px;margin:5px;}'
  '</style>'
  '<title>GitHub-repo-backuper viewer</title>'
  '</head><body>'
] | str join "")
const HTML_TAIL = ([
  '</body></html>'
] | str join "")


def main [
  --port: int = 8080
] {
  start_webserver $port {|req|
    if $req.path == "/" {return (http_redirect "/index.html")}
    if $req.path == ("/github") {return (generate_landingpage)}
    if $req.path =~ "^/github/[^/]+$" {return (generate_userpage $req)}
    if $req.path =~ "^/github/[^/]+/[^/]+$" {return (generate_repopage $req)}
    if $req.path =~ "^/github/[^/]+/[^/]+/issues$" {return (generate_issue_list $req)}
    if $req.path =~ '^/github/[^/]+/[^/]+/issues/\d+$' {return (generate_issue_details $req)}
    if $req.path =~ "^/github/[^/]+/[^/]+/releases$" {return (generate_release_list_page $req)}
    if $req.path =~ '^/github/[^/]+/[^/]+/releases/\d+$' {return (generate_release_details_page $req)}
    format_http 404 $HTML ([$HTML_HEAD '<h1>Page not found</h1><a href="/github">Go Home</a>' $HTML_TAIL] | str join '')
  }
}


def generate_landingpage []: nothing -> string {
  if (not ($'github' | path exists)) {return (format_http 404 $HTML "Nothing found. no users, no repos, nothing.")}
  format_http 200 $HTML ([
    $HTML_HEAD
    "<h1>GitHub repo backuper results</h1>"
    "<h2>Users and Orgs</h2><ul>"
    ((ls github/).name | sort | each {|i| $'<li><a href="/(html escape $i)">(html escape $i)</a></li>'} | str join '')
    "</ul>"
    $HTML_TAIL
  ] | str join "")
}


def generate_userpage [req]: nothing -> string {
  let user = ($req.path | parse "/github/{user}").0.user
  if $user !~ "^[a-zA-Z0-9_-]+$" {return (format_http 300 $HTML "Invalid user name")}
  if (not ($'github/($user)' | path exists)) {return (format_http 404 $HTML "User not found")}
  format_http 200 $HTML ([
    $HTML_HEAD
    $'<h1>/<a href="/github">github</a>/(html escape $user)</h1>'
    '<h2>Repos</h2><ul>'
    ((ls $"github/($user)").name | sort | each {|i| $'<li><a href="/(html escape $i)">(html escape $i)</a></li>'} | str join '')
    '</ul>'
    $HTML_TAIL
  ] | str join '')
}

def generate_repopage [req]: nothing -> string {
  let rp = ($req.path | parse "/github/{user}/{repo}").0
  if $rp.user !~ "^[a-zA-Z0-9_-]+$" {return (format_http 300 $HTML "Invalid user name")}
  if $rp.repo in ["..", "."] {return (format_http 300 $HTML "Invalid repo name")}  # "/" is already filter by mapper
  if (not ($'github/($rp.user)/($rp.repo)/git' | path exists)) {return (format_http 404 $HTML "Repo not found")}

  cd $'github/($rp.user)/($rp.repo)/git'

  let files = (^git ls-tree --name-only -r HEAD | lines)  # "  <-- quote fixes treesitter for line below (dont ask me)
  let readme_name = ($files | where ($it | str starts-with 'README')).0?

  format_http 200 $HTML ([
    $HTML_HEAD
    $'<h1>/<a href="/github">github</a>/<a href="/github/(html escape $rp.user)">(html escape $rp.user)</a>/(html escape $rp.repo)</h1>'

    (if ("../issues" | path exists) {$'<a href="(html escape $req.path)/issues">Issues</a> '})
    (if ("../releases" | path exists) {$'<a href="(html escape $req.path)/releases">Releases</a> '})

    (if $readme_name != null {$'<h2>(html escape $readme_name)</h2><details><summary>toggle</summary><pre>(html escape (^git show -q $"HEAD:($readme_name)"))</pre></details>'} else {""})

    $'<h2>Files</h2><details><summary>toggle</summary><ul>'
    ($files | each {|i| $'<li>(html escape $i)</li>'} | str join '')  # TODO: replace with line below once file-viewer (incl images?) is implemented
    #($files | each {|i| $'<li><a href="(html escape $req.path)/files/(html escape $i)">(html escape $i)</a></li>'} | str join '')
    '</ul></details>'

    # TODO: releae list

    $HTML_TAIL
  ] | str join '')
}

def generate_issue_list [req]: nothing -> string {
  let rp = ($req.path | parse "/github/{user}/{repo}/issues").0
  if $rp.user !~ "^[a-zA-Z0-9_-]+$" {return (format_http 300 $HTML "Invalid user name")}
  if $rp.repo in ["..", "."] {return (format_http 300 $HTML "Invalid repo name")}  # "/" is already filter by mapper

  if (not ($'github/($rp.user)/($rp.repo)/issues' | path exists)) {return (format_http 404 "text/plain;charset=utf-8" $"dir not found: github/($rp.user)/($rp.repo)/issues")}
  cd $'github/($rp.user)/($rp.repo)/issues'

  format_http 200 $HTML ([
    $HTML_HEAD
    $'<h1>/<a href="/github">github</a>/<a href="/github/(html escape $rp.user)">(html escape $rp.user)</a>/<a href="/github/(html escape $rp.user)/(html escape $rp.repo)">(html escape $rp.repo)</a>/issues</h1>'

    '<table class="issues"><tr><th>Id</th><th></th><th></th><th>Name</th><th>Author</th><th></th></tr>'
    ((ls).name | sort --natural | each {|filename|
      let data = (if ($filename | str ends-with ".json.gz") {^gunzip -kc $filename | from json} else if ($filename | str ends-with ".json") {open $filename} else {null})
      let issue_id = ($filename | split row "." | get 0)
      if $data == null {""} else {[
        $'<tr><td><a href="(html escape $req.path)/(html escape $issue_id)">(html escape $issue_id)</a></td>'
        $'<td>(if $data.is_pull_request? == true {"📥"} else {"📌"})</td>'
        $'<td>(if $data.state? == "closed" {"🟣"} else {"🟢"})</td>'
        $'<td>(html escape ($data.title? | default "<no title>"))'
        ($data.labels? | default [] | each {|label|
          if ($label | describe) == "string" {
            $'<span class="label" style="background-color:#00ff00">(html escape $label)</span>'
          } else {
            let fc = (if (isDarkColor ($label.color? | default '0a0')) {"fff"} else {"000"})
            $'<span class="label" style="background-color:#(html escape ($label.color? | default '0a0')); color:#($fc)">(html escape ($label.name? | default ""))</span>'
          }
        } | str join '')
        '</td>'
        $'<td>(html escape ($data.user? | default "<no author>"))</td>'
        $'<td>💬($data.comments? | default [] | length)</td></tr>'
      ] | str join ''}
    } | str join "")
    '</table>'

    $HTML_TAIL
  ] | str join "")
}

def generate_issue_details [req]: nothing -> string {
  let rp = ($req.path | parse "/github/{user}/{repo}/issues/{issue}").0
  if $rp.user !~ "^[a-zA-Z0-9_-]+$" {return (format_http 300 $HTML "Invalid user name")}
  if $rp.repo in ["..", "."] {return (format_http 300 $HTML "Invalid repo name")}  # "/" is already filter by mapper
  if $rp.issue !~ '^\d+$' {return (format_http 300 $HTML "Invalid issue id (not a number)")}
  let issue_file = (if ($'github/($rp.user)/($rp.repo)/issues/($rp.issue).json' | path exists) {$'github/($rp.user)/($rp.repo)/issues/($rp.issue).json'} else {$'github/($rp.user)/($rp.repo)/issues/($rp.issue).json.gz'})
  if (not ($issue_file | path exists)) {return (format_http 404 "text/plain;charset=utf-8" $"Unknown issue")}
  let data = (if ($issue_file | str ends-with ".json.gz") {^gunzip -kc $issue_file | from json} else if ($issue_file | str ends-with ".json") {open $issue_file} else {null})

  format_http 200 $HTML ([
    $HTML_HEAD
    $'<h1>/<a href="/github">github</a>/<a href="/github/(html escape $rp.user)">(html escape $rp.user)</a>/<a href="/github/(html escape $rp.user)/(html escape $rp.repo)">(html escape $rp.repo)</a>/<a href="/github/(html escape $rp.user)/(html escape $rp.repo)/issues">issues</a>/($rp.issue)</h1>'
    $'<h2>(html escape ($data.title? | default "<no name>"))</h2>'
    ($data.labels? | default [] | each {|label|
      if ($label | describe) == "string" {
        $'<span class="label" style="background-color:#00ff00">(html escape $label)</span>'
      } else {
        let fc = (if (isDarkColor ($label.color? | default '0a0')) {"fff"} else {"000"})
        $'<span class="label" style="background-color:#(html escape ($label.color? | default '0a0')); color:#($fc)">(html escape ($label.name? | default ""))</span>'
      }
    } | str join '')
    $'<p>Author: (format_username $data.user? $data.author_association?)</p>'
    (if $data.draft? == true {"<p>This is a draft</p>"} else {""})
    (if $data.locked? == true {"<p>This is locked</p>"} else {""})
    (if $data.state? != null {$"<p>State: (html escape $data.state)</p>"})
    (if ($data.assignees? | default []) != [] {$'<p>Assignees: (html escape ($data.assignees? | default [] | get login | str join ", "))</p>'} else {""})

    # MR data
    # TODO: requested reviewers
    (if $data.merge_commit_sha? != null {$'<p>Merge Commit SHA: (html escape $data.merge_commit_sha)</p>'} else {''})
    (if $data.head? != null {$'<p>FROM <code>(html escape ($data.head.gh_repo? | default "<unknown repo>")):(html escape ($data.head.ref? | default "<unknown ref>"))</code> TO <code>(html escape ($data.base? | default "<unknown target branch>"))</code></p>'})
    (if $data.merged? == true {$'<p>Merged at (html escape ($data.merged_at? | default "<unknown>")) by (html escape ($data.merged_by? | default "<unknown>"))</p>'})

    $'<pre>(html escape ($data.body? | default "<no body>"))</pre>'

    $'created: (html escape ($data.created_at? | default "<unknown>")) updated: (html escape ($data.updated_at? | default "<unknown>"))'

    (format_reactions $data.reactions?)

    '<div class="issue-comments">'
    ($data.comments? | default [] | each {|comment|
      [
        '<div class="comment">'
        $'<b>(format_username $comment.user? $comment.author_association?)</b>'
        $'<pre>(html escape ($comment.body? | default "<no body>"))</pre>'
        $'created: (html escape ($comment.created_at? | default "<unknown>")) updated: (html escape ($comment.updated_at? | default "<unknown>"))'
        (format_reactions $comment.reactions?)
        '</div>'
      ] | str join ''
    } | str join '')
    '</div>'

    $HTML_TAIL
  ] | str join "")
}

def generate_release_list_page [req]: nothing -> string {
  let rp = ($req.path | parse "/github/{user}/{repo}/releases").0
  if $rp.user !~ "^[a-zA-Z0-9_-]+$" {return (format_http 300 $HTML "Invalid user name")}
  if $rp.repo in ["..", "."] {return (format_http 300 $HTML "Invalid repo name")}  # "/" is already filter by mapper
  if (not ($"github/($rp.user)/($rp.repo)/releases" | path exists)) {return (format_http 404 "text/plain;charset=utf-8" $"Repo has no releases or does not exist")}
  cd $'github/($rp.user)/($rp.repo)/releases'

  format_http 200 $HTML ([
    $HTML_HEAD
    $'<h1>/<a href="/github">github</a>/<a href="/github/(html escape $rp.user)">(html escape $rp.user)</a>/<a href="/github/(html escape $rp.user)/(html escape $rp.repo)">(html escape $rp.repo)</a>/releases</h1>'
    '<ul>'
    ((ls --short-names).name | each {|release_id|
      let details_file = (if ($'($release_id)/release.json' | path exists) {$'($release_id)/release.json'} else {$'($release_id)/release.json.gz'})
      let data = (if ($details_file | str ends-with ".json.gz") {^gunzip -kc $details_file | from json} else if ($details_file | str ends-with ".json") {open $details_file} else {null})

      [
        $'<li><a href="(html escape $req.path)/($release_id)">'
        (if $data.is_draft {html escape '<DRAFT>'} else {''})
        (if $data.is_prerelease {html escape '<PRERELEASE>'} else {''})
        (html escape $data.name)
        '</a></li>'
      ] | str join ''
    } | str join '')
    '</ul>'
    $HTML_TAIL
  ] | str join '')
}

def generate_release_details_page [req]: nothing -> string {
  let rp = ($req.path | parse "/github/{user}/{repo}/releases/{id}").0
  if $rp.user !~ "^[a-zA-Z0-9_-]+$" {return (format_http 300 $HTML "Invalid user name")}
  if $rp.repo in ["..", "."] {return (format_http 300 $HTML "Invalid repo name")}  # "/" is already filter by mapper
  if $rp.id !~ '^\d+$' {return (format_http 300 $HTML "Invalid release id (not a number)")}
  if (not ($"github/($rp.user)/($rp.repo)/releases" | path exists)) {return (format_http 404 "text/plain;charset=utf-8" $"Repo has no releases or does not exist")}
  let release_file = (if ($'github/($rp.user)/($rp.repo)/releases/($rp.id).json' | path exists) {$'github/($rp.user)/($rp.repo)/releases/($rp.id)/release.json'} else {$'github/($rp.user)/($rp.repo)/releases/($rp.id)/release.json.gz'})
  if (not ($release_file | path exists)) {return (format_http 404 "text/plain;charset=utf-8" $"Unknown release")}
  let data = (if ($release_file | str ends-with ".json.gz") {^gunzip -kc $release_file | from json} else if ($release_file | str ends-with ".json") {open $release_file} else {null})

  format_http 200 $HTML ([
    $HTML_HEAD
    $'<h1>/<a href="/github">github</a>/<a href="/github/(html escape $rp.user)">(html escape $rp.user)</a>/<a href="/github/(html escape $rp.user)/(html escape $rp.repo)">(html escape $rp.repo)</a>/<a href="(html escape $rp.user)/(html escape $rp.repo)/releases">releases</a>/(html escape $rp.id)</h1>'

    '<h2>'
    (if $data.is_draft {html escape '<DRAFT>'} else {''})
    (if $data.is_prerelease {html escape '<PRERELEASE>'} else {''})
    (html escape $data.name)
    '</h2>'

    (if ("created_at" in $data) {$' created at (html escape $data.created_at)'} else {''})
    (if ("published_at" in $data) {$' published at (html escape $data.published_at)'} else {''})
    (if ("body" in $data) {$'<pre>(html escape $data.body)</pre>'} else {''})
    (if ("reactions" in $data) {format_reactions $data.reactions} else {''})

    (if ("assets" in $data) {[
      '<h3>Assets</h3><table>'
      ($data.assets | each {|asset|
        $'<tr><td>💾($asset.download_count)</td><td>(html escape $asset.name)</td></tr>'
      } | str join '')
      '</table>'
    ] | str join ''} else {})

    $HTML_TAIL
  ] | str join '')
}

const REACTION_NAME_TO_EMOTE = {
  # https://docs.github.com/en/rest/reactions/reactions
  "+1": "👍"
  "-1": "👎"
  "laugh": "😄"
  "confused": "😕"
  "heart": "❤️"
  "hooray": "🎉"
  "rocket": "🚀"
  "eyes": "👀"
}
def format_reactions [reactions] {
  [
    '<div class="reactions">'
    ($reactions
      | default {}
      | transpose k v
      | update k {|i| $REACTION_NAME_TO_EMOTE | get $i.k? | default $i.k? | default "?"}
      | each {|i| $'<span>(html escape $i.k) ($i.v)</span>'}
      | str join ''
    )
    '</div>'
  ] | str join ''
}
def format_username [name, association]: nothing -> string {
  if $association in [null, "NONE"] {return (html escape ($name | default "<no name>"))}
  $'(html escape ($name | default "<no name>")) [(html escape $association)]'
}

def isDarkColor [color: string] {
  # non hex -> idk -> false
  if $color !~ "[0-9a-f]{3,8}" {return false;}
  # remove alpha
  let color = (if ($color | str length) == 4 {$color | str substring 0..2} else {$color})
  let color = (if ($color | str length) == 8 {$color | str substring 0..5} else {$color})
  # 3 -> 6
  let color = (if ($color | str length) == 3 {let a = ($color | split chars); $"($a.0)($a.0)($a.1)($a.1)($a.2)($a.2)"} else {$color})
  let color = $"($color)0000"  # better than indexOutOfRange error
  let r = ($color | str substring 0..1 | into int --radix 16)
  let g = ($color | str substring 2..3 | into int --radix 16)
  let b = ($color | str substring 4..5 | into int --radix 16)
  let luminance = (($r * 0.299 + $g * 0.587 + $b * 0.114) / 256)
  return ($luminance < 0.5)
}
