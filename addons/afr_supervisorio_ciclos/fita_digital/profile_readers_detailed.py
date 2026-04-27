#!/usr/bin/env python3
"""Enhanced profiling with parsed data statistics for each reader implementation."""

import os
import sys
import time
import tracemalloc
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from reader_fita_digital.reader_fita_digital_afr13 import ReaderFitaDigitalAfr13
from reader_fita_digital.reader_fita_digital_afr14_medplast import ReaderFitaDigitalAfr14Medplast
from reader_fita_digital.reader_fita_digital_baumer_hivac2 import ReaderFitaDigitalBaumerHivac2
from reader_fita_digital.reader_fita_digital_sercon_or2011 import ReaderFitaDigitalSerconOr2011
from reader_fita_digital.reader_fita_digital_sercon_jp_lac210 import ReaderFitaDigitalSerconJpLac210
from reader_fita_digital.reader_fita_digital_sercon_tds import ReaderFitaDigitalSerconTds


EXEMPLOS_DIR = Path(__file__).parent / "reader_fita_digital" / "exemplos_fitas"

READERS = [
    (ReaderFitaDigitalAfr13, "afr13/20260425_152851_Ciclo_003154.txt", "AFR13"),
    (ReaderFitaDigitalAfr14Medplast, "afr14_medplast/20251001_152420_Ciclo_002509_baumer_estilo_amostra.txt", "AFR14_MedPlast"),
    (ReaderFitaDigitalBaumerHivac2, "baumer_hivac2/20251001_152420_Ciclo_002509_rollover_marcador.txt", "Baumer_Hivac2"),
    (ReaderFitaDigitalSerconOr2011, "sercon_or2011/20251001_152420_Ciclo_002509_valid_afr13.txt", "Sercon_OR2011"),
    (ReaderFitaDigitalSerconJpLac210, "sercon_jp_lac210/20251001_152420_Ciclo_002509_valid_afr13.txt", "Sercon_JP_LAC210"),
    (ReaderFitaDigitalSerconTds, "sercon_tds/20251001_152420_Ciclo_002509_valid_afr13.txt", "Sercon_TDS"),
]


def get_fixture_path(filename):
    """Get example file from exemplos_fitas directory."""
    exemplos_path = EXEMPLOS_DIR / filename
    if exemplos_path.exists():
        return exemplos_path
    raise FileNotFoundError(f"Example {filename} not found in {EXEMPLOS_DIR}")


def profile_reader_detailed(reader_class, fixture_file, name):
    """Profile reader and extract parsed data statistics."""
    fixture_path = get_fixture_path(fixture_file)

    if not fixture_path.exists():
        return None

    file_size_kb = fixture_path.stat().st_size / 1024

    try:
        tracemalloc.start()
        start_time = time.perf_counter()

        reader = reader_class(str(fixture_path))
        result = reader.read_file()

        elapsed = time.perf_counter() - start_time
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        peak_mb = peak / 1024 / 1024
        elapsed_ms = elapsed * 1000

        # Extract parsed data info
        state = reader.get_state()

        # Handle error states
        if isinstance(state, str) or state == "erro":
            data_points = 0
            phases = 0
            phase_names = []
        else:
            header = state.get('header', {})
            body = state.get('body', {})

            data_points = len(body.get('data', []))
            phases = len(body.get('fase', []))
            phase_names = [f[1] for f in body.get('fase', [])] if body.get('fase') else []

        return {
            "name": name,
            "fixture": fixture_file,
            "file_size_kb": file_size_kb,
            "elapsed_ms": elapsed_ms,
            "peak_memory_mb": peak_mb,
            "data_points": data_points,
            "phases": phases,
            "phase_names": ", ".join(phase_names) if phase_names else "N/A",
            "result_success": result is not None,
        }

    except Exception as e:
        return {
            "name": name,
            "fixture": fixture_file,
            "file_size_kb": file_size_kb,
            "error": str(e),
        }


def main():
    """Profile all readers and print detailed results."""
    print("=" * 140)
    print("DETAILED PROFILING - READER IMPLEMENTATIONS WITH PARSED DATA STATISTICS")
    print("=" * 140)
    print()

    results = []
    for reader_class, fixture, name in READERS:
        print(f"Profiling {name}...", end=" ", flush=True)
        result = profile_reader_detailed(reader_class, fixture, name)

        if result:
            if "error" in result:
                print(f"ERROR: {result['error']}")
            else:
                print(f"OK ({result['data_points']} data points, {result['phases']} phases)")
            results.append(result)
        else:
            print("SKIPPED (fixture not found)")

    print()
    print("=" * 140)
    print("RESULTS TABLE")
    print("=" * 140)
    print()

    # Print table header
    print(f"{'Reader':<25} {'File (KB)':<12} {'Exec (ms)':<12} {'Peak Mem (MB)':<14} {'Data Pts':<10} {'Phases':<10} {'Status':<10}")
    print("-" * 140)

    for result in results:
        if "error" in result:
            print(f"{result['name']:<25} {result['file_size_kb']:<12.2f} {'ERROR':<12} {result['error']:<30} {'FAILED':<10}")
        else:
            file_size = f"{result['file_size_kb']:.2f}"
            exec_time = f"{result['elapsed_ms']:.3f}"
            peak_mem = f"{result['peak_memory_mb']:.3f}"
            status = "OK" if result['result_success'] else "FAILED"

            print(f"{result['name']:<25} {file_size:<12} {exec_time:<12} {peak_mem:<14} {result['data_points']:<10} {result['phases']:<10} {status:<10}")

    print()
    print("=" * 140)
    print("PARSED DATA DETAILS")
    print("=" * 140)
    print()

    for result in results:
        if "error" not in result and result.get('phases', 0) > 0:
            print(f"{result['name']}:")
            print(f"  Data Points: {result['data_points']}")
            print(f"  Phases: {result['phases']}")
            print(f"  Phase Names: {result['phase_names']}")
            print()


if __name__ == "__main__":
    main()
