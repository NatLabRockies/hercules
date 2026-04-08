# Contributing to Hercules

We welcome contributions in the form of bug reports, bug fixes, improvements to the documentation,
ideas for enhancements (or the enhancements themselves!).

You can find a [list of current issues](https://github.com/NatLabRockies/hercules/issues) in the project's
GitHub repo. Feel free to tackle any existing bugs or enhancement ideas by submitting a
[pull request](https://github.com/NatLabRockies/hercules/pulls).


## Pull Requests
If you'd like to contribute code through a pull request, please read the following guidance:
* Please reference relevant GitHub issues in your commit message using `GH123` or `#123`.
* Changes should be [PEP8](http://www.python.org/dev/peps/pep-0008/) compatible.
* Keep style fixes to a separate commit to make your pull request more readable.
* Docstrings are required and should follow the
  [Google style](https://www.sphinx-doc.org/en/master/usage/extensions/example_google.html).
* When you start working on a pull request, start by creating a new branch pointing at the latest
  commit on [develop](https://github.com/NatLabRockies/hercules/tree/develop).
* Code formatting is enforced using pre-commit hooks and is required for any code pushed up to the repository. The pre-commit package is included in the developer install of the repository. The pre-commit hooks can be installed by running
```bash
pre-commit install
```
in the repository directory. This will automatically run the pre-commit formatting hooks when code changes are committed. If you are having difficulty committing code after it has been reformatted by these hooks, try using the commit command
```bash
git commit -am "<Your commit message here>"
```
which will re-add the reformatted files to the commit.
If changes are required, follow the suggested fix or resolve the stated issue(s). Restaging and committing may take multiple attempts steps if errors are unaddressed or insufficiently addressed. Please see [pre-commit](https://pre-commit.com/),
[ruff](https://docs.astral.sh/ruff/), or [isort](https://pycqa.github.io/isort/) for more information.
* The Hercules copyright policy is detailed in the [`LICENSE`](https://github.com/NatLabRockies/hercules/blob/main/LICENSE.txt).
