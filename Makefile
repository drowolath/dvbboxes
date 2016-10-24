init:
	python setup.py --command-packages=stdeb.command bdist_deb
	rm -rf build dist .egg dvbboxes.egg-info dvbboxes*.tar.gz
	mv deb_dist/python-dvbboxes_*.deb .
	mv python-dvbboxes_*.deb deb_dist/python-dvbboxes.deb

clean:
	rm -r deb_dist

install:
	dpkg -i deb_dist/python-dvbboxes.deb
