# gromacs-hpccm-recipes
HPCCM recipes for GROMACS build and installation


#### Sample Command

    /gromacs_docker_builds.py --ubuntu 18.04 --engines simd=sse2:rdtscp=off:mdrun=off simd=avx2:rdtscp=on:mdrun=on simd=avx2:rdtscp=off:mdrun=on  --gromacs 2020.1> Dockerfile
