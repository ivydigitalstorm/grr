#!/usr/bin/env python
"""setup.py file for a GRR API client library."""

import ConfigParser
import os
import shutil
import subprocess

from distutils.command.build_py import build_py

from setuptools import find_packages
from setuptools import setup
from setuptools.command.sdist import sdist

THIS_DIRECTORY = os.path.dirname(os.path.realpath(__file__))

# If you run setup.py from the root GRR dir you get very different results since
# setuptools uses the MANIFEST.in from the root dir.  Make sure we are in the
# package dir.
os.chdir(THIS_DIRECTORY)


def get_config():
  """Get INI parser with version.ini data."""
  ini_path = os.path.join(THIS_DIRECTORY, "version.ini")
  if not os.path.exists(ini_path):
    ini_path = os.path.join(THIS_DIRECTORY, "../../version.ini")
    if not os.path.exists(ini_path):
      raise RuntimeError("Couldn't find version.ini")

  config = ConfigParser.SafeConfigParser()
  config.read(ini_path)
  return config


# TODO(user): instead of being tightly coupled with the source files of the
# rest of GRR, we should introduce a separate package with compiled protobufs,
# that we can reuse (i.e. grr-response-proto). Compiling the protos here
# and doing the create_package_file() trickery and grr_api_client/__init__.py
# hack will all be unneeded then.
def compile_protos():
  """Builds necessary assets from sources.

  This compiles all the proto files from GRR codebase using grr_api_client/proto
  as the output path. This means, for example, that grr/proto/api.proto will be
  compiled to grr_api_client/proto/grr/api_pb2.py.

  compile_protos also writes __init__.py files into generated
  grr_api_client/proto subfolders in order for them to be correctly treated as
  Python packages.

  Compiled files are only needed if there's no "grr-response-core" package
  installed on the system (this will happen if the user installs just
  the grr-api-client package without installing the rest of GRR).
  grr_api_client/__init__.py tries to import grr.proto (that comes with
  grr-response-core) first and, if the import fails, modifies the sys.path to
  load the protos generated by compile_protos().

  sys.path modification is needed in order to load compiled protobufs code,
  because generated protobuf files reference each other via
  "from grr.proto import ..." imports (while we'd need something like
  "from grr_api_client.proto.grr.proto import ...") and because we don't
  want to do some heavy pre-processing of proto files to change their import
  statemets from "grr/proto/blah.proto" to something that's relative to
  grr_api_client.

  See grr_api_client/__init__.py for the sys.path modification code.
  """

  # Only compile protobufs if we're inside GRR source tree.
  if (not os.path.exists(
      os.path.join(THIS_DIRECTORY, "..", "..", "makefile.py")) or
      not os.path.exists(os.path.join(THIS_DIRECTORY, "..", "..", "..", "grr"))):
    return

  # Clean and recompile the protobufs.
  protos_out = os.path.join(THIS_DIRECTORY, "grr_api_client", "proto")
  try:
    os.makedirs(protos_out)
  except OSError:
    pass
  subprocess.check_call(
      ["python", "makefile.py", "--clean", "--python_out", protos_out],
      cwd=os.path.join(THIS_DIRECTORY, "../../"))

  # Create __init__ files for generated protobuf files.
  create_package_file(protos_out, "grr", "proto")
  create_package_file(protos_out, "grr", "proto", "api")
  create_package_file(protos_out, "grr", "client", "components",
                      "chipsec_support", "actions")
  create_package_file(protos_out, "grr", "client", "components",
                      "rekall_support")


def create_package_file(*dest):
  cur_path = None
  for d in dest:
    if not cur_path:
      cur_path = d
    else:
      cur_path = os.path.join(cur_path, d)

    with open(os.path.join(cur_path, "__init__.py"), "w"):
      pass


class Build(build_py):

  def find_all_modules(self):
    compile_protos()
    self.packages = find_packages()
    return build_py.find_all_modules(self)


class Sdist(sdist):
  """Build sdist."""

  def make_release_tree(self, base_dir, files):
    sdist.make_release_tree(self, base_dir, files)

    sdist_version_ini = os.path.join(base_dir, "version.ini")
    if os.path.exists(sdist_version_ini):
      os.unlink(sdist_version_ini)
    shutil.copy(
        os.path.join(THIS_DIRECTORY, "../../version.ini"), sdist_version_ini)


VERSION = get_config()

setup_args = dict(
    name="grr-api-client",
    version=VERSION.get("Version", "packageversion"),
    description="GRR API client library",
    license="Apache License, Version 2.0",
    url="https://github.com/google/grr/tree/master/api_client/python",
    cmdclass={
        "build_py": Build,
        "sdist": Sdist,
    },
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "grr_api_shell = grr_api_client.api_shell:main",
        ]
    },
    install_requires=[
        "ipython==5.0.0",
        "protobuf==3.3.0",
        "requests==2.9.1",
        "Werkzeug==0.11.3",
    ],
    data=["version.ini"])

setup(**setup_args)
