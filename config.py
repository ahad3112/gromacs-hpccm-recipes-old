'''
Author :
    * Muhammed Ahad <ahad3112@yahoo.com, maaahad@gmail.com>
'''

# Argument options
ENGINE_OPTIONS = {'simd': ['avx_512f', 'avx2', 'avx', 'sse2'],
                  'rdtscp': ['on', 'off'],
                  'mdrun': ['on', 'off']}

SIMD_MAPPER = dict(zip(ENGINE_OPTIONS['simd'], ['AVX_512', 'AVX2_256', 'AVX_256', 'SSE2']))


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
