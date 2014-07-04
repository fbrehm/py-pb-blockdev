#
# Makefile for i18n-Objects in pb-base
#

.SUFFIXES: .mo .po

MODULE     = py_pb_blockdev
LOCALE_DIR = /usr/share/locale
DESTDIR    =

all: $(MODULE:=.de.mo)

.po.mo:
	@echo
	@echo "Compiling $*.mo from $*.po ..."
	msgfmt -o $*.mo --check -v $*.po
	@if [ ! -d de/LC_MESSAGES ] ; then mkdir -vp de/LC_MESSAGES; fi
	@TARGET=de/LC_MESSAGES/`echo $* | sed s'/\.de$$//'`.mo; \
		cp -pv $*.mo $$TARGET

clean:
	@echo
	@echo "Removing locale output dirs ..."
	for dir in *; do \
		if [ -d $$dir ] ; then \
			rm -rv $$dir ; \
		fi ; \
	done
	@echo "Removing compiled language message files ..."
	rm -vf *.mo

install: all
	@echo
	@echo "Installing language message files ..."
	if [ ! -d $(DESTDIR)$(LOCALE_DIR) ] ; then \
		mkdir -vp $(DESTDIR)$(LOCALE_DIR) ; \
	fi
	for dir in *; do \
		if [ -d $$dir ] ; then \
			cp -vR $$dir $(DESTDIR)$(LOCALE_DIR) ; \
		fi ; \
	done

.PHONY: all clean install
