# Copyright 2020 The Cirq Developers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import functools
import glob
import os
import pathlib
import subprocess
import sys
from typing import Set

import pytest
from filelock import FileLock

from dev_tools import shell_tools
from dev_tools.env_tools import create_virtual_env

SKIP_NOTEBOOKS = [
    # skipping vendor notebooks as we don't have auth sorted out
    "**/google/*.ipynb",
    "**/pasqal/*.ipynb",
    "**/aqt/*.ipynb",
    # skipping fidelity estimation due to
    # https://github.com/quantumlib/Cirq/issues/3502
    "examples/*fidelity*",
    # https://github.com/quantumlib/Cirq/pull/3669#issuecomment-766450463
    'docs/characterization/*.ipynb',
    # chemistry.ipynb requires openfermion, that installs cirq 0.9.1, which interferes
    # with testing cirq itself...
    'docs/tutorials/educators/chemistry.ipynb',
]


def _list_all_notebooks() -> Set[str]:
    output = subprocess.check_output(['git', 'ls-files', '*.ipynb'])
    return set(output.decode('utf-8').splitlines())


def _tested_notebooks():
    """We list all notebooks here, even those that are not """

    all_notebooks = _list_all_notebooks()
    skipped_notebooks = functools.reduce(
        lambda a, b: a.union(b), list(set(glob.glob(g, recursive=True)) for g in SKIP_NOTEBOOKS)
    )

    # sorted is important otherwise pytest-xdist will complain that
    # the workers have different parametrization:
    # https://github.com/pytest-dev/pytest-xdist/issues/432
    return sorted(os.path.abspath(n) for n in all_notebooks.difference(skipped_notebooks))


TESTED_NOTEBOOKS = _tested_notebooks()


@pytest.mark.slow
@pytest.mark.parametrize("notebook_path", TESTED_NOTEBOOKS)
def test_notebooks_against_released_cirq(notebook_path):
    notebook_file = os.path.basename(notebook_path)
    notebook_rel_dir = os.path.dirname(os.path.relpath(notebook_path, "."))
    out_path = f"out/{notebook_rel_dir}/{notebook_file[:-6]}.out.ipynb"
    cmd = f"""mkdir -p out/{notebook_rel_dir}
papermill {notebook_path} {out_path}"""

    stdout, stderr, status = shell_tools.run_shell(
        cmd=cmd,
        log_run_to_stderr=False,
        raise_on_fail=False,
        out=shell_tools.TeeCapture(),
        err=shell_tools.TeeCapture(),
    )

    if status != 0:
        print(stderr)
        pytest.fail(f"Notebook failure: {notebook_file}, please see {out_path}")
