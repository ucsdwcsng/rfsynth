# `rfsynth`

## Using the `matlab` code for data generation

Refer to `matlab/README.md` for instructions on how to use the `matlab` code for data generation.

## Using `rfsynth` to transmit signals wirelessly

Generate a compressed zip file using the `auto_compressed_siggen` function in `matlab`. This will generate a zip file containing the I/Q data files and metadata. Now the `rfsyth_tx.py` main function can be invoked with an appropriate tx configuration file.

```bash
python rfsynth_tx.py --data /full/path/to/compressed_data.zip --txconfig ./configs/rt_tx_config_scenario_3.json
```

This example tx config file is for 3 transmitters, each an SDR with configs listed in the json file. `rfsynth` only supports Ettus USRP SDRs.

## Requirements

1. GNURadio
2. UHD
3. pyzmq
