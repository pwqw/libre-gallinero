
# -*- coding: utf-8 -*-
set -e
set -u
cd $HOME/libre-gallinero
git pull --rebase
exec ./termux/grabar-placa.sh
