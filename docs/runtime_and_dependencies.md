# Runtime and dependency policy

Use Python3.12 from the working-tree root; the package supports this branch and installs editable because dbt/infra resources remain in the working tree. Runtime evidence names the exact Python/tool/engine versions actually executed. PowerShell5.1/7 and Docker Compose v2 with --wait are the intended Windows workflow; native validation is a separate acceptance gate.

Direct dependencies are pinned in requirements.txt and pyproject.toml. requirements-py312.lock.txt records the tested Python3.12 Linux resolution and is not a claim that Windows wheels/another Python branch were verified. Install with `python -m pip install -r requirements.txt -c requirements-py312.lock.txt`, then pip check and the acceptance suite. The setuptools build backend is pinned. PostgreSQL container tag pins major/minor and base distribution; no image digest/pull execution is claimed if the engine was unavailable.

For updates, change the direct pins in both files, create a fresh venv, regenerate the constraints from its distribution metadata (exclude the local editable package/path), run unit/full/native acceptance, and record versions/evidence. Never include a local absolute editable path or credentials in the lock. Do not edit applied SQL migration checksums. No LICENSE was added: distribution/reuse licensing requires the owner's explicit choice.

The empty dbt analyses/seeds directories are intentionally retained as registered scaffold. Redundant placeholders in macros/snapshots/tests are removed.
