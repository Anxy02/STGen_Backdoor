# Project Toolchain Documentation

This project contains multiple important toolchains that support the entire workflow. The main components are as follows:

| Directory     | Description |
| :---          | ----------- |
| `/nuXmv`      | Verification and post-processing based on nuXmv tool |
| `/plcverif`   | Verification and post-processing based on plcverif tool, integrating nuXmv, cbmc, and other verification methods |
| `/tools`      | Collection of all utility tools |

# Environment Setup Guide

This section provides detailed instructions for configuring the necessary toolchains to support PLC command-line compilation and verification.

> ⚠️ Note: The following tools have been added to .gitignore and need to be manually installed and configured.

## I. Compilation Toolchains

### 1. MatIEC Compiler

MatIEC is an open-source IEC 61131-3 compiler used to compile IEC code into C code.

```bash
# 1. Clone repository
git clone https://github.com/nucleron/matiec.git
cd matiec

# 2. Install dependencies
apt-get install autoconf flex bison
apt-get install build-essential -y

# 3. Build and install
autoreconf -i
./configure
make

# 4. Configure environment variables (add to ~/.bashrc)
export MATIEC_INCLUDE_PATH=$path_to_LLM4PLC/matiec/lib
export MATIEC_C_INCLUDE_PATH=$path_to_LLM4PLC/matiec/lib/C
export PATH=$path_to_LLM4PLC/matiec:$PATH

# Usage examples
# ./iec2iec --help  # View help information
# ./iec2c --help    # View help information
```

### 2. Rusty Compiler

Rusty is a Rust-based PLC compiler that supports modern PLC programming features.

```bash
# 1. Install system dependencies
sudo apt-get install build-essential llvm-14-dev liblld-14-dev libz-dev lld libclang-common-14-dev libpolly-14-dev

# 2. Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# 3. Clone and build Rusty
git clone https://github.com/PLC-lang/rusty.git --depth 1
cd rusty
cargo build

# 4. Configure environment variables (add to ~/.bashrc)
export PATH="$PATH:/path/to/rusty/target/debug"

# 5. Install OSCAT library (optional)
git clone https://github.com/PLC-lang/oscat.git

# Usage example
plc /path/to/your/file.st
```

## II. Verification Toolchains

Verification tools are used for formal verification of generated code to detect potential errors and validate the functional correctness of ST code.

### 3. nuXmv Verification Tool

nuXmv is a powerful model checking tool for formal verification.

```bash
# 1. Download and extract
wget https://nuxmv.fbk.eu/theme/download.php?file=nuXmv-2.0.0-linux64.tar.gz
tar -xzvf nuXmv-2.0.0-linux64.tar.gz

# 2. Configure environment variables (add to ~/.bashrc)
export PATH=$PATH:/path/to/nuXmv-2.0.0-Linux/bin
```

### 4. CBMC Verification Tool

CBMC is a bounded model checker for verifying C and C++ programs.

```bash
# Direct installation
apt-get install cbmc
```

### 5. PLCverif Toolchain

PLCverif is an automated verification tool that can translate PLC code and specified requirements into various model checker input formats.

```bash
# 1. Install Java dependency
sudo apt install openjdk-17-jdk

# 2. Download and install PLCverif
cd src
mkdir plcverif
cd plcverif
wget https://plcverif-oss.gitlab.io/cern.plcverif.cli/releases/cern.plcverif.cli.cmdline.app.product-linux.gtk.x86_64.tar.gz
tar -xvzf cern.plcverif.cli.cmdline.app.product-linux.gtk.x86_64.tar.gz

# 3. Configure environment variables (add to ~/.bashrc)
export PLCVERIF_PATH="/path/to/plcverif"
export PATH="$PLCVERIF_PATH:$PATH"
```

## Environment Variables Configuration Example

Add the following content to your `~/.bashrc` file:

```bash
# Toolchain path configuration
export PATH=$PATH:/workspaces/STGen-Backdoor/src/nuXmv-2.0.0-Linux/bin
export PLCVERIF_PATH="/workspaces/STGen-Backdoor/src/plcverif"
export PATH="$PLCVERIF_PATH:$PATH"
export PATH=/bin:/usr/bin:$PATH
export PATH="$PATH:/workspaces/STGen-Backdoor/src/rusty/target/debug"
```

After configuration, execute `source ~/.bashrc` to apply the environment variables.