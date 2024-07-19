# `matlab` signal generator for `rfsynth`

Directory structure:

```
lib/ - all library functions
examples/ - example scripts
```

## Requirements

- MATLAB R2021b or later
- [Communications Toolbox](https://www.mathworks.com/products/communications.html)
- [Bluetooth Toolbox](https://www.mathworks.com/products/bluetooth.html)
- [WLAN Toolbox](https://www.mathworks.com/products/wlan.html)

## Configuration driven generation

To generate a single I/Q data file and metadata, use the `auto_siggen` function. This function reads a configuration file and generates the data file and metadata.

```matlab
auto_siggen('config.yml');
```

To generate compressed I/Q data files and metadata (for transmitting long signals OTA), use the `auto_compressed_siggen` function. This function reads a configuration file and generates the data files and metadata. The format of this config file is slightly different - and involves specifying the number of transmitters and their capabilities.

```matlab
auto_compressed_siggen('compressed_config.yml');
```

## Using the 'API'  

The code in `siggen_api` is a simple example of how to use the signal generation functions in a more programmatic way. This is useful if you want to generate signals in a loop, or if you want to generate signals with different parameters.
