from unittest import TestCase

from .binary_package_version import join_description, split_description
from .source_package_version import (SOURCE_PACKAGE_FILE_TYPE_DIFF,
                                     SOURCE_PACKAGE_FILE_TYPE_DIFF_TARBALL,
                                     SOURCE_PACKAGE_FILE_TYPE_DSC,
                                     SOURCE_PACKAGE_FILE_TYPE_NATIVE,
                                     SOURCE_PACKAGE_FILE_TYPE_ORIG_TARBALL,
                                     SourcePackageValidationException,
                                     guess_ftype_from_filename)


class BinaryPackageVersionTestCase(TestCase):
    def test_split_description_empty(self):
        self.assertEquals(split_description(''), ('', ''))

    def test_split_description_no_long_description(self):
        self.assertEquals(split_description('Only a short description'),
                          ('Only a short description', ''))

    def test_split_description_full(self):
        self.assertEquals(split_description('a short description\n ...and a long\n .\n description, too\n'),
                          ('a short description', '...and a long\n.\ndescription, too\n'))

    def test_join_description_empty(self):
        self.assertEquals(join_description('', ''), '')

    def test_join_description_no_long_description(self):
        self.assertEquals(join_description('Only a short description', ''), 'Only a short description')

    def test_join_description_full(self):
        self.assertEquals(join_description('a short description', '...and a long\n.\ndescription, too\n'),
                          'a short description\n ...and a long\n .\n description, too\n')


class SourcePackageVersionTestCase(TestCase):
    def test_guess_ftype_dsc(self):
        self.assertEquals(guess_ftype_from_filename('foobar.dsc'), SOURCE_PACKAGE_FILE_TYPE_DSC)

    def test_guess_ftype_orig_tarball(self):
        for fname in ['foo.orig.tar.gz', 'foo.orig.tar.bz2', 'foo.orig.tar.xz']:
            self.assertEquals(guess_ftype_from_filename(fname), SOURCE_PACKAGE_FILE_TYPE_ORIG_TARBALL,
                              '%s was not detected as an original tarball' % fname)

    def test_guess_ftype_diff(self):
        for fname in ['foo.diff.gz', 'foo.diff.bz2', 'foo.diff.xz']:
            self.assertEquals(guess_ftype_from_filename(fname), SOURCE_PACKAGE_FILE_TYPE_DIFF,
                              '%s was not detected as diff patch' % fname)

    def test_guess_ftype_diff_tarball(self):
        for fname in ['foo.diff.tar.gz', 'foo.diff.tar.bz2', 'foo.diff.tar.xz']:
            self.assertEquals(guess_ftype_from_filename(fname), SOURCE_PACKAGE_FILE_TYPE_DIFF_TARBALL,
                              '%s was not detected as diff tarball' % fname)

    def test_guess_ftype_native(self):
        for fname in ['foo.tar.gz', 'foo.tar.bz2', 'foo.tar.xz']:
            self.assertEquals(guess_ftype_from_filename(fname), SOURCE_PACKAGE_FILE_TYPE_NATIVE,
                              '%s was not detected as native tarball' % fname)

    def test_guess_ftype_nonsense(self):
        for fname in ['foasdfsadf', '...........', 'foo.tar.xz.blah']:
            self.assertRaises(SourcePackageValidationException, guess_ftype_from_filename, fname)
