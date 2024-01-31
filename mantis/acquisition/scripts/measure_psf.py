# %%
from pathlib import Path

import cupy as cp
import napari
import numpy as np

from cupyx.scipy.ndimage import affine_transform

# from iohub.ngff_meta import TransformationMeta
from iohub.reader import open_ome_zarr, read_micromanager

from mantis.analysis.AnalysisSettings import DeskewSettings
from mantis.analysis.analyze_psf import (
    analyze_psf,
    detect_peaks,
    extract_beads,
    generate_report,
)
from mantis.analysis.deskew import (  # _average_n_slices,
    _get_transform_matrix,
    get_deskewed_data_shape,
)

# %% Load data - swap with data acquisition block

data_dir = Path(r'Z:\2023_03_30_beads')
dataset = 'beads_ip_0.74_1'
data_path = data_dir / dataset

# data_dir = Path(r'Z:\2022_12_22_LS_after_SL2')
# dataset = 'epi_beads_100nm_fl_mount_after_SL2_1'
# zyx_data = tifffile.imread(data_dir / dataset / 'LS_beads_100nm_fl_mount_after_SL2_1_MMStack_Pos0.ome.tif')
# scale = (0.250, 0.069, 0.069)  # in um
# axis_labels = ("Z", "Y", "X")

if str(data_path).endswith('.zarr'):
    ds = open_ome_zarr(data_path / '0/0/0')
    zyx_data = ds.data[0, 0]
    # channel_names = ds.channel_names
else:
    ds = read_micromanager(str(data_path))
    zyx_data = ds.get_array(0)[0, 0]
    # channel_names = ds.channel_names

scale = (0.1565, 0.116, 0.116)  # in um
axis_labels = ("SCAN", "TILT", "COVERSLIP")

deskew = True

# %% Detect peaks

raw = False
if axis_labels == ("SCAN", "TILT", "COVERSLIP"):
    raw = True

peaks = detect_peaks(zyx_data, raw=raw)
print(f'Number of peaks detected: {len(peaks)}')

# %% Visualize in napari

viewer = napari.Viewer()
viewer.add_image(zyx_data)

viewer.add_points(peaks, name='peaks local max', size=12, symbol='ring', edge_color='yellow')

# %% Extract and analyze bead patches

beads, offsets = extract_beads(
    zyx_data=zyx_data,
    points=peaks,
    scale=scale,
)

df_gaussian_fit, df_1d_peak_width = analyze_psf(
    zyx_patches=beads,
    bead_offsets=offsets,
    scale=scale,
)

# %% Generate HTML report

psf_analysis_path = data_dir / dataset / 'psf_analysis'
generate_report(
    psf_analysis_path,
    data_dir,
    dataset,
    beads,
    peaks,
    df_gaussian_fit,
    df_1d_peak_width,
    scale,
    axis_labels,
)

# %% Deskew data

if raw and deskew:
    num_chunks = 2
    chunked_data = np.split(zyx_data, num_chunks, axis=-1)
    chunk_shape = chunked_data[0].shape

    settings = DeskewSettings(
        pixel_size_um=scale[-1],
        ls_angle_deg=30,
        scan_step_um=scale[-3],
        keep_overhang=True,
        average_n_slices=3,
    )
    # T, C, Z, Y, X = (1, 1) + chunk_shape

    deskewed_shape, voxel_size = get_deskewed_data_shape(
        chunk_shape,
        settings.ls_angle_deg,
        settings.px_to_scan_ratio,
        settings.keep_overhang,
        settings.average_n_slices,
        settings.pixel_size_um,
    )

    matrix = _get_transform_matrix(
        chunk_shape,
        settings.ls_angle_deg,
        settings.px_to_scan_ratio,
        settings.keep_overhang,
    )

    matrix_gpu = cp.asarray(matrix)
    deskewed_chunks = []
    for chunk in chunked_data:
        deskewed_data_gpu = affine_transform(
            cp.asarray(chunk),
            matrix_gpu,
            output_shape=deskewed_shape,
            order=1,
            cval=80,
        )
        deskewed_chunks.append(cp.asnumpy(deskewed_data_gpu))
        del deskewed_data_gpu

    # concatenate arrays in reverse order
    # identical to cpu deskew using ndi.affine_transform
    deskewed_data = np.concatenate(deskewed_chunks[::-1], axis=-2)

    # TODO: average_n_slices

    # TODO: save deskewed data to zarr

    # df_deskew_gaussian_fit, df_deskew_1d_peak_width = analyze_psf(
    #     zyx_patches=deskewed_beads,
    #     bead_offsets=offsets,
    #     scale=voxel_size,
    # )

    # psf_analysis_path = data_dir / dataset / 'psf_analysis_deskewed'
    # generate_report(
    #     psf_analysis_path,
    #     data_dir,
    #     dataset,
    #     deskewed_beads,
    #     peaks,
    #     df_deskew_gaussian_fit,
    #     df_deskew_1d_peak_width,
    #     voxel_size,
    #     axis_labels=("Z", "Y", "X"),
    # )

    # ct = np.cos(settings.ls_angle_deg * np.pi / 180)
    # Z_shift = 0
    # if not settings.keep_overhang:
    #     Z_shift = int(np.floor(Y * ct * settings.px_to_scan_ratio))
    # matrix = np.array(
    #     [
    #         [
    #             -settings.px_to_scan_ratio * ct,
    #             0,
    #             settings.px_to_scan_ratio,
    #             Z_shift,
    #         ],
    #         [-1, 0, 0, Y - 1],
    #         [0, -1, 0, X - 1],
    #     ]
    # )

    # deskewed_data = deskew_data(
    #     zyx_data,
    #     settings.ls_angle_deg,
    #     settings.px_to_scan_ratio,
    #     settings.keep_overhang,
    #     settings.average_n_slices,
    # )

    # # Create a zarr store
    # transform = TransformationMeta(
    #     type="scale",
    #     scale=2 * (1,) + voxel_size,
    # )
    # output_path = data_dir / (dataset + '_deskewed.zarr')

    # with open_ome_zarr(output_path, layout="hcs", mode="w", channel_names=channel_names) as output_dataset:
    #     pos = dataset.create_position('0', '0', '0')
    #     pos.create_image(
    #         name="0",
    #         data=deskewed_data,
    #         chunks=(1, 1) + deskewed_shape,  # may be bigger than 500 MB
    #         transform=[transform],
    #     )
# %%