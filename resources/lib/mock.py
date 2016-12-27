import libreelec

def mock_libreelec():
    libreelec.OS_RELEASE['NAME'] = 'LibreELEC'
    libreelec.OS_RELEASE['VERSION_ID'] = '8.0'
    libreelec.OS_RELEASE['VERSION'] = 'devel-20161224210557-#1224-gdc61a12'
    libreelec.OS_RELEASE['MILHOUSE_BUILD'] = '161224'
    libreelec.OS_RELEASE['LIBREELEC_ARCH'] = 'RPi2.arm'
