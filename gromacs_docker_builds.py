#!/usr/bin/env python

'''
Author :
    * Muhammed Ahad <ahad3112@yahoo.com, maaahad@gmail.com>

Usage:
    $ python3 gromacs_docker_builds.py -h/--help
'''

import argparse
from utilities.cli import CLI
from container.recipes import GromacsRecipes

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='HPCCM recipes for GROMACS container')
    stages = CLI(parser=parser).get_stages()

    for key, value in stages.items():
        print('|||||||||||', key, value)

    # GromacsRecipes(cli=cli)

    # print(parser.parse_args().__dict__)
