'''
Author :
    * Muhammed Ahad <ahad3112@yahoo.com, maaahad@gmail.com>
'''

from __future__ import print_function
import os
import hpccm
from hpccm.primitives import baseimage


class BuildRecipes:
    '''
    Docker/Singularity container specification
    '''
    # tag = 'cmake-{cmake_version}-gcc-{gcc_version}-fftw-{fftw_version}-{mpi}'
    stages = {}
    # _os_packages
    _os_packages = ['vim',
                    'wget', ]
    # python packages

    def __init__(self, *, cli):
        self.cli = cli
        # choosing base image
        self.__define_base_image()

    def __define_base_image(self):
        if self.cli.args.cuda:
            raise ValueError('Wrong Option : cuda is not supported.')
        else:
            if self.cli.args.ubuntu:
                self.base_image = 'ubuntu:' + self.cli.args.ubuntu
            elif self.cli.args.centos:
                self.base_image = 'centos:centos' + self.cli.args.centos
            else:
                raise RuntimeError('Input Error: No Linux distribution was chosen.')

        # We need to check whether the base image is available or not

    def __initiate_build_stage(self):
        self.stages['build'] = hpccm.Stage()

        self.stages['build'] += baseimage(image=self.base_image, _as='build')

        # ospackages
        self.stages['build'] += hpccm.building_blocks.packages(os_packages=self._os_packages)
        # python
        self.stages['build'] += hpccm.building_blocks.python()

        # cmake
        self.__add_cmake(stage='build')
        # compiler
        self.__add_compiler(stage='build')

        # mpi
        if self.cli.args.openmpi or self.cli.args.impi:
            self.__add_mpi(stage='build')

        # fftw
        self.__add_fftw(stage='build')

    def __add_cmake(self, *, stage):
        if self.cli.args.cmake:
            self.stages[stage] += hpccm.building_blocks.cmake(eula=True, version=self.cli.args.cmake)
        else:
            raise RuntimeError('Input Error : cmake is missing')

    def __add_compiler(self, *, stage):
        if self.cli.args.gcc:
            self.compiler = hpccm.building_blocks.gnu(fortran=False, version=self.cli.args.gcc)
            self.stages[stage] += self.compiler
        else:
            raise RuntimeError('Input Error: Only available compiler option is gcc.')

    def __add_fftw(self, *, stage):
        if self.cli.args.fftw:
            # fftw configure opts : Later we may try to set this from the user perspective
            configure_opts = ['--enable-openmp', '--enable-shared', '--enable-threads',
                              '--enable-sse2', '--enable-avx', '--enable-avx2', '--enable-avx512',
                              '--disable-static', ]
            # configuring configure_opts for fftw
            if not self.cli.args.double:
                configure_opts.append('--enable-float')

            # Don't think mpi option is necessary
            mpi = True if self.cli.args.openmpi else False

            if hasattr(self.compiler, 'toolchain'):
                self.stages[stage] += hpccm.building_blocks.fftw(toolchain=self.compiler.toolchain,
                                                                 configure_opts=configure_opts,
                                                                 mpi=mpi,
                                                                 version=self.cli.args.fftw)
            else:
                raise RuntimeError('Implementation Error: compiler is not an HPCCM building block')

    def __add_mpi(self, *, stage):
        if self.cli.args.openmpi:
            if hasattr(self.compiler, 'toolchain'):
                self.stages[stage] += hpccm.building_blocks.openmpi(cuda=False, infiniband=False,
                                                                    toolchain=self.compiler.toolchain,
                                                                    version=self.cli.args.openmpi)
            else:
                raise RuntimeError('Implementation Error: compiler is not an HPCCM building block')

        elif self.cli.args.impi:
            raise RuntimeError('Input Error: Intel MPI not implemented yet.')


# The reason to use separate class for GromacsRecipes is to use Paul's BuildStage here... if required
class GromacsRecipes(BuildRecipes):
    # tag = 'ahad3112/gromacs:{gromacs_version}-cmake-{cmake_version}' + \
    #     '-gcc-{gcc_version}-fftw-{fftw_version}-{mpi}'
    # The following option will add later
    # -DGMX_DEFAULT_SUFFIX=OFF \
    # -DGMX_BINARY_SUFFIX=$bin_suffix$ \
    # -DGMX_LIBS_SUFFIX=$libs_suffix$ \

    directory = 'gromacs-{version}'
    build_directory = 'build.{simd}'
    prefix = '/usr/local/gromacs'
    build_environment = {}
    url = 'ftp://ftp.gromacs.org/pub/gromacs/gromacs-{version}.tar.gz'
    cmake_opts = "\
    -DCMAKE_INSTALL_BINDIR=bin.$simd$ \
    -DCMAKE_INSTALL_LIBDIR=lib.$simd$ \
    -DCMAKE_C_COMPILER=$c_compiler$ \
    -DCMAKE_CXX_COMPILER=$cxx_compiler$ \
    -DGMX_OPENMP=ON \
    -DGMX_MPI=$mpi$ \
    -DGMX_GPU=$cuda$ \
    -DGMX_SIMD=$simd$ \
    -DGMX_USE_RDTSCP=$rdtscp$ \
    -DGMX_DOUBLE=$double$ \
    -D$fft$ \
    -DGMX_EXTERNAL_BLAS=OFF \
    -DGMX_EXTERNAL_LAPACK=OFF \
    -DBUILD_SHARED_LIBS=OFF \
    -DGMX_PREFER_STATIC_LIBS=ON \
    -DREGRESSIONTEST_DOWNLOAD=$regtest$ \
    -DGMX_BUILD_MDRUN_ONLY=$mdrun$ \
    "

    def __init__(self, *, cli):
        BuildRecipes.__init__(self, cli=cli)
        # initiate build stage
        self.__initiate_build_stage()
        # Runtime stage
        self.__runtime_stage(build_stage='build')
        # Generate Container Recipes
        self.__generate()

    def __initiate_build_stage(self):
        # Add common build stage
        BuildRecipes._BuildRecipes__initiate_build_stage(self)

        # iterate through each engine options to modify cmake_opts  ... Try without sci-f for now
        engine_cmake_opts = self.__get_cmake_opts()

        for engine in self.cli.gromacs_engines:
            # simd, rdtscp, mdrun
            for key in engine:
                value = engine[key] if key == 'simd' else engine[key].upper()
                engine_cmake_opts = engine_cmake_opts.replace('$' + key + '$', value)

            self.stages['build'] += hpccm.building_blocks.generic_cmake(cmake_opts=engine_cmake_opts.split(),
                                                                        directory=self.directory.format(version=self.cli.args.gromacs),
                                                                        build_directory=self.build_directory.format(simd=engine['simd']),
                                                                        prefix=self.prefix,
                                                                        build_environment=self.build_environment,
                                                                        url=self.url.format(version=self.cli.args.gromacs))

    def __runtime_stage(self, *, build_stage):
        self.stages['runtime'] = hpccm.Stage()
        self.stages['runtime'] += baseimage(image=self.base_image)
        self.stages['runtime'] += self.stages[build_stage].runtime()

        for engine in self.cli.gromacs_engines:
            self.stages['runtime'] += hpccm.primitives.environment(variables={'PATH': '$PATH:/usr/local/gromacs/bin.{simd}'.format(simd=engine['simd'])})

        self.stages['runtime'] += hpccm.primitives.label(metadata={'gromacs.version': self.cli.args.gromacs})

    def __get_cmake_opts(self):
        engine_cmake_opts = self.cmake_opts[:]
        # Compiler and mpi
        if self.cli.args.openmpi or self.cli.args.impi:
            engine_cmake_opts = engine_cmake_opts.replace('$c_compiler$', 'mpicc')
            engine_cmake_opts = engine_cmake_opts.replace('$cxx_compiler$', 'mpicxx')
            engine_cmake_opts = engine_cmake_opts.replace('$mpi$', 'ON')
        else:
            engine_cmake_opts = engine_cmake_opts.replace('$c_compiler$', 'gcc')
            engine_cmake_opts = engine_cmake_opts.replace('$cxx_compiler$', 'g++')
            engine_cmake_opts = engine_cmake_opts.replace('$mpi$', 'OFF')

        #  fftw
        if self.cli.args.fftw:
            engine_cmake_opts = engine_cmake_opts.replace('$fft$', 'GMX_FFT_LIBRARY=fftw3')
            self.build_environment['CMAKE_PREFIX_PATH'] = '/usr/local/fftw'
        else:
            engine_cmake_opts = engine_cmake_opts.replace('$fft$', 'GMX_BUILD_OWN_FFTW=ON')

        # cuda, regtest, double
        for option in ('cuda', 'regtest', 'double'):
            if getattr(self.cli.args, option):
                engine_cmake_opts = engine_cmake_opts.replace('$' + option + '$', 'ON')
            else:
                engine_cmake_opts = engine_cmake_opts.replace('$' + option + '$', 'OFF')

        # bin_suffix, libs_suffix

        return engine_cmake_opts

    def __generate(self):
        hpccm.config.set_container_format(self.cli.args.format)
        print(self.stages['build'])
        print(self.stages['runtime'])
