'''
Author :
    * Muhammed Ahad <ahad3112@yahoo.com, maaahad@gmail.com>
'''

import os

# Argument options for GROMACS : TODO : The Following Things needs to be simplified
ARCHITECTURES = ['avx_512f', 'avx2', 'avx', 'sse2']
GMX_BINARY_DIRECTORY_SUFFIX = ['AVX_512', 'AVX2_256', 'AVX_256', 'SSE2']

ENGINE_OPTIONS = {'simd': ARCHITECTURES,
                  'rdtscp': ['on', 'off'],
                  'mdrun': ['on', 'off']}

SIMD_MAPPER = dict(zip(ENGINE_OPTIONS['simd'], GMX_BINARY_DIRECTORY_SUFFIX))


# Default Arguments
DEFAULT_SIMD = 'sse2'
DEFAULT_RDTSCP = 'on'
DEFAULT_MDRUN = 'off'

DEFAULT_ENGINES = [dict(zip(ENGINE_OPTIONS.keys(), [DEFAULT_SIMD, DEFAULT_RDTSCP, DEFAULT_MDRUN])), ]

# Minimum Software Version

# Default Software version
DEFAULT_GROMACS_VERSION = '2020.1'
DEFAULT_GCC_VERSION = '8'
DEFAULT_CMAKE_VERSION = '3.9.6'


# Configuration related to GMX engines
# Default Suffix for GMX engine binaries
GMX_INSTALLATION_DIRECTORY = '/usr/local/gromacs'
GMX_BINARY_DIRECTORY = os.path.join(GMX_INSTALLATION_DIRECTORY, 'bin.{0}')

GMX_ENGINE_SUFFIX_OPTIONS = {
    'mpi': '_mpi',
    'double': '_d',
    'rdtscp': '_rdtscp'
}

BINARY_SUFFIX_FORMAT = '{mpi}{double}{rdtscp}'
LIBRARY_SUFFIX_FORMAT = '{mpi}{double}{rdtscp}'


WRAPPER_SUFFIX_FORMAT = '{mpi}{double}'
