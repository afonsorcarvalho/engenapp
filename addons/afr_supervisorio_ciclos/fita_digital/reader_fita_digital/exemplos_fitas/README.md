# Exemplo Fitas Digitais

This directory contains example fita digital files organized by reader implementation type.

## Directory Structure

Each subdirectory contains example files for the corresponding reader:

- **afr13/** - Examples for `ReaderFitaDigitalAfr13`
  - `20251001_152420_Ciclo_002509_valid_afr13.txt` - Valid AFR13 format with complete header and data

- **afr14_medplast/** - Examples for `ReaderFitaDigitalAfr14Medplast`
  - `20251001_152420_Ciclo_002509_baumer_estilo_amostra.txt` - Baumer-style format (compatible with AFR14_MedPlast)

- **baumer_hivac2/** - Examples for `ReaderFitaDigitalBaumerHivac2`
  - `20251001_152420_Ciclo_002509_rollover_marcador.txt` - Baumer Hivac2 with marcador timestamps and rollover handling
  - `20260425_152851_Ciclo_003154.txt` - Production example with ~70 data points

- **sercon_or2011/** - Examples for `ReaderFitaDigitalSerconOr2011`
  - `20251001_152420_Ciclo_002509_valid_afr13.txt` - AFR13-compatible format

- **sercon_jp_lac210/** - Examples for `ReaderFitaDigitalSerconJpLac210`
  - `20251001_152420_Ciclo_002509_valid_afr13.txt` - AFR13-compatible format

- **sercon_tds/** - Examples for `ReaderFitaDigitalSerconTds`
  - `20251001_152420_Ciclo_002509_valid_afr13.txt` - AFR13-compatible format

## Usage

### Testing a Specific Reader

```python
from reader_fita_digital_afr13 import ReaderFitaDigitalAfr13
from pathlib import Path

fixture = Path("exemplos_fitas/afr13/20251001_152420_Ciclo_002509_valid_afr13.txt")
reader = ReaderFitaDigitalAfr13(str(fixture))
reader.read_file()
state = reader.get_state()
```

### Profiling

Use the profiling scripts at the package root:

- `profile_readers.py` - Quick benchmarking (10 iterations, avg execution time & peak memory)
- `profile_readers_detailed.py` - Detailed breakdown with parsed data statistics

## File Format Notes

- **AFR13 format**: Standard 25-line header followed by phase definitions and timestamped measurements
- **Baumer format**: Similar header, specialized timestamp handling with marcador snapshots for day-rollover detection
- **Sercon formats**: Compatible with AFR13 base format with reader-specific parsing rules

## Adding New Examples

To add a new example file:

1. Place it in the appropriate reader subdirectory
2. Use a descriptive filename following the pattern: `YYYYMMDD_HHMMSS_Ciclo_XXXXXX_<description>.txt`
3. Ensure the file is valid for the reader type (test with the reader before committing)
4. Update this README if needed
