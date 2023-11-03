from click.testing import CliRunner

from mantis.cli.main import cli


def test_optimize_affine_cli(tmp_path, example_plate, example_estimate_affine_settings):
    plate_path, _ = example_plate
    config_path, _ = example_estimate_affine_settings
    output_path = tmp_path / "config.yaml"

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "optimize-affine",
            "-s",
            str(plate_path) + "/A/1/0",
            "-t",
            str(plate_path) + "/B/1/0",  # test could be improved with different stores
            "-c",
            str(config_path),
            "-o",
            str(output_path),
        ],
    )

    # Weak test
    assert "Enter phase_channel index to process" in result.output
