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

- **master**: This is the deployment branch, direct push are blocked for both admin and regular members. Ideally, code contained in this branch should be the least error-prone.
- **dev**: This is the development branch where all changes are integrated together before being merged into master. Admin of the repo can push to this branch. *Only push directly here if it is a small codestyle fix*.
- **Feature/Issue branches**: Anytime you want to work on resolving an issue or implementing a new feature, you should branch off of the `dev` branch into one of these branches. Name the branch `issue-x` where `x` is the issue number with the issue you are trying to resolve/feature you are trying to implement. You can be more descriptive so other people know what exactly you are working on. Example: `issue-42` or `issue-30/paginator` are both acceptable.

### Pull requests

When you have finished your task and pushed your work to the corresponding branch on remote, you can create a pull request via Github web interface to integrate your code into production. Remember the difference between `master` and `dev` to choose the destination branch. After creating a pull request, you should ask at least 1 person to review your work and update it accordingly. If your pull request is approved, changes will be applied to the destination branch, and the feature/enhancement will be deployed eventually.

