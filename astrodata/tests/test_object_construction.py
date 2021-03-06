import astrodata
import numpy as np
import pytest
from astrodata.testing import download_from_archive
from astropy.io import fits
from astropy.nddata import NDData
from astropy.table import Table


@pytest.fixture()
def testfile1():
    """
    Pixels Extensions
    Index  Content                  Type              Dimensions     Format
    [ 0]   science                  NDAstroData       (2304, 1056)   uint16
    [ 1]   science                  NDAstroData       (2304, 1056)   uint16
    [ 2]   science                  NDAstroData       (2304, 1056)   uint16
    """
    return download_from_archive("N20110826S0336.fits")


@pytest.fixture
def testfile2():
    """
    Pixels Extensions
    Index  Content                  Type              Dimensions     Format
    [ 0]   science                  NDAstroData       (4608, 1056)   uint16
    [ 1]   science                  NDAstroData       (4608, 1056)   uint16
    [ 2]   science                  NDAstroData       (4608, 1056)   uint16
    [ 3]   science                  NDAstroData       (4608, 1056)   uint16
    [ 4]   science                  NDAstroData       (4608, 1056)   uint16
    [ 5]   science                  NDAstroData       (4608, 1056)   uint16
    """
    return download_from_archive("N20160524S0119.fits")


def test_create_with_no_data():
    for phu in (fits.PrimaryHDU(), fits.Header(), {}):
        ad = astrodata.create(phu)
        assert isinstance(ad, astrodata.AstroData)
        assert len(ad) == 0
        assert ad.instrument() is None
        assert ad.object() is None


def test_create_with_header():
    hdr = fits.Header({'INSTRUME': 'darkimager', 'OBJECT': 'M42'})
    for phu in (hdr, fits.PrimaryHDU(header=hdr), dict(hdr), list(hdr.cards)):
        ad = astrodata.create(phu)
        assert isinstance(ad, astrodata.AstroData)
        assert len(ad) == 0
        assert ad.instrument() == 'darkimager'
        assert ad.object() == 'M42'


def test_create_from_hdu():
    phu = fits.PrimaryHDU()
    hdu = fits.ImageHDU(data=np.zeros((4, 5)), name='SCI')
    ad = astrodata.create(phu, [hdu])

    assert isinstance(ad, astrodata.AstroData)
    assert len(ad) == 1
    assert isinstance(ad[0].data, np.ndarray)
    assert ad[0].data is hdu.data


def test_create_invalid():
    with pytest.raises(ValueError):
        astrodata.create('FOOBAR')
    with pytest.raises(ValueError):
        astrodata.create(42)


def test_append_image_hdu():
    ad = astrodata.create(fits.PrimaryHDU())
    hdu = fits.ImageHDU(data=np.zeros((4, 5)))
    ad.append(hdu, name='SCI')
    ad.append(hdu, name='SCI2')

    assert len(ad) == 2
    assert ad[0].data is hdu.data
    assert ad[1].data is hdu.data


def test_append_tables():
    """If both ad and ad[0] have a TABLE1, check that ad[0].TABLE1 return the
    extension table.
    """
    nd = NDData(np.zeros((4, 5)), meta={'header': {}})
    ad = astrodata.create({})
    ad.append(nd)
    ad.append(Table([[1]]))
    ad.append(Table([[2]]), add_to=ad[0].nddata)
    assert ad[0].TABLE2['col0'][0] == 2


def test_append_tables2():
    """Check that slices do not report extension tables."""
    ad = astrodata.create({})
    ad.append(NDData(np.zeros((4, 5)), meta={'header': {}}))
    ad.append(NDData(np.zeros((4, 5)), meta={'header': {}}))
    ad.append(NDData(np.zeros((4, 5)), meta={'header': {}}))
    ad.append(Table([[1]]), name='TABLE1', add_to=ad[0].nddata)
    ad.append(Table([[1]]), name='TABLE2', add_to=ad[1].nddata)
    ad.append(Table([[1]]), name='TABLE3', add_to=ad[2].nddata)

    assert ad.exposed == set()
    assert ad[1].exposed == {'TABLE2'}
    assert ad[1:].exposed == set()


def test_append_lowercase_name():
    nd = NDData(np.zeros((4, 5)), meta={'header': {}})
    ad = astrodata.create({})
    ad.append(nd)
    ad.append(Table([[1]]), name='foo')
    ad.append(Table([[1], [2]]), name='bar', add_to=ad[0].nddata)
    ad.append(np.zeros(3), name='arr', add_to=ad[0].nddata)

    assert ad.tables == {'FOO'}
    assert ad.exposed == {'FOO'}

    assert ad[0].tables == {'FOO', 'BAR'}
    assert ad[0].exposed == {'FOO', 'BAR', 'ARR'}


@pytest.mark.dragons_remote_data
def test_can_read_data(testfile1):
    ad = astrodata.open(testfile1)
    assert len(ad) == 3
    assert ad.shape == [(2304, 1056), (2304, 1056), (2304, 1056)]


@pytest.mark.dragons_remote_data
def test_can_read_write_pathlib(tmp_path):
    testfile = tmp_path / 'test.fits'

    ad = astrodata.create({})
    ad.append(np.zeros((4, 5)))
    ad.write(testfile)

    ad = astrodata.open(testfile)
    assert len(ad) == 1
    assert ad.shape == [(4, 5)]


@pytest.mark.dragons_remote_data
def test_append_array_to_root_no_name(testfile2):
    ad = astrodata.open(testfile2)

    lbefore = len(ad)
    ones = np.ones((10, 10))
    ad.append(ones)
    assert len(ad) == (lbefore + 1)
    assert ad[-1].data is ones
    assert ad[-1].hdr['EXTNAME'] == 'SCI'
    assert ad[-1].hdr['EXTVER'] == len(ad)


@pytest.mark.dragons_remote_data
def test_append_array_to_root_with_name_sci(testfile2):
    ad = astrodata.open(testfile2)

    lbefore = len(ad)
    ones = np.ones((10, 10))
    ad.append(ones, name='SCI')
    assert len(ad) == (lbefore + 1)
    assert ad[-1].data is ones
    assert ad[-1].hdr['EXTNAME'] == 'SCI'
    assert ad[-1].hdr['EXTVER'] == len(ad)


@pytest.mark.dragons_remote_data
def test_append_array_to_root_with_arbitrary_name(testfile2):
    ad = astrodata.open(testfile2)
    assert len(ad) == 6

    ones = np.ones((10, 10))
    with pytest.raises(ValueError):
        ad.append(ones, name='ARBITRARY')


@pytest.mark.dragons_remote_data
def test_append_array_to_extension_with_name_sci(testfile2):
    ad = astrodata.open(testfile2)
    assert len(ad) == 6

    ones = np.ones((10, 10))
    with pytest.raises(ValueError):
        ad[0].append(ones, name='SCI')


@pytest.mark.dragons_remote_data
def test_append_array_to_extension_with_arbitrary_name(testfile2):
    ad = astrodata.open(testfile2)

    lbefore = len(ad)
    ones = np.ones((10, 10))
    ad[0].append(ones, name='ARBITRARY')

    assert len(ad) == lbefore
    assert ad[0].ARBITRARY is ones


@pytest.mark.dragons_remote_data
def test_append_nddata_to_root_no_name(testfile2):
    ad = astrodata.open(testfile2)

    lbefore = len(ad)
    ones = np.ones((10, 10))
    hdu = fits.ImageHDU(ones)
    nd = NDData(hdu.data)
    nd.meta['header'] = hdu.header
    ad.append(nd)
    assert len(ad) == (lbefore + 1)


@pytest.mark.dragons_remote_data
def test_append_nddata_to_root_with_arbitrary_name(testfile2):
    ad = astrodata.open(testfile2)
    assert len(ad) == 6

    ones = np.ones((10, 10))
    hdu = fits.ImageHDU(ones)
    nd = NDData(hdu.data)
    nd.meta['header'] = hdu.header
    hdu.header['EXTNAME'] = 'ARBITRARY'
    with pytest.raises(ValueError):
        ad.append(nd)


@pytest.mark.dragons_remote_data
def test_append_table_to_root(testfile2):
    ad = astrodata.open(testfile2)
    with pytest.raises(AttributeError):
        ad.MYTABLE

    assert len(ad) == 6
    table = Table(([1, 2, 3], [4, 5, 6], [7, 8, 9]), names=('a', 'b', 'c'))
    ad.append(table, 'MYTABLE')
    assert (ad.MYTABLE == table).all()


@pytest.mark.dragons_remote_data
def test_append_table_to_root_without_name(testfile2):
    ad = astrodata.open(testfile2)
    assert len(ad) == 6
    with pytest.raises(AttributeError):
        ad.TABLE1

    table = Table(([1, 2, 3], [4, 5, 6], [7, 8, 9]), names=('a', 'b', 'c'))
    ad.append(table)
    assert len(ad) == 6
    assert isinstance(ad.TABLE1, Table)


@pytest.mark.dragons_remote_data
def test_append_table_to_extension(testfile2):
    ad = astrodata.open(testfile2)
    assert len(ad) == 6

    table = Table(([1, 2, 3], [4, 5, 6], [7, 8, 9]), names=('a', 'b', 'c'))
    ad[0].append(table, 'MYTABLE')
    assert (ad[0].MYTABLE == table).all()


# Append / assign Gemini specific

@pytest.mark.dragons_remote_data
def test_append_dq_to_root(testfile2):
    ad = astrodata.open(testfile2)

    dq = np.zeros(ad[0].data.shape)
    with pytest.raises(ValueError):
        ad.append(dq, 'DQ')


@pytest.mark.dragons_remote_data
def test_append_dq_to_ext(testfile2):
    ad = astrodata.open(testfile2)

    dq = np.zeros(ad[0].data.shape)
    ad[0].append(dq, 'DQ')
    assert dq is ad[0].mask


@pytest.mark.dragons_remote_data
def test_append_var_to_root(testfile2):
    ad = astrodata.open(testfile2)

    var = np.random.random(ad[0].data.shape)
    with pytest.raises(ValueError):
        ad.append(var, 'VAR')


@pytest.mark.dragons_remote_data
def test_append_var_to_ext(testfile2):
    ad = astrodata.open(testfile2)

    var = np.random.random(ad[0].data.shape)
    ad[0].append(var, 'VAR')
    assert np.abs(var - ad[0].variance).mean() < 0.00000001


# Append AstroData slices

@pytest.mark.dragons_remote_data
def test_append_single_slice(testfile1, testfile2):
    ad = astrodata.open(testfile2)
    ad2 = astrodata.open(testfile1)

    lbefore = len(ad2)
    last_ever = ad2[-1].nddata.meta['header'].get('EXTVER', -1)
    ad2.append(ad[1])

    assert len(ad2) == (lbefore + 1)
    assert np.all(ad2[-1].data == ad[1].data)
    assert last_ever < ad2[-1].nddata.meta['header'].get('EXTVER', -1)


@pytest.mark.dragons_remote_data
def test_append_non_single_slice(testfile1, testfile2):
    ad = astrodata.open(testfile2)
    ad2 = astrodata.open(testfile1)

    with pytest.raises(ValueError):
        ad2.append(ad[1:])


@pytest.mark.dragons_remote_data
def test_append_whole_instance(testfile1, testfile2):
    ad = astrodata.open(testfile2)
    ad2 = astrodata.open(testfile1)

    with pytest.raises(ValueError):
        ad2.append(ad)


@pytest.mark.dragons_remote_data
def test_append_slice_to_extension(testfile1, testfile2):
    ad = astrodata.open(testfile2)
    ad2 = astrodata.open(testfile1)

    with pytest.raises(ValueError):
        ad2[0].append(ad[0], name="FOOBAR")


@pytest.mark.dragons_remote_data
def test_delete_named_associated_extension(testfile2):
    ad = astrodata.open(testfile2)
    table = Table(([1, 2, 3], [4, 5, 6], [7, 8, 9]), names=('a', 'b', 'c'))
    ad[0].append(table, 'MYTABLE')
    assert 'MYTABLE' in ad[0]
    del ad[0].MYTABLE
    assert 'MYTABLE' not in ad[0]


@pytest.mark.dragons_remote_data
def test_delete_arbitrary_attribute_from_ad(testfile2):
    ad = astrodata.open(testfile2)

    with pytest.raises(AttributeError):
        ad.arbitrary

    ad.arbitrary = 15

    assert ad.arbitrary == 15

    del ad.arbitrary

    with pytest.raises(AttributeError):
        ad.arbitrary
