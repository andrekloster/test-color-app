{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = [
    pkgs.docker
    pkgs.poetry
    pkgs.python312
  ];

  shellHook = ''
    poetry env use 3.12
    poetry install --no-root
    poetry run python build.py -e $DEPLOYMENT_ENV -v $VERSION
    exit
  '';
}
