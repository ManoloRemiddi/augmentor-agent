#!/usr/bin/env python3
# Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0
"""Source-side updater launcher with no caller-supplied installation inputs."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'services'))


def main():
    if len(sys.argv)!=1:raise ValueError('The update launcher accepts no caller arguments.')
    from updates.windows_bootstrap import bootstrap
    bootstrap(ROOT)


if __name__=='__main__':main()
