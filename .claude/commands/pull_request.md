# Create Pull Request / Merge Request

Based on the `Instructions` below, take the `Variables` follow the `Run` section to create a pull request (GitHub) or merge request (GitLab). Then follow the `Report` section to report the results of your work.

## Variables

branch_name: $ARGUMENT
issue: $ARGUMENT
plan_file: $ARGUMENT
adw_id: $ARGUMENT

## Instructions

- Generate a title in the format: `<issue_type>: #<issue_number> - <issue_title>`
- The body should include:
  - A summary section with the issue context
  - Link to the implementation `plan_file` if it exists
  - Reference to the issue (Closes #<issue_number>)
  - ADW tracking ID
  - A checklist of what was done
  - A summary of key changes made
- Extract issue number, type, and title from the issue JSON
- Examples of titles:
  - `feat: #123 - Add user authentication`
  - `bug: #456 - Fix login validation error`
  - `chore: #789 - Update dependencies`
  - `test: #1011 - Test xyz`
- Don't mention Claude Code in the body - let the author get credit for this.

## Run

1. Run `git diff origin/main...HEAD --stat` to see a summary of changed files
2. Run `git log origin/main..HEAD --oneline` to see the commits that will be included
3. Run `git diff origin/main...HEAD --name-only` to get a list of changed files
4. Detect the issue tracker provider:
   - Check if `ADW_PROVIDER` env var is set ("github" or "gitlab")
   - If not set, check if a `gitlab` git remote exists (`git remote get-url gitlab`)
   - If gitlab remote exists, use GitLab. Otherwise, use GitHub.
5. Push the branch:
   - **GitHub**: `git push -u origin <branch_name>`
   - **GitLab**: `git push -u gitlab <branch_name>`
6. Create the MR/PR:
   - **GitHub**: Set GH_TOKEN from GITHUB_PAT if available, then run `gh pr create --title "<title>" --body "<body>" --base main`
   - **GitLab**: Run `glab mr create --title "<title>" --description "<body>" --target-branch main -R <repo_path> --yes`
7. Capture the URL from the output

## Report

Return ONLY the MR/PR URL that was created (no other text)
