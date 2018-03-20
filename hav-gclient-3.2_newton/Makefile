
DESTDIR := 
SITELIB := $(shell python -c "from distutils.sysconfig import get_python_lib; print get_python_lib(1)[1:]")
DEBUGSRC := "/usr/src/debug"
DEBUGLIB := "/usr/lib/debug"
CC := gcc
PYVER := $(shell python -c "import sys; print sys.version[0:3]")
CFLAGS := -g -I/usr/include/python$(PYVER) -Wall -Werror -fPIC $(OPTFLAGS) -fno-strict-aliasing
LDFLAGS := -shared

#VERSION := $(shell awk '/Version:/ { print $$2 }' python-pyblock.spec)
#RELEASE := $(shell awk -F '[ %]' '/Release:/ { print $$2 }' python-pyblock.spec)
USESELINUX = 1
COMPILE_PYTHON := tools/compile.py
dm_LIBS = dmraid devmapper
ifeq (1, $(USESELINUX))
dm_LIBS += selinux
CFLAGS += -DUSESELINUX=1
endif
dmraid_LIBS = dmraid devmapper

PYFILES=About.pyc LoginFrame.pyc Resource.pyc Util.pyc \
		Advance.pyc Main.pyc Session.pyc VM.pyc \
		Console.pyc MainFrame.pyc Setting.pyc Version.pyc \
		DisplayPanel.pyc Network.pyc SettingDialog.pyc \
		Logger.pyc ProgressDialog.pyc Update.pyc VMAction.pyc \
		backend.pyc base.pyc consoleInfo.pyc exceptions.pyc \
		havclient.pyc user.pyc utils.pyc ResolutionDialog.pyc \
        ShutdownDialog.pyc start.pyc RDPLoginDialog.pyc Wfile.pyc \
		VPNDialog.pyc ChangePw.pyc RDPSettingDialog.pyc Message.pyc \
        SendRequests.pyc ServiceThread.pyc
SHFILES=gf_launch.sh 
DISABLE=99-disable-fn.conf
XORGFILES=xorg.conf
exec :
	@chmod 777 *.sh
	@chmod 777 tools/compile.py
	@$(COMPILE_PYTHON) .
all :	exec

tag:
	@git tag -a -m "Tag as pyblock-$(VERSION)-$(RELEASE)" pyblock-$(VERSION)-$(RELEASE)
	@echo "Tagged as pyblock-$(VERSION)-$(RELEASE)"

archive-no-tag:
	@git archive --format=tar --prefix=pyblock-$(VERSION)/ pyblock-$(VERSION)-$(RELEASE) > pyblock-$(VERSION).tar
	@bzip2 -f pyblock-$(VERSION).tar

archive: clean tag archive-no-tag

dist : archive

upload: dist
	@scp pyblock-$(VERSION).tar.bz2 fedorahosted.org:pyblock

flat_install: all
	@install -v -m 0755 -d ${DESTDIR}/
	@for x in $(PYFILES) ; do \
		install -v -m 0755 $$x ${DESTDIR}/$$x ; \
	done
	@for x in $(LIBS) ; do \
		install -v -m 0755 $$x.$(VERSION) ${DESTDIR}/$$x ; \
	done

install_debug: clean all
	@install -v -m 0755 -d "${DESTDIR}/RHupdates/block"
	@install -v -m 0755 -d "${DESTDIR}/RHupdates/${DEBUGLIB}/${SITELIB}/block"
	@install -v -m 0755 -d "${DESTDIR}/RHupdates/usr/src/debug/pyblock-${VERSION}"
	@for x in ${PYFILES} ; do \
		install -m 0755 $$x ${DESTDIR}/RHupdates/block/$$x ; \
	done
	@for x in "*.[ch]" ; do \
		install -m 0644 $$x \
		  "${DESTDIR}/RHupdates/usr/src/debug/pyblock-${VERSION}/" ; \
	done
	@for x in ${LIBS} ; do \
		echo /usr/lib/rpm/debugedit -b "${PWD}" \
			-d /usr/src/debug \
			"$$x.${VERSION}" ; \
		/usr/lib/rpm/debugedit -b "${PWD}" \
			-d /usr/src/debug \
			"$$x.${VERSION}" ; \
		echo eu-strip -f \
		  "${DESTDIR}/RHupdates/${DEBUGLIB}/${SITELIB}/block/$$x.debug"\
		  "$$x.${VERSION}" ; \
		echo install -m 0755 $$x.${VERSION} \
			${DESTDIR}/RHupdates/block/$$x ; \
		install -m 0755 $$x.${VERSION} \
			${DESTDIR}/RHupdates/block/$$x ; \
	done

install : all
	@install -v -m 0755 -d "${DESTDIR}/usr/share/hav-gclient/"
	@install -v -m 0755 -d "${DESTDIR}/usr/bin/"
	@install -v -m 0755 -d "${DESTDIR}/etc/init.d/"
	@install -v -m 0755 -d "${DESTDIR}/etc/rc.d/rc5.d/"
	@install -v -m 0755 -d "${DESTDIR}/usr/share/hav-gclient/images/"
	@install -v -m 0755 -d "${DESTDIR}/usr/share/hav-gclient/xorg/"
	@install -v -m 0755 -d "${DESTDIR}/etc/X11/"
	@install -v -m 0755 -d "${DESTDIR}/etc/X11/xorg.conf.d/"
	#@install -v -m 0755 -d "${DESTDIR}/etc/xdg/autostart/"
	#@install -v -m 0755 -d "${DESTDIR}/usr/share/hav-gclient/"
	#@install -v -m 0755 -d "${DESTDIR}/etc/xscreensaver/"
	@for x in ${PYFILES} ; do \
		install -v -m 0755 $$x ${DESTDIR}/usr/share/hav-gclient/$$x ; \
	done
	@for x in ${SHFILES} ; do \
		install -v -m 0777 $$x ${DESTDIR}/usr/bin/$$x; \
	done
	@for x in ${XORGFILES} ; do \
		install -v -m 0777 $$x ${DESTDIR}/etc/X11/$$x; \
	done
	@for x in ${DISABLE} ; do \
		install -v -m 0777 $$x ${DESTDIR}/etc/X11/xorg.conf.d/$$x; \
	done
	@cp -r images ${DESTDIR}/usr/share/hav-gclient/
	@cp -r xorg ${DESTDIR}/usr/share/hav-gclient/
	@cp xorg.conf ${DESTDIR}/etc/X11/
	@cp 99-disable-fn.conf ${DESTDIR}/etc/X11/xorg.conf.d/ 
	#@cp NetIPS.sh ${DESTDIR}/usr/share/hav-gclient/
	@cp gclient.desktop ${DESTDIR}/usr/share/hav-gclient/
	#@cp flag ${DESTDIR}/usr/share/hav-gclient/ reboot
	#@cp xmodmap.conf ${DESTDIR}/usr/share/hav-gclient/ Alt
	@cp XScreenSaver.ad ${DESTDIR}/usr/share/hav-gclient/
	@cp pcmanfm.conf ${DESTDIR}/usr/share/hav-gclient/
	@cp lxde-rc.xml ${DESTDIR}/usr/share/hav-gclient/
	#@cp ovirt-ip ${DESTDIR}/etc/init.d/
	#@cp ovirt-engine ${DESTDIR}/etc/
	#@cp xorg.conf ${DESTDIR}/etc/X11/
	#@cp gclient.desktop ${DESTDIR}/etc/xdg/autostart
	#@cp XScreenSaver.ad ${DESTDIR}/etc/xscreensaver

clean :
	@rm -vf *.py[co] *.so *.so.${VERSION} *.o core* *.pyc *.pyo
	@rm -vf pyblock-*.tar.bz2

.PHONY : clean install
.SECONDARY : ${foreach lib,${LIBS},${lib}.${VERSION}}
