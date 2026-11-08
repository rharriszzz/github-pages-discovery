# Python setup (WSL2, Linux, macOS and Windows)

As of **November 2026**, CPython **3.15** (recommended for new setups) and
**3.14** are the stable versions receiving regular bug-fix releases. Python
3.11–3.13 still receive security updates but no longer receive routine bug
fixes. Python 3.10 reached end of life in October 2026.

Check the current status at the
[official Python version table](https://devguide.python.org/versions/) and
[Python downloads](https://www.python.org/downloads/). Update the recommendation
when the maintenance status changes, rather than accumulating obsolete version
numbers in the README or CI workflow.

The project's public features and local research storage use only the Python
standard library. The optional live YouTube integration has dependencies in
[`requirements-youtube.txt`](../requirements-youtube.txt).

## WSL2 Ubuntu, Linux and macOS

**Do not replace Ubuntu's `/usr/bin/python3`.** For example, Ubuntu 22.04's
default Python is 3.10, now end-of-life, even though it is still needed by
Ubuntu's own tools.

For an existing Python 3.15 (or 3.14) installation, you can create a normal
virtual environment:

```bash
python3.15 -m venv .venv
source .venv/bin/activate
python3 --version  # Python 3.15.x
```

If your operating system does not supply a current interpreter, use
[`uv`](https://docs.astral.sh/uv/getting-started/installation/) to install it
without changing the system Python. Install `uv` by following its official
installation instructions, then run from the repository directory:

```bash
uv python install 3.15
uv venv --seed --python 3.15 .venv
source .venv/bin/activate
python3 --version  # Python 3.15.x
```

You can use `3.14` in place of `3.15`; CI tests both stable series.
The `--seed` option installs `pip` in the virtual environment for the
optional YouTube packages. It is not needed for standard-library-only tasks.

From the same activated shell, the commands in the README work unmodified:

```bash
python3 -m pagefinder stats
python3 -m unittest discover -s tests -v
```

Alternatively, run `.venv/bin/python -m ...` to select the project interpreter
explicitly, without activating the environment. A new shell requires
reactivating the environment or using that explicit path.

## Native Windows (PowerShell)

Use a current Python from [Python.org](https://www.python.org/downloads/windows/)
or install it through `uv` as described above. If using `uv`, from the
repository directory run:

```powershell
uv python install 3.15
uv venv --seed --python 3.15 .venv
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

On Windows, use `.\.venv\Scripts\python.exe` for commands in place of
`python3` if you have not activated the environment.

## Keeping the environment current

Install the latest **patch** release of the chosen maintained series and
periodically check the [CPython maintenance table](https://devguide.python.org/versions/).
If using a `uv`-managed interpreter, `uv python upgrade 3.15` upgrades that
series. Recreate your project virtual environment if necessary to pick up a
new interpreter, then reinstall only the optional packages you use:

```bash
.venv/bin/python -m pip install -r requirements-youtube.txt
```

This is an **environment recommendation**, not a claim that older Python
versions cannot run the code. CI covers 3.14 and 3.15; the checked-in work
does not require users to install prerelease versions.
