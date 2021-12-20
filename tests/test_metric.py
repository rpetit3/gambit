"""Test distance metric calculations."""

import pickle

import pytest
import numpy as np

from gambit.metric import jaccard, jaccarddist, jaccard_bits, jaccard_generic, jaccarddist_array, \
	jaccarddist_matrix, SCORE_DTYPE, BOUNDS_DTYPE
from gambit.sigs.convert import sparse_to_dense
from gambit.sigs import SignatureArray, SignatureList
from gambit.kmers import KmerSpec
from gambit.test import make_signatures, check_progress


@pytest.fixture(
	params=[
		(7, 'u2'),
		(9, 'u4'),
		(9, 'i4'),
		(9, 'u8'),
		None,
	],
	scope='module',
)
def sigs(request, test_data):
	"""SignatureArray to test on."""

	if request.param is None:
		# Load signatures from file
		with open(test_data / 'signatures/signatures.pickle', 'rb') as fobj:
			signatures_list = pickle.load(fobj)

		sigs = SignatureArray(signatures_list, KmerSpec(11, 'ATGAC'))

	else:
		# Create random signatures
		k, dtype = request.param

		np.random.seed(0)
		sigs = make_signatures(k, 40, dtype)

	return sigs


@pytest.fixture()
def queries(sigs):
	"""Query signatures."""
	# Make it a little different than the reference signatures
	return sigs[::2]


@pytest.fixture()
def refs_array(sigs):
	"""Reference signatures as SignatureArray."""
	# Make it a little different than the query signatures
	return sigs[5:]


@pytest.fixture()
def refs(request, refs_array):
	"""Reference signatures in multiple different types. Use indirect parameterization."""

	if request.param == 'SignatureArray':
		return refs_array

	if request.param == 'alt_bounds':
		# The inner Cython function takes a specific type for the bounds array.
		# Try with this type and a different type, should be converted automatically by the outer Python func
		assert refs_array.bounds.dtype == BOUNDS_DTYPE
		refs_array = SignatureArray.from_arrays(refs_array.values, refs_array.bounds.astype('i4'), refs_array.kmerspec)
		assert refs_array.bounds.dtype != BOUNDS_DTYPE
		return refs_array

	if request.param == 'SignatureList':
		return SignatureList(refs_array)

	if request.param == 'list':
		return list(refs_array)

	assert 0


def test_jaccard_single(sigs):
	"""Test calculating single distances at a time."""

	# Because jaccard() is calculated as 1 - jaccarddist(), it is off from the other two Python
	# versions which divide the intersection by the union directly
	def isclose(a, b): return np.isclose(a, b, atol=1e-7)

	# Iterate over subset of pairs
	for i, sparse1 in enumerate(sigs[:5]):
		dense1 = sparse_to_dense(sigs.kmerspec, sparse1)
		for j, sparse2 in enumerate(sigs):
			dense2 = sparse_to_dense(sigs.kmerspec, sparse2)

			score = jaccard(sparse1, sparse2)

			# Check range
			assert 0 <= score <= 1

			# Check vs slow version
			assert isclose(score, jaccard_generic(sparse1, sparse2))

			# Check distance
			assert isclose(jaccarddist(sparse1, sparse2), 1 - score)

			# Check dense bit vector version
			assert isclose(jaccard_bits(dense1, dense2), score)

			# Check score vs. self is one
			if i == j:
				assert score == 1


class TestJaccardDistArray:
	"""Test jaccarddist_array() function."""

	def test_signaturearray(self, sigs):
		"""Full test using SignatureArray as refs argument."""

		for i, sig1 in enumerate(sigs):
			dists = jaccarddist_array(sig1, sigs)
			assert dists.shape == (len(sigs),)

			# Check against single signatures
			for j, sig2 in enumerate(sigs):
				assert dists[j] == jaccarddist(sig1, sig2)

	@pytest.mark.parametrize('refs', ['alt_bounds', 'SignatureList', 'list'], indirect=True)
	def test_alt_types(self, refs_array, refs):
		"""Test alternate types for refs argument."""
		q = refs_array[0]
		assert np.array_equal(jaccarddist_array(q, refs), jaccarddist_array(q, refs_array))

	def test_preallocated(self, sigs):
		"""Test using pre-allocated output array"""
		out = np.empty(len(sigs), dtype=SCORE_DTYPE)
		jaccarddist_array(sigs[0], sigs, out=out)
		assert np.array_equal(out, jaccarddist_array(sigs[0], sigs))

		# Wrong size
		out2 = np.empty(len(sigs) + 1, dtype=SCORE_DTYPE)
		with pytest.raises(ValueError):
			jaccarddist_array(sigs[0], sigs, out=out2)

		# Wrong dtype
		out3 = np.empty(len(sigs), dtype=int)
		with pytest.raises(ValueError):
			jaccarddist_array(sigs[0], sigs, out3)


class TestJaccardDistMatrix:
	"""Test the jaccarddist_matrix() function."""

	@pytest.fixture()
	def expected(self, queries, refs_array):
		"""Expected array of distances, calculated row by row."""
		dmat = np.empty((len(queries), len(refs_array)), dtype=SCORE_DTYPE)

		for i, q in enumerate(queries):
			for j, r in enumerate(refs_array):
				dmat[i, j] = jaccarddist(queries[i], refs_array[j])

		return dmat

	@pytest.mark.parametrize('refs', ['SignatureArray', 'SignatureList', 'list'], indirect=True)
	@pytest.mark.parametrize('use_ref_indices', [False, True])
	@pytest.mark.parametrize('chunksize', [None, 10])
	def test_basic(self, queries, refs, expected, use_ref_indices, chunksize):

		if use_ref_indices:
			ref_indices = [i for i in range(len(refs)) if i % 3 != 0]
			expected = expected[:, ref_indices]
		else:
			ref_indices = None

		with check_progress(total=expected.size) as pconf:
			out = jaccarddist_matrix(queries, refs, ref_indices=ref_indices, chunksize=chunksize, progress=pconf)

		assert np.array_equal(out, expected)

	def test_out(self, queries, refs_array, expected):
		"""Test using pre-allocated output array."""
		out = np.empty((len(queries), len(refs_array)), dtype=SCORE_DTYPE)
		jaccarddist_matrix(queries, refs_array, out=out)
		assert np.array_equal(out, expected)

		# Wrong size
		out2 = np.empty((len(refs_array) + 1, len(queries)), dtype=SCORE_DTYPE)
		with pytest.raises(ValueError):
			jaccarddist_matrix(queries, refs_array, out=out2)

		# Wrong dtype
		out3 = np.empty((len(refs_array) + 1, len(queries)), dtype=int)
		with pytest.raises(ValueError):
			jaccarddist_array(queries, refs_array, out3)


def test_different_dtypes():
	"""Test metric on sparse arrays with different dtypes."""

	np.random.seed(0)
	dtypes = ['u2', 'i4', 'u4', 'u8']

	# Test all pairs of dtypes
	for i, dt1 in enumerate(dtypes):
		for j in range(i + 1, len(dtypes)):
			dt2 = dtypes[j]

			# Bit length of largest positive integer both dtypes can store
			nbits = min(np.iinfo(dt).max.bit_length() for dt in [dt1, dt2])

			# Try for k == 8, but not larger than will fit in both dtypes
			k = min(nbits // 4, 8)

			# Create test signatures as u8 dtype (will fit everything)
			sigs = make_signatures(k, 5, 'u8')

			# Convert signatures to each dtype, making sure there is no overflow
			try:
				# Tell numpy to raise error on overflow
				old_err = np.seterr(over='raise')

				sigs1 = SignatureArray(sigs, dtype=dt1)
				sigs2 = SignatureArray(sigs, dtype=dt2)

			finally:
				np.seterr(**old_err)

			assert sigs1.values.dtype == dt1
			assert sigs2.values.dtype == dt2

			# Expected all-by-all distance matrix from u8 signatures
			expected = jaccarddist_matrix(sigs, sigs)

			for k in range(len(sigs)):
				# Test individually
				for l in range(k + 1, len(sigs)):
					assert jaccarddist(sigs1[k], sigs2[l]) == expected[k, l]
					assert jaccarddist(sigs2[k], sigs1[l]) == expected[k, l]

				# Test each against all of the others using jaccarddist_array
				assert np.array_equal(jaccarddist_array(sigs1[k], sigs2), expected[k, :])
				assert np.array_equal(jaccarddist_array(sigs2[k], sigs1), expected[k, :])

			# Test full matrix using jaccarddist_matrix
			assert np.array_equal(jaccarddist_matrix(sigs1, sigs2), expected)
