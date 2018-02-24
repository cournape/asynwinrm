try:
    from ._version import version_info as __version_info__
    from ._version import version as __version__
except ImportError:
    version_info = (0, 0, 0, "dev", 0)
    version = "0.0.0.dev0"

from .api import run_cmd, run_ps, run_psrp
