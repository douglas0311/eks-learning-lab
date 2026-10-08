"""Allowlisted entry point for current and archived SRE scenarios."""
import argparse
from pathlib import Path
import subprocess
import sys

ROUTES = {
    'lab-03': ('lab03.py', (), {'activate', 'restore'}),
    'lab-04': ('lab04.py', (), {'activate', 'restore', 'check'}),
    'lab-05': ('lab05.py', ('lab-05',), {'activate', 'restore', 'check', 'cleanup'}),
    'lab-05.1': ('lab05.py', ('lab-05.1',), {'activate', 'restore', 'check', 'cleanup'}),
    'lab-05.2': ('lab05.py', ('lab-05.2',), {'activate', 'restore', 'check', 'cleanup'}),
    'lab-06': ('lab06.py', (), {'activate', 'restore', 'check', 'cleanup'}),
}


def command(scenario, operation):
    if scenario not in ROUTES:
        raise ValueError('Unknown lab: ' + scenario)
    script, extra, allowed = ROUTES[scenario]
    if operation not in allowed:
        raise ValueError(scenario + ' supports only: ' + ', '.join(sorted(allowed)))
    return [sys.executable, str(Path(__file__).resolve().with_name(script)), operation, *extra]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scenario')
    parser.add_argument('operation')
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args(argv)
    try:
        selected = command(args.scenario, args.operation)
    except ValueError as error:
        parser.error(str(error))
    if args.validate_only:
        print('Valid selection: ' + args.scenario + ' / ' + args.operation)
        return
    subprocess.run(selected, check=True)


if __name__ == '__main__':
    main()
