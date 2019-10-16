# Contributing to Canary

Hey, thank you for expressing interest in our project!

Canary is a Discord chat bot, maintained by a small group of students from McGill University; as such, all kinds of contribution to improving our repository are more than welcome. Feel free to send us a message [on Discord](https://discordapp.com/invite/HDHvv58) if you have any question.

The following document contains a set of guidelines for contributing to Canary. This is the place to start if you are looking to open your first issue, or submit a pull request. There is a few things that everyone should follow in order to keep the repo organized and free of bugs:

## Development workflow

### Github issues

Github provides a user-friendly interface for managing issues for a repository. We often use it to discuss new ideas, improvements or bugs. A few things you can do with the issue tracking feature:
- Bring up your novel ideas: Have something in mind that you believe can make the chat bot more powerful? Have a suggestion regarding marty's (how we name the chat bot on McGill discord server) performance? Let us know ASAP! We provide templates that make it easier for you to file an issue.
- Find something to work on: Resolving open issues is an easy way to get involved in the development of Canary and is what our maintainers spend a lot of time on. We assign a `good first issue` label for anything we feel can be a good starting point for new members. Don't want to write code? You can still participate in the discussions.

### Git branches

- **dev**: This is the development branch where all changes are integrated together before being merged into master. You should fork your issue branch from here, and make your PR to merge with this branch. *While technically possible for admins, pushing directly to this branch is strictly forbidden.* Small codestyle and spelling fixes should be committed to the `task/cleanup` branch, and a PR made from there. Once that PR is merged, `task/cleanup` is **NOT** deleted.
- **master**: This is the deployment branch, direct push are blocked for both admin and regular members. Ideally, code contained in this branch should be the least error-prone.
- **Feature/Issue branches**: Anytime you want to work on resolving an issue or implementing a new feature, branch off of the `dev` branch into one of these branches. Name the branch `issue-x` where `x` is the issue number with the issue you are trying to resolve/feature you are trying to implement. You can be more descriptive so other people know what exactly you are working on. Example: `issue-42` or `issue-30/paginator` are both acceptable.

### Pull requests

When you have finished your task and pushed your work to the corresponding branch on remote, you can create a pull request via Github web interface to integrate your code into production. By default, your PR should be requesting to merge into `dev` -- however, it's good practice to check that this is indeed the case before you submit your PR. After creating a pull request, you should ask at least 1 person to review your work and update it accordingly. If your pull request is approved, changes will be applied to the destination branch, and the feature/enhancement will be deployed eventually.

### Reviewing PRs

- Go through the code line-by-line to see what was changed. A good way to do this in-browser is to click the `Files changed` tab.
- Comment on relevant lines. You can click the plus (+) next to individual lines or click and drag to select multiple lines for a single comment.
- Consider creating your own local branch that tracks the same PR branch on `origin`, to test the changes yourself. You can do this by first running `git fetch` then `git checkout -b issue-XX` on your machine. Once you're done and the PR has been merged, checkout locally to your `dev` branch, run `git pull` and delete the issue branch with `git branch -d issue-XX`.
- Provide constructive criticism on the code. You don't have to restrict yourself to things to fix -- this is an excellent opportunity to compliment good design choices, new concepts you're seeing for the first time, etc.!
- Ensure that the changes are understandable by a newcomer to the project. The writer of the code will have their own familiarity with the code since they've built it from their own mental model. As reviewer, consider yourself to be 1 degree removed from that mental model, and be liberal about asking for clarification on changes you don't understand! (This is a 2-way street: submitters should also be responsive to questions and suggestions.)
- Don't be afraid to request changes. It's ok if it's blocking the merge. If the submitter is not willing to make changes, try to come to an agreement in the comment thread. You're not always going to agree, but in the end, the feature has to be implemented.
