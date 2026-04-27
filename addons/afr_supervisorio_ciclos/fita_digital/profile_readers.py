#!/usr/bin/env python3
"""Profile memory and CPU usage for each reader implementation."""

import os
import sys
import time
import tracemalloc
import cProfile
import pstats
from io import StringIO
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

# Map reader class to example file in organized folders
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


def profile_reader(reader_class, fixture_file, name, iterations=10):
    """Profile a single reader implementation."""
    fixture_path = get_fixture_path(fixture_file)

    if not fixture_path.exists():
        return None

    file_size_kb = fixture_path.stat().st_size / 1024

    try:
        # Warm-up run
        reader = reader_class(str(fixture_path))
        reader.read_file()

        # Multiple runs for averaging
        times = []
        peak_memory = 0

        for i in range(iterations):
            tracemalloc.start()
            start_time = time.perf_counter()

            reader = reader_class(str(fixture_path))
            result = reader.read_file()

            elapsed = time.perf_counter() - start_time
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            times.append(elapsed * 1000)  # Convert to ms
            peak_mb = peak / 1024 / 1024
            if peak_mb > peak_memory:
                peak_memory = peak_mb

        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        return {
            "name": name,
            "fixture": fixture_file,
            "file_size_kb": file_size_kb,
            "avg_time_ms": avg_time,
            "min_time_ms": min_time,
            "max_time_ms": max_time,
            "peak_memory_mb": peak_memory,
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
    """Profile all readers and print results."""
    print("=" * 100)
    print("PROFILING READER IMPLEMENTATIONS")
    print("=" * 100)
    print()

    results = []
    for reader_class, fixture, name in READERS:
        print(f"Profiling {name}...", end=" ", flush=True)
        result = profile_reader(reader_class, fixture, name)

        if result:
            if "error" in result:
                print(f"ERROR: {result['error']}")
            else:
                print(f"OK")
            results.append(result)
        else:
            print("SKIPPED (fixture not found)")

    print()
    print("=" * 120)
    print("RESULTS TABLE")
    print("=" * 120)
    print()

    # Print table header
    print(f"{'Reader':<25} {'File Size':<12} {'Min Time':<12} {'Avg Time':<12} {'Max Time':<12} {'Peak Mem':<12} {'Status':<10}")
    print("-" * 120)

    for result in results:
        if "error" in result:
            print(f"{result['name']:<25} {result['file_size_kb']:<12.2f}KB {'ERROR':<12} {result['error']:<30} {'FAILED':<10}")
        else:
            file_size = f"{result['file_size_kb']:.2f} KB"
            min_time = f"{result['min_time_ms']:.3f} ms"
            avg_time = f"{result['avg_time_ms']:.3f} ms"
            max_time = f"{result['max_time_ms']:.3f} ms"
            peak_mem = f"{result['peak_memory_mb']:.2f} MB"
            status = "OK" if result['result_success'] else "FAILED"

            print(f"{result['name']:<25} {file_size:<12} {min_time:<12} {avg_time:<12} {max_time:<12} {peak_mem:<12} {status:<10}")

    print()
    print("=" * 120)


if __name__ == "__main__":
    main()
