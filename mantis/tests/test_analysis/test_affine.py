# %%
import numpy as np
import ants
from mantis.cli.utils import (
    numpy_to_ants_transform_zyx,
    ants_to_numpy_transform_zyx,
    affine_transform,
)


def test_numpy_to_ants_transform_zyx():
    T_numpy = np.eye(4)
    T_ants = numpy_to_ants_transform_zyx(T_numpy)
    assert isinstance(T_ants, ants.core.ants_transform.ANTsTransform)


def test_ants_to_numpy_transform_zyx():
    T_ants = ants.new_ants_transform(transform_type='AffineTransform')
    T_ants.set_parameters(np.eye(12))
    T_numpy = ants_to_numpy_transform_zyx(T_ants)
    assert isinstance(T_numpy, np.ndarray)
    assert T_numpy.shape == (4, 4)


def test_affine_transform():
    # Create input data
    zyx_data = np.ones((10, 10, 10))
    matrix = np.eye(4)
    output_shape_zyx = (10, 10, 10)

    # Call the function
    result = affine_transform(zyx_data, matrix, output_shape_zyx)

    # Check the result
    assert isinstance(result, np.ndarray)
    assert result.shape == output_shape_zyx


def test_3d_translation():
    # Create input data
    zyx_data = np.ones((10, 10, 10))
    matrix = np.eye(4)
    translation = np.array([-3, 1, 4])
    matrix[:3, -1] = translation
    output_shape_zyx = (10, 10, 10)

    # Call the function
    result = affine_transform(zyx_data, matrix, output_shape_zyx)

    # Check the result
    assert isinstance(result, np.ndarray)
    assert result.shape == output_shape_zyx
    assert np.all(result[3:10, 0:9, 0:6] == 1)  # Example assertion


if __name__ == "__main__":
    test_numpy_to_ants_transform_zyx()
    test_ants_to_numpy_transform_zyx()
    test_affine_transform()
    test_3d_translation()
# %%
