import ast
import os
import re
import subprocess

from setuptools import setup


MAJOR = 0
MINOR = 1
MICRO = 0

IS_RELEASED = False

PREVIOUS_VERSION = "d1c718c330dd24ee7fd1112c4ea4d571f8f4e45c"
VERSION = '%d.%d.%d' % (MAJOR, MINOR, MICRO)

INSTALL_REQUIRES = (
    "attrs >= 16.0.0",
    "lxml >= 3.6.0",
    "asyncio >= 1.3.0",
    "aiohttp >=3.0.6",
    "pykerberos >= 1.2.0",
    "pycryptodome >= 3.5.0",
    "ntlm_auth >= 1.1.0"
)

PACKAGES = (
    "aiowinrm",
    "aiowinrm.soap",
    "aiowinrm.sec",
    "aiowinrm.psrp",
)


def _minimal_ext_cmd(cmd):
    # construct minimal environment
    env = {}
    for k in ['SYSTEMROOT', 'PATH']:
        v = os.environ.get(k)
        if v is not None:
            env[k] = v
    # LANGUAGE is used on win32
    env['LANGUAGE'] = 'C'
    env['LANG'] = 'C'
    env['LC_ALL'] = 'C'
    out = subprocess.check_output(cmd, env=env)
    return out


# Return the git revision as a string
def git_version():
    try:
        out = _minimal_ext_cmd(['git', 'rev-parse', 'HEAD'])
        git_revision = out.strip().decode('ascii')
    except OSError:
        git_revision = "Unknown"

    return git_revision


_R_RC = re.compile("rc(\d+)$")


def is_rc(version):
    return _R_RC.search(version) is not None


def rc_number(version):
    m = _R_RC.search(version)
    assert m is not None
    return m.groups()[0]


def compute_build_number(from_tag):
    cmd = ["git", "rev-list", from_tag + "..", "--count"]
    output = _minimal_ext_cmd(cmd)
    build_number = int(output.strip())
    assert build_number < 2 ** 16, "build number overflow"
    return build_number


def write_version_py(filename):
    template = """\
# THIS FILE IS GENERATED FROM AIOWINRM SETUP.PY
version = '{final_version}'
full_version = '{full_version}'
git_revision = '{git_revision}'
is_released = {is_released}

version_info = {version_info}
"""
    version = full_version = VERSION
    is_released = IS_RELEASED

    if not os.path.exists('.git'):
        if os.path.exists(filename):
            return
        else:
            raise RuntimeError(
                "No git repo found and no {!r} found !".format(filename)
            )

    if os.path.isfile('.git'):  # submodule, we give up
        git_rev = "Unknown"
        build_number = 0
    else:
        git_rev = git_version()
        build_number = compute_build_number(PREVIOUS_VERSION)

    if is_rc(version):
        release_level = "rc"
    elif not IS_RELEASED:
        release_level = "dev"
    else:
        release_level = "final"

    if not IS_RELEASED:
        full_version += '.dev' + str(build_number)
        if is_rc(version):
            serial = rc_number(version)
        else:
            serial = build_number
        final_version = full_version
    else:
        final_version = version
        if is_rc(version):
            serial = rc_number(version)
        else:
            serial = 0

    version_info = (MAJOR, MINOR, MICRO, release_level, serial)

    with open(filename, "wt") as fp:
        data = template.format(
            final_version=final_version, full_version=full_version,
            git_revision=git_rev, is_released=is_released,
            version_info=version_info
        )
        fp.write(data)


class _AssignmentParser(ast.NodeVisitor):
    def __init__(self):
        self._data = {}

    def parse(self, s):
        self._data.clear()

        root = ast.parse(s)
        self.visit(root)
        return self._data

    def generic_visit(self, node):
        if type(node) != ast.Module:
            raise ValueError(
                "Unexpected expression @ line {0}".format(node.lineno),
                node.lineno
            )
        super(_AssignmentParser, self).generic_visit(node)

    def visit_Assign(self, node):
        value = ast.literal_eval(node.value)
        for target in node.targets:
            self._data[target.id] = value


def parse_version(path):
    with open(path) as fp:
        return _AssignmentParser().parse(fp.read())["version"]


def main():
    version_file = os.path.join("aiowinrm", "_version.py")
    write_version_py(version_file)
    version = parse_version(version_file)

    setup(
        author="Sjuul Janssen",
        author_email="sjuul@transceptor.technology",
        name="aiowinrm",
        description="A python 3.5+ async library for the WinRM protocol",
        url="https://github.com/obeleh/aio-winrm",
        version=version,
        license="Apache 2.0",
        packages=PACKAGES,
        install_requires=INSTALL_REQUIRES,
    )


if __name__ == "__main__":
    main()

