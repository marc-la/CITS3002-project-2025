# Statistical Demonstration for Protocol Project

This project implements a custom low-level protocol with error detection and handling capabilities. The statistical demonstration aims to showcase the effectiveness of the protocol's error detection mechanisms by artificially injecting errors into packets and measuring how many packets are flagged as corrupted.

## Project Structure

- `src/__init__.py`: Main module for the protocol, detailing advanced features and tasks related to custom protocols and encryption layers.
- `src/packet.py`: Defines the `Packet` class for creating, packing, and unpacking protocol packets, including checksum verification and error handling.
- `src/checksum.py`: Implements functions for computing and verifying checksums using CRC32.
- `src/errors.py`: Defines custom exceptions for handling checksum verification failures and out-of-sequence packets.
- `src/stats_demo/__init__.py`: Initializer for the statistical demonstration module.
- `src/stats_demo/injector.py`: Contains functionality to inject errors or scramble bits in packets to measure corruption detection.

## Getting Started

To set up the project, clone the repository and navigate to the `src` directory. You can run the statistical demonstration by executing the `injector.py` script.

### Requirements

- Python 3.x
- Required libraries (if any) should be listed here.

### Running the Demonstration

1. Run the statistical demonstration script:
   ```
   python stat_demo.py
   ```

### Expected Output

The demonstration will output the number of packets sent, the number of packets flagged as corrupted, and any additional statistics related to the error injection process.

## Contributing

Contributions to enhance the statistical demonstration or the protocol itself are welcome. Please submit a pull request or open an issue for discussion.

## License

This project is licensed under the MIT License - see the LICENSE file for details.