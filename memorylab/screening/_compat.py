"""Compatibility shim for PyCCE with newer SciPy/NumPy versions.

PyCCE 1.1.1 has several incompatibilities with modern scientific Python:
- `scipy.sparse.sputils.isintlike` was removed in SciPy 1.13+
- `np.unicode_` was removed in NumPy 2.0 (use `np.str_` instead)
- `pd.read_csv(delim_whitespace=...)` is deprecated in pandas

This shim restores these before PyCCE is imported.
"""
import numpy as np


def _install_scipy_shim():
    """Install isintlike into scipy.sparse.sputils if missing."""
    try:
        import scipy.sparse.sputils as sputils
        if not hasattr(sputils, "isintlike"):
            def isintlike(x):
                if isinstance(x, (int, np.integer)):
                    return True
                if isinstance(x, (float, np.floating)) and float(x).is_integer():
                    return True
                return False
            sputils.isintlike = isintlike
    except ImportError:
        pass


def _install_numpy_shim():
    """Restore np.unicode_ and np.str_ aliases removed in NumPy 2.0."""
    if not hasattr(np, 'unicode_'):
        np.unicode_ = np.str_
    if not hasattr(np, 'string_'):
        np.string_ = np.bytes_


def _install_pandas_shim():
    """Patch pd.read_csv to convert delim_whitespace to sep='\\s+'."""
    try:
        import pandas as pd
        if not hasattr(pd, '_delim_ws_patched'):
            _original_read_csv = pd.read_csv
            def _patched_read_csv(*args, **kwargs):
                if kwargs.get('delim_whitespace'):
                    kwargs['sep'] = r'\s+'
                    del kwargs['delim_whitespace']
                return _original_read_csv(*args, **kwargs)
            pd.read_csv = _patched_read_csv
            pd._delim_ws_patched = True
    except ImportError:
        pass


def install_all_shims():
    """Install all compatibility shims for PyCCE."""
    _install_numpy_shim()
    _install_scipy_shim()
    _install_pandas_shim()


install_all_shims()
