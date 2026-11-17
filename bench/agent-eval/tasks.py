FMT = ("When you are done, end your reply with exactly one final line in this form: "
       "ANSWER: repo1, repo2, ... (folder names, sorted alphabetically), or ANSWER: none")
INTRO = "The current folder contains 20 git repositories, one per subfolder. "
TASKS = {
 "T01_dirty":   "Which repositories have uncommitted changes (modified, staged or untracked files)?",
 "T02_behind":  "Fetch from origin in every repository. After fetching, which repositories are behind their upstream branch?",
 "T03_tests":   "Every repository has a ./ci.sh script that runs its tests. Run it in every repository. Which repositories' tests fail (non-zero exit code)?",
 "T04_branch":  "Which repositories currently have a branch checked out other than main or master?",
 "T05_ahead":   "Which repositories have local commits that have not been pushed to their upstream branch?",
 "T06_node":    "Which repositories declare a minimum Node.js version below 20 in the engines.node field of their own package.json?",
 "T07_dep":     "Which repositories list the package tsd in dependencies, devDependencies or peerDependencies of their own package.json?",
 "T08_todo":    "For each repository, count the lines that contain the exact text TODO (case-sensitive) in its git-tracked files. ",
 "T09_license": "Which repositories have no license file in their root folder? A license file is any file whose name starts with LICENSE, LICENCE or COPYING, in any letter case.",
 "T10_touch":   "Create an empty file named .bench-ok in the root folder of every Python repository (a repository that has a pyproject.toml or setup.py in its root folder). Do not create it anywhere else. Then list the repositories where you created it.",
}
FMT_COUNTS = ("Report every repository whose count is above zero. When you are done, end your reply with exactly one final line in this form: "
              "ANSWER: repo1=count1, repo2=count2, ... (sorted alphabetically by folder name)")
def prompt(t):
    return INTRO + TASKS[t] + " " + (FMT_COUNTS if t == "T08_todo" else FMT)

# Tier 2: compound tasks (added after tier 1 hit the ceiling on Sonnet 5.5; same harness, same arms)
TASKS2 = {
 "H1_pull_test": "Fetch from origin in every repository. Fast-forward every repository that is behind its upstream branch (do not change any other repository). Then run ./ci.sh in every repository you updated. Which of the updated repositories have failing tests (non-zero exit code)?",
 "H2_fail_dirty": "Every repository has a ./ci.sh script that runs its tests. Which repositories both have failing tests (non-zero exit code from ./ci.sh) and have uncommitted changes (modified, staged or untracked files)?",
 "H3_ahead_behind": "Fetch from origin in every repository. Then, for each repository that has an upstream branch configured, find how many commits it is ahead of and behind its upstream branch. ",
 "H4_commit_readme": "Some repositories have uncommitted edits to a tracked README file. In every repository where a tracked README file is modified, commit only that README change with the message \"docs: wip\". Do not commit anything else and do not change any other repository. Then list the repositories where you made a commit.",
}
FMT_AB = ("Report every repository where either number is above zero. When you are done, end your reply with exactly one final line in this form: "
          "ANSWER: repo1=ahead/behind, repo2=ahead/behind, ... (sorted alphabetically by folder name, for example ANSWER: foo=1/0, bar=0/3)")
TASKS.update(TASKS2)
_prompt1 = prompt
def prompt(t):
    if t == "H3_ahead_behind": return INTRO + TASKS[t] + " " + FMT_AB
    return _prompt1(t)

# Round 2 (skill eval): new tasks. D* = dev split, O* = held-out split, N* = single-repo negative controls.
TASKS3 = {
 "D_govet": "Run go vet ./... in every Go repository (a repository with a go.mod file or .go files in its root folder). Which repositories fail (non-zero exit code)?",
 "N_branch": "What branch is currently checked out in the go-humanize repository? End your reply with exactly one final line in this form: ANSWER: branch-name",
 "O_jstests": "Every repository has a ./ci.sh script that runs its tests. Run it in every JavaScript repository (a repository with a package.json in its root folder). Which of them fail (non-zero exit code)?",
 "O_pytests": "Every repository has a ./ci.sh script that runs its tests. Run it in every Python repository (a repository with a pyproject.toml or setup.py in its root folder). Which of them fail (non-zero exit code)?",
 "N_toolz": "In the toolz repository, run ./ci.sh. How many tests passed? End your reply with exactly one final line in this form: ANSWER: number",
}
TASKS.update(TASKS3)
_prompt2 = prompt
def prompt(t):
    if t in ("N_branch", "N_toolz"): return INTRO + TASKS[t]
    return _prompt2(t)
SPLITS = {"dev": ["T03_tests", "D_govet", "H2_fail_dirty", "T02_behind", "N_branch"],
          "heldout": ["O_jstests", "O_pytests", "H1_pull_test", "H3_ahead_behind", "T01_dirty", "N_toolz"]}
PARALLEL_TASKS = {"T03_tests", "D_govet", "H2_fail_dirty", "O_jstests", "O_pytests", "H1_pull_test"}
