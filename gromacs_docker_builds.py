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
    cli = CLI(parser=parser)
    GromacsRecipes(cli=cli)
