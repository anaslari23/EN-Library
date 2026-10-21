# EN-Library release checklist

The GitHub feature branch is installable with `python3 -m pip install git+https://github.com/anaslari23/EN-Library.git@feat/en-architecture`. A plain `pip install codeinenglish` requires a separate PyPI publication and is not promised by this repository state.

Before publishing a package version:

1. Choose the release commit, version, project description, license, and public package name. Verify the chosen name is available and that both `pyproject.toml` and `build_backend.py` contain the same version.
2. Run `python3 -m unittest discover -s tests -q` with each claimed Python version and run the paired `en-language/scripts/verify_library.py` against a fresh install. The current checked environments are Python 3.10, 3.11, 3.12, 3.13, and 3.14.
3. Build a wheel with `python3 -m pip wheel --no-deps --no-build-isolation . -w dist`, inspect its `codeinenglish/*.py`, `METADATA`, `WHEEL`, `entry_points.txt`, and `RECORD`, then install that exact wheel in a fresh virtual environment outside the checkout.
4. Check that generation works with the network disconnected. Run Python and JavaScript examples. JavaScript generation needs no Node.js; executing generated JavaScript does.
5. Publish only the reviewed wheel, record its hash and release tag, and update installation instructions after confirming the published package resolves to the intended project. Publication is a separate release action.
