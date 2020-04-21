'''
Author :
    * Muhammed Ahad <ahad3112@yahoo.com, maaahad@gmail.com>
'''

from __future__ import print_function
import os
from distutils.version import StrictVersion

import hpccm

import config


class BuildRecipes:
    '''
    Docker/Singularity container specification
    '''
    stages = {}
    # os_packages
    os_packages = ['vim', 'wget']

    def __init__(self, *, cli):
        self.cli = cli
        # choosing base image
        self.__define_base_image()

    def __define_base_image(self):
        if self.cli.args.cuda:
            # TODO : add on second iteration
            raise RuntimeError('Wrong Option : cuda is not supported.')
        else:
            if self.cli.args.ubuntu:
                self.base_image = 'ubuntu:' + self.cli.args.ubuntu
            elif self.cli.args.centos:
                self.base_image = 'centos:centos' + self.cli.args.centos
            else:
                raise RuntimeError('Input Error: No Linux distribution was chosen.')

        # TODO: We need to check whether the base image is available or not

    def __initiate_build_stage(self):
        self.stages['build'] = hpccm.Stage()

        self.stages['build'] += hpccm.primitives.baseimage(image=self.base_image, _as='build')

        # python TODO: need to think whether to have this in the container
        self.stages['build'] += hpccm.building_blocks.python(python3=True,
                                                             python2=False,
                                                             devel=False)

        # cmake
        self.__add_cmake(stage='build')
        # compiler
        self.__add_compiler(stage='build')
        # mpi
        self.__add_mpi(stage='build')
        # fftw
        self.__add_fftw(stage='build')

    def __add_cmake(self, *, stage):
        if self.cli.args.cmake and BuildRecipes.version_checked('CMake',
                                                                config.CMAKE_MIN_REQUIRED_VERSION,
                                                                self.cli.args.cmake):
            self.stages[stage] += hpccm.building_blocks.cmake(eula=True, version=self.cli.args.cmake)
        else:
            raise RuntimeError('Implementation Error : Default CMake is missing')

    def __add_compiler(self, *, stage):
        # if self.cli.args.gcc and BuildRecipes.version_checked('gcc',
        #                                                       config.GCC_MIN_REQUIRED_VERSION,
        #                                                       self.cli.args.gcc):
        if self.cli.args.gcc:
            self.compiler = hpccm.building_blocks.gnu(fortran=False, version=self.cli.args.gcc)
            self.stages[stage] += self.compiler
        else:
            raise RuntimeError('Input Error: Only available compiler option is gcc.')

    def __add_fftw(self, *, stage):
        if self.cli.args.fftw:
            # TODO: fftw configure opts : Later we may try to set this from the user perspective
            configure_opts = ['--enable-shared', '--disable-static', '--enable-sse2',
                              '--enable-avx', '--enable-avx2', '--enable-avx512']
            # configuring configure_opts for fftw
            if not self.cli.args.double:
                configure_opts.append('--enable-float')

            if hasattr(self.compiler, 'toolchain'):
                self.stages[stage] += hpccm.building_blocks.fftw(toolchain=self.compiler.toolchain,
                                                                 configure_opts=configure_opts,
                                                                 version=self.cli.args.fftw)
            else:
                raise RuntimeError('Implementation Error: compiler is not an HPCCM building block')

    def __add_mpi(self, *, stage):
        if self.cli.args.openmpi and BuildRecipes.version_checked('openmpi',
                                                                  config.OPENMPI_MIN_REQUIRED_VERSION,
                                                                  self.cli.args.openmpi):
            if hasattr(self.compiler, 'toolchain'):
                self.stages[stage] += hpccm.building_blocks.openmpi(cuda=False, infiniband=False,
                                                                    toolchain=self.compiler.toolchain,
                                                                    version=self.cli.args.openmpi)
            else:
                raise RuntimeError('Implementation Error: compiler is not an HPCCM building block')

        elif self.cli.args.impi:
            raise RuntimeError('Input Error: Intel MPI not implemented yet.')

    @staticmethod
    def version_checked(tool, required, given):
        if StrictVersion(given) < StrictVersion(required):
            raise RuntimeError('Invalid {tool} version: {given}. Minimum required version: {required}.'.format(
                tool=tool,
                given=given,
                required=required
            ))

        return True


class GromacsRecipes(BuildRecipes):
    '''
    This class mostly deals with configuring GROMACS and stage['deploy']
    Most part of the build stage is delegated to super class BuildRecipes
    '''
    directory = 'gromacs-{version}'
    build_directory = 'build.{simd}'
    prefix = config.GMX_INSTALLATION_DIRECTORY
    build_environment = {}
    url = 'ftp://ftp.gromacs.org/pub/gromacs/gromacs-{version}.tar.gz'

    # regression test
    regtest = '/var/tmp/' + directory + '/' + build_directory + \
        '/tests/regressiontests-{version}/gmxtest.pl all {np} -suffix {suffix}'

    # Regression test : direct download and direct gmxtest.pl call
    regressiontest_url = 'http://gerrit.gromacs.org/download/regressiontests-{version}.tar.gz'
    regressiontest_tarball = os.path.split(regressiontest_url)[1]
    regressiontest_directory = regressiontest_tarball.replace('.tar.gz', '')
    regressiontest = os.path.join(regressiontest_directory, 'gmxtest.pl')

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
    -DGMX_DEFAULT_SUFFIX=OFF \
    -DGMX_BINARY_SUFFIX=$bin_suffix$ \
    -DGMX_LIBS_SUFFIX=$libs_suffix$ \
    "

    # list of wrapper binaries
    wrappers = []

    def __init__(self, *, cli):
        BuildRecipes.__init__(self, cli=cli)
        # initiate build stage
        self.__initiate_build_stage()
        # Runtime stage
        self.__deployment_stage(build_stage='build')
        # Generate Container Recipes
        self.__generate()

    def __initiate_build_stage(self):
        # Add common build stage
        BuildRecipes._BuildRecipes__initiate_build_stage(self)

        # iterate through each GrROMACS engine options to modify cmake_opts
        # TODO: Download GROMACS only once...

        engine_cmake_opts = self.__get_cmake_opts()
        for engine in self.cli.gromacs_engines:
            # binary and library suffix
            bin_libs_suffix = self.__get_bin_libs_suffix(engine['rdtscp'])
            cmake_opts = engine_cmake_opts.replace('$bin_suffix$', bin_libs_suffix)
            cmake_opts = cmake_opts.replace('$libs_suffix$', bin_libs_suffix)

            # wrapper suffix
            self.wrappers.append('mdrun') if engine['mdrun'].lower() == 'on' else self.wrappers.append('gmx')

            # simd, rdtscp, mdrun
            for key in engine:
                value = engine[key] if key == 'simd' else engine[key].upper()
                cmake_opts = cmake_opts.replace('$' + key + '$', value)

            # Adding regression test
            postinstall = []
            preconfigure = []
            check = False
            if self.cli.args.regtest:
                perl = ['apt-get update',
                        'apt-get upgrade -y',
                        'apt-get install -y perl',
                        ]

                if engine['mdrun'].lower() == 'off':
                    check = True
                    preconfigure.extend(perl)

                else:
                    postinstall.extend(perl + [
                        'export PATH={GMX_BINARY_DIRECTORY}:$PATH'.format(
                            GMX_BINARY_DIRECTORY=config.GMX_BINARY_DIRECTORY.format(
                                engine['simd']
                            )),
                        '{regtest}'.format(regtest=self.regtest.format(
                            version=self.cli.args.gromacs,
                            simd=engine['simd'],
                            np='-np 2' if self.cli.args.openmpi or self.cli.args.impi else '',
                            suffix=bin_libs_suffix
                        ))
                    ])

            # Generic cmake
            self.stages['build'] += hpccm.building_blocks.generic_cmake(cmake_opts=cmake_opts.split(),
                                                                        directory=self.directory.format(version=self.cli.args.gromacs),
                                                                        build_directory=self.build_directory.format(simd=engine['simd']),
                                                                        prefix=self.prefix,
                                                                        build_environment=self.build_environment,
                                                                        url=self.url.format(version=self.cli.args.gromacs),
                                                                        preconfigure=preconfigure,
                                                                        check=check,
                                                                        postinstall=postinstall)

        # Addimg appropriate suffix to the wrapper binaries
        wrapper_suffix = self.__get_wrapper_suffix()
        self.wrappers = [wrapper + wrapper_suffix for wrapper in set(self.wrappers)]

    def __deployment_stage(self, *, build_stage):
        self.stages['deploy'] = hpccm.Stage()
        self.stages['deploy'] += hpccm.primitives.baseimage(image=self.base_image)
        self.stages['deploy'] += hpccm.building_blocks.packages(ospackages=self.os_packages)
        self.stages['deploy'] += self.stages[build_stage].runtime()

        # setting wrapper binaries
        # create the wrapper binaries directory
        wrappers_directory = os.path.join(config.GMX_INSTALLATION_DIRECTORY, 'bin')
        self.stages['deploy'] += hpccm.primitives.shell(commands=['mkdir -p {}'.format(wrappers_directory)])

        for wrapper in self.wrappers:
            wrapper_path = os.path.join(wrappers_directory, wrapper)
            self.stages['deploy'] += hpccm.primitives.copy(src='/scripts/wrapper.py',
                                                           dest=wrapper_path)

        # setting the gmx_chooser script
        self.stages['deploy'] += hpccm.primitives.copy(src='/scripts/gmx_chooser.py',
                                                       dest=os.path.join(wrappers_directory, 'gmx_chooser.py'))
        # chmod
        self.stages['deploy'] += hpccm.primitives.shell(commands=['chmod +x {}'.format(
            os.path.join(wrappers_directory, '*')
        )])

        # copying config file
        self.stages['deploy'] += hpccm.primitives.copy(src='config.py',
                                                       dest=os.path.join(wrappers_directory, 'config.py'))
        # environment variable
        self.stages['deploy'] += hpccm.primitives.environment(variables={'PATH': '$PATH:{}'.format(wrappers_directory)})

        self.stages['deploy'] += hpccm.primitives.label(metadata={'gromacs.version': self.cli.args.gromacs})

    def __get_wrapper_suffix(self):
        return config.WRAPPER_SUFFIX_FORMAT.format(mpi=config.GMX_ENGINE_SUFFIX_OPTIONS['mpi'] if self.cli.args.openmpi or self.cli.args.impi else '',
                                                   double=config.GMX_ENGINE_SUFFIX_OPTIONS['double'] if self.cli.args.double else '')

    def __get_bin_libs_suffix(self, rdtscp):
        return config.BINARY_SUFFIX_FORMAT.format(mpi=config.GMX_ENGINE_SUFFIX_OPTIONS['mpi'] if self.cli.args.openmpi or self.cli.args.impi else '',
                                                  double=config.GMX_ENGINE_SUFFIX_OPTIONS['double'] if self.cli.args.double else '',
                                                  rdtscp=config.GMX_ENGINE_SUFFIX_OPTIONS['rdtscp'] if rdtscp.lower() == 'on' else '')

    def __get_cmake_opts(self):
        engine_cmake_opts = self.cmake_opts[:]
        # Compiler and mpi
        if self.cli.args.openmpi or self.cli.args.impi:
            engine_cmake_opts = engine_cmake_opts.replace('$c_compiler$', 'mpicc')
            engine_cmake_opts = engine_cmake_opts.replace('$cxx_compiler$', 'mpicxx')
            engine_cmake_opts = engine_cmake_opts.replace('$mpi$', 'ON')

            # setting for regtest
            if self.cli.args.regtest:
                # TODO: missing mpiexec ??????????
                # regtest_mpi_cmake_variables = "-DMPIEXEC=mpiexec \
                # -DMPIEXEC_NUMPROC_FLAG=-np \
                # -DMPIEXEC_PREFLAGS='--allow-run-as-root;--oversubscribe' \
                # -DMPIEXEC_POSTFLAGS= "
                regtest_mpi_cmake_variables = " -DMPIEXEC_NUMPROC_FLAG=-np \
                        -DMPIEXEC_PREFLAGS='--allow-run-as-root;--oversubscribe'\
                        -DMPIEXEC_POSTFLAGS="
                engine_cmake_opts = engine_cmake_opts + regtest_mpi_cmake_variables

        else:
            engine_cmake_opts = engine_cmake_opts.replace('$c_compiler$', 'gcc')
            engine_cmake_opts = engine_cmake_opts.replace('$cxx_compiler$', 'g++')
            engine_cmake_opts = engine_cmake_opts.replace('$mpi$', 'OFF')

        #  fftw
        if self.cli.args.fftw:
            engine_cmake_opts = engine_cmake_opts.replace('$fft$', 'GMX_FFT_LIBRARY=fftw3')
            self.build_environment['CMAKE_PREFIX_PATH'] = '\'/usr/local/fftw\''
        else:
            engine_cmake_opts = engine_cmake_opts.replace('$fft$', 'GMX_BUILD_OWN_FFTW=ON')

        # cuda, regtest, double
        for option in ('cuda', 'regtest', 'double'):
            if getattr(self.cli.args, option):
                engine_cmake_opts = engine_cmake_opts.replace('$' + option + '$', 'ON')
            else:
                engine_cmake_opts = engine_cmake_opts.replace('$' + option + '$', 'OFF')

        return engine_cmake_opts

    def __generate(self):
        hpccm.config.set_container_format(self.cli.args.format)
        print(self.stages['build'])
        print(self.stages['deploy'])
