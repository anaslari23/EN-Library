# EN-Library release checklist

The GitHub feature branch is installable with `python3 -m pip install git+https://github.com/anaslari23/EN-Library.git@feat/en-architecture`. The distribution is named `en` (`pip install en`, once published); the import package and the `codeinenglish` command keep their names, and an `en` command is added. Check `https://pypi.org/pypi/en/json` is still a 404 immediately before the first upload: names are first come, first served and cannot be reserved without publishing.

Before publishing a package version:

1. Choose the release commit, version, project description, license, and public package name. Verify the chosen name is available and that both `pyproject.toml` and `build_backend.py` contain the same version.
2. Run `python3 -m unittest discover -s tests -q` with each claimed Python version and run the paired `en-language/scripts/verify_library.py` against a fresh install. The current checked environments are Python 3.10, 3.11, 3.12, 3.13, and 3.14.
3. Build a wheel with `python3 -m pip wheel --no-deps --no-build-isolation . -w dist`, inspect its `codeinenglish/*.py`, `METADATA`, `WHEEL`, `entry_points.txt`, and `RECORD`, then install that exact wheel in a fresh virtual environment outside the checkout.
4. Check that generation works with the network disconnected. Run Python and JavaScript examples. JavaScript generation needs no Node.js; executing generated JavaScript does.
5. Publish only the reviewed wheel, record its hash and release tag, and update installation instructions after confirming the published package resolves to the intended project. Publication is a separate release action.

## Upload (needs your own PyPI account and API token; never paste the token into chat or commit it)

1. Build: `python3 -m pip wheel --no-deps --no-build-isolation . -w dist`, then `python3 -m pip install twine` in a throwaway virtual environment and run `twine check dist/*`.
2. Rehearse on TestPyPI: `twine upload --repository testpypi dist/*`, then `pip install --index-url https://test.pypi.org/simple/ en` in a fresh environment and run `en run` on an example.
3. Publish: `twine upload dist/*`. A version can never be re-uploaded or replaced, so bump the version for any fix.
4. Moving from the old name: in any environment that has `codeinenglish` installed, run `pip uninstall codeinenglish` before `pip install en`, because both own the same files.
