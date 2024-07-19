# `rfsynth`

`rfsynth` is a comprehensive RF data generation and testing platform designed specifically for spectrum information systems. By leveraging both simulation and real-world data generation methodologies, `rfsynth` facilitates the creation of extensive and diverse datasets necessary for training and testing RF machine learning models and spectrum sensing solutions. This repository includes the MATLAB code for data generation and scripts for signal transmission using Ettus USRP SDRs.

<https://github.com/user-attachments/assets/295cc706-e7db-4178-b2d8-e8b314a08c92>

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

## Citation

If you find this useful, please cite our work:

```
@inproceedings{RFSynth2024,
  author    = {Hari Prasad Sankar and Raghav Subbaraman and Tianyi Hu and Dinesh Bharadia},
  title     = {RFSynth: Data Generation and Testing Platform for Spectrum Information Systems},
  booktitle = {Proceedings of the 2024 IEEE International Symposium on Dynamic Spectrum Access Networks (DySpan)},
  year      = {2024},
  address   = {Washington, DC},
  month     = {May},
  publisher = {IEEE},
}
```

For the full paper and talk slides, please visit [wcsng.ucsd.edu/rfsynth](https://wcsng.ucsd.edu/rfsynth)

## Acknowledgements

This paper is based upon work supported in part by the Office of the Director of National Intelligence (ODNI), Intelligence Advanced Research Projects Activity (IARPA), via [2021-2106240007]. The views and conclusions contained herein are those of the authors and should not be interpreted as necessarily representing the official policies, either expressed or implied, of ODNI, IARPA, or the U.S. Government. The U.S. Government is authorized to reproduce and distribute reprints for governmental purposes notwithstanding any copyright annotation therein.
