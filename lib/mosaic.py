import sys
from . import gdal_merge
from ..rasters import getRasterAsGdal


def moasicRasters(input_file_list, output_filepath, no_data_value=None, additional_args=None, open=False):
    '''
    Mosaic rasters. Basically a function wrapper for the `gdal_merge` program. Automatically copies raster color table,
    if one exists in the first band of first raster.
    :param input_file_list: (str[]) List of rasters to mosaic as filepaths.
    :param output_filepath: (str) Output filepath.
    :param [no_data_value]: (number) No data value.
    :param [additional_args]: (str[]) List of additional arguments. See <https://gdal.org/programs/gdal_merge.html> for
           full documentation.
    :param [open=False]: (boolean) If true, will open and return the resulting raster dataset.
    :return: (gdal.Dataset) Dataset instance of mosaiced raster.
    '''
    # first arguments (empty then output)
    args = ["", "-o", output_filepath]
    # add optional supplied no data value
    if no_data_value is not None:
        args += ["-n", str(no_data_value)]
    # auto grab some arguments from first input file
    first_raster = getRasterAsGdal(input_file_list[0])
    first_raster_band = first_raster.GetRasterBand(1)
    if additional_args is not None:
        # additional arguments added as key/value pairs
        for key, value in additional_args.iteritems():
            args += [key, value]
    # copy over some automatic arguments if they do not exist in supplied
    # mask no data value
    # if (not additional_args or "-n" not in additional_args) and no_data_value is None and first_raster_band.GetNoDataValue() is not None:
    #     args += ["-n", str(first_raster_band.GetNoDataValue())]
    # add color table if it exists
    if (not additional_args or "-pct" not in additional_args) and first_raster_band.GetRasterColorTable() is not None:
        args += ["-pct"]
    sys.argv = args + input_file_list
    gdal_merge.main()
    if open:
        return getRasterAsGdal(output_filepath)
